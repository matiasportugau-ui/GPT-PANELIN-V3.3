"""
src/app.py — Panelin Agno API (FastAPI + Agno)

Punto de entrada principal que integra:
  1. Wolf API legacy (rutas existentes — no se rompe nada)
  2. Agno Chat API (nueva arquitectura agentic)
  3. Panelin Engine API (cotizaciones directas)

Las rutas legacy /calculate_quote, /sheets/*, /kb/* se preservan sin cambios.
Las rutas nuevas /v2/chat, /v2/quote usan el Agno Agent + Workflow.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from src.core.config import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Importar Wolf API base app (preserva todas las rutas legacy) ──────────────
from wolf_api.main import app as wolf_app  # noqa: E402

# Ampliar la app de Wolf API con las nuevas rutas v2
app = wolf_app

# Actualizar CORS con la configuración del settings
for middleware in app.middleware_stack.middlewares if hasattr(app, "middleware_stack") else []:
    pass  # CORS ya configurado en wolf_api/main.py via settings

# ── Schemas v2 ────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Solicitud de chat al agente Panelin."""
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str = Field(..., description="ID de sesión para memoria conversacional")
    user_id: Optional[str] = Field(None, description="ID del usuario (email o UUID)")
    mode: str = Field(default="pre_cotizacion", description="informativo|pre_cotizacion|formal")
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    client_location: Optional[str] = None
    use_workflow: bool = Field(
        default=True,
        description="Si True, usa el pipeline determinístico para cotizaciones",
    )


class ChatResponse(BaseModel):
    """Respuesta del agente Panelin."""
    ok: bool
    content: str
    session_id: str
    run_id: Optional[str] = None
    error: Optional[str] = None


class QuoteRequestV2(BaseModel):
    """Solicitud directa al engine de cotización (sin LLM)."""
    text: str = Field(..., min_length=1)
    mode: str = Field(default="pre_cotizacion")
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    client_location: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None


# ── Router v2 ─────────────────────────────────────────────────────────────────

v2_router = APIRouter(prefix="/v2", tags=["Panelin v2 (Agno)"])


@v2_router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    """Chat con el agente Panelin (Agno).

    Usa el Workflow determinístico para cotizaciones y el agente LLM para
    conversaciones generales. Memoria conversacional persistente por session_id.
    """
    from src.agent.panelin import run_panelin_chat

    try:
        result = await run_in_threadpool(
            lambda: __import__("asyncio").get_event_loop().run_until_complete(
                run_panelin_chat(
                    message=payload.message,
                    session_id=payload.session_id,
                    user_id=payload.user_id,
                    mode=payload.mode,
                    client_name=payload.client_name,
                    client_phone=payload.client_phone,
                    client_location=payload.client_location,
                    use_workflow=payload.use_workflow,
                )
            )
        )
        return ChatResponse(
            ok=True,
            content=result.get("content", ""),
            session_id=result.get("session_id", payload.session_id),
            run_id=result.get("run_id"),
        )
    except Exception as exc:
        logger.error("Error en /v2/chat: %s", exc, exc_info=True)
        return ChatResponse(
            ok=False,
            content="",
            session_id=payload.session_id,
            error=str(exc),
        )


@v2_router.post("/quote")
async def quote_v2(payload: QuoteRequestV2) -> dict:
    """Cotización directa al engine v4 (sin LLM, determinístico, < 1ms).

    Usa exclusivamente precios de la KB — nunca inventa.
    """
    from src.quotation.service import QuotationRequest, quotation_service

    try:
        request = QuotationRequest(
            text=payload.text,
            mode=payload.mode,
            client_name=payload.client_name,
            client_phone=payload.client_phone,
            client_location=payload.client_location,
            session_id=payload.session_id,
            user_id=payload.user_id,
        )
        result = await run_in_threadpool(quotation_service.run, request)
        return {"ok": True, "data": result.to_dict()}
    except Exception as exc:
        logger.error("Error en /v2/quote: %s", exc, exc_info=True)
        return {"ok": False, "error": str(exc)}


@v2_router.get("/health")
async def health_v2() -> dict:
    """Health check del stack Agno."""
    return {
        "ok": True,
        "version": "2.0.0",
        "agno": True,
        "model": settings.openai_model,
        "db_configured": bool(
            settings.database_url
            and not settings.database_url.endswith("localhost:5432/panelin")
        ),
        "mcp_url": settings.mcp_server_url,
    }


@v2_router.get("/session/{session_id}")
async def get_session(session_id: str) -> dict:
    """Obtiene el historial de sesión desde PostgreSQL."""
    db = None
    try:
        from src.agent.workflow import build_panelin_db
        db = build_panelin_db()
        if db is None:
            return {"ok": False, "error": "PostgreSQL no configurado"}

        from src.agent.panelin import build_panelin_agent
        agent = build_panelin_agent(session_id=session_id, db=db)
        history = agent.get_chat_history(session_id=session_id)
        return {"ok": True, "session_id": session_id, "history": history or []}
    except Exception as exc:
        logger.error("Error obteniendo sesión %s: %s", session_id, exc)
        return {"ok": False, "error": str(exc)}


# Incluir el router v2 en la app principal
app.include_router(v2_router)


# ── Root ──────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Sistema"])
async def root() -> dict:
    return {
        "service": "Panelin API",
        "version": "4.0.0",
        "agno": "2.x",
        "status": "ok",
        "endpoints": {
            "legacy": "/calculate_quote, /sheets/*, /kb/*",
            "v2": "/v2/chat, /v2/quote, /v2/health, /v2/session/{id}",
            "engine": "/api/quote, /api/validate, /api/sai-score",
            "docs": "/docs",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.app:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        reload=False,
    )
