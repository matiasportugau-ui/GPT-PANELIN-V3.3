"""Panelin v4 — Agno Architecture Entry Point.

FastAPI app que expone:
- /v4/chat           — Endpoint conversacional (POST)
- /v4/quote          — Ejecuta el workflow determinístico completo (POST)
- /v4/health         — Health check
- /v4/agent/run      — Agente en modo sync
- /v4/workflow/run   — Workflow pipeline directo
- Wolf API legacy routes preservadas en /calculate_quote, /sheets/*, /kb/*

Nota: Para el Agno Playground completo con 50+ endpoints AgentOS,
usar `agno app serve src.app:app` desde CLI de Agno.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Startup / Shutdown
# ─────────────────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup, clean up on shutdown."""
    logger.info("Panelin v4 arrancando (Agno Architecture)...")

    # Pre-load the engine to warm up the KB caches
    try:
        from src.quotation.service import QuotationService
        svc = QuotationService()
        app.state.quotation_service = svc
        logger.info("QuotationService inicializado OK")
    except Exception as exc:
        logger.warning("QuotationService no disponible: %s", exc)
        app.state.quotation_service = None

    # Initialize DB (optional — won't fail if not configured)
    from src.agent.panelin import get_postgres_db
    db = get_postgres_db()
    app.state.db = db

    yield

    logger.info("Panelin v4 cerrando...")


# ─────────────────────────────────────────────────────────────────────────────
# App factory
# ─────────────────────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    """Crea y configura la aplicación FastAPI."""
    from src.core.config import get_settings
    settings = get_settings()

    app = FastAPI(
        title="Panelin API v4",
        description=(
            "Sistema de cotizaciones técnico-comerciales BMC Uruguay — "
            "Arquitectura Agno con pipeline determinístico v4"
        ),
        version="4.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS — origins desde env o wildcard en development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.effective_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount Wolf API legacy routes
    _mount_wolf_api(app)

    # Register v4 routes
    app.include_router(_build_v4_router(), prefix="/v4")

    return app


def _mount_wolf_api(app: FastAPI) -> None:
    """Monta las rutas legadas del Wolf API para compatibilidad backwards."""
    try:
        from wolf_api.main import app as wolf_app
        # Mount the Wolf API as a sub-application
        app.mount("/wolf", wolf_app)
        logger.info("Wolf API montado en /wolf")
    except Exception as exc:
        logger.warning("Wolf API no disponible: %s", exc)


def _build_v4_router():
    """Construye el router v4 con todos los endpoints del agente Agno."""
    from fastapi import APIRouter

    router = APIRouter(tags=["Panelin v4 — Agno"])

    # ── Health ──────────────────────────────────────────────────────────────

    @router.get("/health")
    async def health():
        return {
            "status": "ok",
            "version": "4.0.0",
            "architecture": "agno",
            "pipeline": "panelin_v4",
        }

    # ── Chat — Conversational Agent ─────────────────────────────────────────

    class ChatRequest(BaseModel):
        message: str = Field(..., min_length=1, max_length=4000)
        session_id: Optional[str] = Field(None, description="ID de sesión para memoria conversacional")
        user_id: Optional[str] = Field(None, description="ID de usuario")
        stream: bool = Field(False, description="Si True, retorna respuesta como SSE stream")

    class ChatResponse(BaseModel):
        reply: str
        session_id: Optional[str] = None
        tool_calls_made: int = 0

    @router.post("/chat", response_model=ChatResponse)
    async def chat(req: ChatRequest, request: Request):
        """Endpoint conversacional — el agente Panelin responde en español."""
        db = getattr(request.app.state, "db", None)

        from src.agent.panelin import build_panelin_agent
        agent = build_panelin_agent(
            db=db,
            session_id=req.session_id,
            user_id=req.user_id,
        )

        try:
            response = agent.run(req.message)
            reply = response.content if hasattr(response, "content") else str(response)
            tool_count = len(response.tool_calls) if hasattr(response, "tool_calls") and response.tool_calls else 0
            return ChatResponse(
                reply=reply,
                session_id=req.session_id or getattr(agent, "session_id", None),
                tool_calls_made=tool_count,
            )
        except Exception as exc:
            logger.error("chat error: %s", exc)
            raise HTTPException(status_code=500, detail=f"Error del agente: {exc}")

    # ── Quote — Direct workflow execution ───────────────────────────────────

    class QuoteRequest(BaseModel):
        texto: str = Field(..., min_length=5, max_length=2000, description="Descripción del proyecto en español")
        modo: Optional[str] = Field(None, description="'informativo', 'pre_cotizacion' o 'formal'")
        session_id: Optional[str] = None
        user_id: Optional[str] = None

    @router.post("/quote")
    async def quote(req: QuoteRequest, request: Request):
        """Ejecuta el pipeline determinístico v4 directamente (sin conversación).

        Ideal para integraciones programáticas donde se quiere el resultado
        estructurado del pipeline, no una respuesta conversacional.
        """
        db = getattr(request.app.state, "db", None)

        from src.agent.workflow import build_panelin_workflow
        workflow = build_panelin_workflow(
            db=db,
            session_id=req.session_id,
            user_id=req.user_id,
        )

        try:
            result = workflow.run(input=req.texto)
            step_results = {}
            if result.step_results:
                for sr in result.step_results:
                    step_results[sr.step_name] = sr.content
            return {
                "ok": True,
                "content": result.content,
                "step_results": step_results,
                "session_id": req.session_id,
            }
        except Exception as exc:
            logger.error("quote workflow error: %s", exc)
            raise HTTPException(status_code=500, detail=f"Error en el pipeline: {exc}")

    # ── Quick quote — Sync service call ────────────────────────────────────

    class QuickQuoteRequest(BaseModel):
        texto: str = Field(..., min_length=5, max_length=2000)
        modo: Optional[str] = None

    @router.post("/quick-quote")
    async def quick_quote(req: QuickQuoteRequest, request: Request):
        """Cotización rápida usando solo el engine determinístico (sin LLM).

        Retorna el JSON del pipeline completo. Costo: $0.00.
        Ideal para verificaciones programáticas y tests de integración.
        """
        svc = getattr(request.app.state, "quotation_service", None)
        if svc is None:
            raise HTTPException(status_code=503, detail="QuotationService no disponible")

        try:
            result = svc.process(req.texto, mode=req.modo)
            return {"ok": True, "result": result}
        except Exception as exc:
            logger.error("quick_quote error: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc))

    # ── Batch quote ─────────────────────────────────────────────────────────

    class BatchRequest(BaseModel):
        textos: list[str] = Field(..., min_length=1, max_length=50)

    @router.post("/batch-quote")
    async def batch_quote(req: BatchRequest, request: Request):
        """Procesa múltiples cotizaciones en lote (sin LLM). Costo: $0.00."""
        svc = getattr(request.app.state, "quotation_service", None)
        if svc is None:
            raise HTTPException(status_code=503, detail="QuotationService no disponible")

        try:
            results = svc.batch(req.textos)
            return {"ok": True, "total": len(results), "results": results}
        except Exception as exc:
            logger.error("batch_quote error: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc))

    # ── Price check ─────────────────────────────────────────────────────────

    @router.get("/price/{familia}/{sub_familia}/{espesor_mm}")
    async def get_price(familia: str, sub_familia: str, espesor_mm: int):
        """Consulta precio por m² desde KB. NUNCA inventa precios."""
        try:
            from panelin_v4.engine.pricing_engine import _find_panel_price_m2
            price = _find_panel_price_m2(familia, sub_familia, espesor_mm)
            if price is None:
                return {
                    "available": False,
                    "message": f"Precio no disponible para {familia} {sub_familia} {espesor_mm}mm",
                }
            return {
                "available": True,
                "familia": familia,
                "sub_familia": sub_familia,
                "espesor_mm": espesor_mm,
                "precio_m2_usd": price,
                "iva_incluido": True,
            }
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    # ── Autoportancia check ──────────────────────────────────────────────────

    @router.get("/autoportancia/{familia}/{sub_familia}/{espesor_mm}/{luz_m}")
    async def check_autoportancia(familia: str, sub_familia: str, espesor_mm: int, luz_m: float):
        """Verifica si un panel soporta una determinada luz entre apoyos."""
        try:
            from panelin_v4.engine.sre_engine import calculate_sre
            from panelin_v4.engine.parser import QuoteRequest
            req = QuoteRequest(
                familia=familia,
                sub_familia=sub_familia,
                thickness_mm=espesor_mm,
                span_m=luz_m,
                uso="techo",
            )
            result = calculate_sre(req)
            from src.agent.workflow import _dataclass_to_dict
            return {"ok": True, "result": _dataclass_to_dict(result)}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    return router


# ─────────────────────────────────────────────────────────────────────────────
# Application instance
# ─────────────────────────────────────────────────────────────────────────────

app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.app:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8080")),
        reload=os.environ.get("DEBUG", "false").lower() == "true",
        log_level=os.environ.get("LOG_LEVEL", "info").lower(),
    )
