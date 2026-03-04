"""
Panelin Agno — FastAPI Application Entry Point
================================================

Expone:
    1. /agno/chat         — Agente conversacional (con historial por sesión)
    2. /agno/quote        — Workflow determinístico de cotización
    3. /agno/health       — Health check del agente
    4. Agno Playground    — UI de desarrollo en /playground

El Wolf API existente se monta en /api/* preservando todos sus endpoints.
La migración es ADITIVA — no rompe nada de la arquitectura actual.

Arquitectura de costos:
    - /agno/chat:  ~$0.02 por mensaje (solo LLM para formateo)
    - /agno/quote: ~$0.02 por cotización (pipeline determinístico + LLM)
    - Wolf API:    $0.00 por request (no usa LLM)
"""

from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.core.config import settings

logger = logging.getLogger("panelin.app")

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan (startup / shutdown)
# ─────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Panelin Agno iniciando...")
    logger.info(f"Modelo LLM: {settings.openai_model}")
    logger.info(f"MCP Server: {settings.mcp_server_url}")
    logger.info(f"DB configurada: {bool(settings.agno_db_url)}")
    yield
    logger.info("Panelin Agno deteniendo...")


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Panelin Agno API",
    description=(
        "Backend agentic para cotizaciones técnico-comerciales de paneles BMC Uruguay. "
        "Migrado desde GPT Custom GPT a arquitectura Agno con pipeline determinístico v4.0."
    ),
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Montar Wolf API existente (preservar todos los endpoints /api/*)
# ─────────────────────────────────────────────────────────────────────────────
try:
    from wolf_api.main import app as wolf_app
    app.mount("/api", wolf_app)
    logger.info("Wolf API montada en /api")
except Exception as e:
    logger.warning(f"Wolf API no pudo montarse: {e}. Continuando sin ella.")


# ─────────────────────────────────────────────────────────────────────────────
# Schemas Pydantic
# ─────────────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    user_id: Optional[str] = None


class QuoteRequest(BaseModel):
    text: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    force_mode: Optional[str] = None


class QuoteResponse(BaseModel):
    result: dict
    session_id: str


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints Agno
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/agno/health")
async def agno_health():
    """Health check del agente Agno."""
    return {
        "status": "ok",
        "service": "panelin-agno",
        "version": "4.0.0",
        "model": settings.openai_model,
        "db_configured": bool(settings.agno_db_url),
        "mcp_configured": bool(settings.mcp_server_url),
    }


@app.post("/agno/chat", response_model=ChatResponse)
async def agno_chat(request: ChatRequest):
    """Chat conversacional con el agente Panelin.

    Mantiene historial de conversación por sesión (si database_url está configurado).
    El agente clasifica intenciones y usa herramientas según el contexto.

    - Cotizaciones: invoca el motor panelin_v4 directamente
    - Consultas técnicas: verifica autoportancia, precios, etc.
    - Preguntas generales: responde con conocimiento del catálogo BMC
    """
    from src.agent.panelin import run_panelin_agent

    session_id = request.session_id or str(uuid.uuid4())

    if not settings.openai_api_key and not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY no configurado. El agente no puede procesar mensajes.",
        )

    response_text = await run_panelin_agent(
        message=request.message,
        session_id=session_id,
        user_id=request.user_id,
    )

    return ChatResponse(
        response=response_text,
        session_id=session_id,
        user_id=request.user_id,
    )


@app.post("/agno/quote")
async def agno_quote(request: QuoteRequest):
    """Cotización rápida usando el pipeline determinístico completo.

    Equivale a llamar directamente al motor panelin_v4 sin el agente conversacional.
    Ideal para integrations programáticas que necesitan el JSON de la cotización.
    Costo: $0.00 (motor Python puro, sin LLM).
    """
    from panelin_v4.engine.quotation_engine import process_quotation

    session_id = request.session_id or str(uuid.uuid4())

    output = process_quotation(
        text=request.text,
        force_mode=request.force_mode,
    )

    return {
        "session_id": session_id,
        "result": output.to_dict() if hasattr(output, "to_dict") else vars(output),
    }


@app.post("/agno/workflow")
async def agno_workflow(request: ChatRequest):
    """Ejecuta el workflow Agno completo (7 pasos determinísticos + LLM respuesta).

    A diferencia de /agno/quote (solo motor), este endpoint ejecuta el workflow
    completo con todos los Steps de Agno y retorna la respuesta formateada en español.
    Costo: ~$0.02 por cotización.
    """
    from src.agent.workflow import run_quotation_workflow

    session_id = request.session_id or str(uuid.uuid4())

    if not settings.openai_api_key and not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY no configurado",
        )

    response_text = await run_quotation_workflow(
        text=request.message,
        session_id=session_id,
        user_id=request.user_id,
    )

    return ChatResponse(
        response=response_text,
        session_id=session_id,
        user_id=request.user_id,
    )


@app.get("/")
async def root():
    """Raíz de la API — información del servicio."""
    return {
        "service": "Panelin Agno",
        "description": "Backend agentic para cotizaciones BMC Uruguay",
        "version": "4.0.0",
        "endpoints": {
            "agno_chat": "POST /agno/chat — Agente conversacional",
            "agno_quote": "POST /agno/quote — Cotización directa (sin LLM)",
            "agno_workflow": "POST /agno/workflow — Workflow completo",
            "wolf_api": "/api/* — API Wolf (KB, Sheets, PDF)",
            "docs": "/docs",
        },
    }


@app.get("/health")
async def health():
    """Health check principal (compatibilidad con Cloud Run)."""
    return {"status": "ok", "service": "panelin-agno", "version": "4.0.0"}


# ─────────────────────────────────────────────────────────────────────────────
# Entry point para desarrollo local
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "src.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
