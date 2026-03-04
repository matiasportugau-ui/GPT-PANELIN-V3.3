"""
Panelin v5.0 — Agno Application Entry Point
===============================================

Serves the Panelin agent via Agno Playground, exposing:
- Agent endpoints (/v1/agents/{id}/runs)
- Workflow endpoints (/v1/workflows/{id}/runs)
- Health check (/health)
- Legacy Wolf API routes (preserved for backward compatibility)

Run with: uvicorn src.app:app --host 0.0.0.0 --port 8080
"""

from __future__ import annotations

import logging
import os

from agno.playground import Playground

from src.agent.panelin import build_panelin_agent
from src.agent.workflow import build_quotation_workflow
from src.core.config import get_settings

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

# ── Build Agent ──
panelin_agent = build_panelin_agent(
    model_id=settings.default_model_id,
    enable_mcp=bool(settings.mcp_server_url),
)

# ── Build Workflow ──
quotation_workflow = build_quotation_workflow(
    model_id=settings.default_model_id,
)

# ── Playground ──
playground = Playground(
    agents=[panelin_agent],
    workflows=[quotation_workflow],
)

app = playground.get_app()


# ── Mount legacy Wolf API for backward compatibility ──

def _mount_legacy_api():
    """Mount the existing Wolf API routes under /legacy/ prefix."""
    try:
        from wolf_api.main import app as wolf_app
        from fastapi import APIRouter
        from starlette.routing import Mount

        app.mount("/legacy", wolf_app)
        logger.info("Legacy Wolf API mounted at /legacy/*")
    except Exception as e:
        logger.warning("Could not mount legacy Wolf API: %s", e)


def _mount_panelin_v4_api():
    """Mount the Panelin v4 engine API routes."""
    try:
        from fastapi import APIRouter
        from pydantic import BaseModel, Field
        from starlette.concurrency import run_in_threadpool

        from panelin_v4.engine.classifier import OperatingMode
        from panelin_v4.engine.quotation_engine import process_quotation
        from panelin_v4.evaluator.sai_engine import calculate_sai

        router = APIRouter(prefix="/api/v4", tags=["Panelin v4 Engine"])

        class EngineInput(BaseModel):
            text: str = Field(..., min_length=1)
            mode: str = Field(default="pre_cotizacion")
            client_name: str | None = None
            client_phone: str | None = None
            client_location: str | None = None

        MODE_MAP = {
            "informativo": OperatingMode.INFORMATIVO,
            "pre_cotizacion": OperatingMode.PRE_COTIZACION,
            "formal": OperatingMode.FORMAL,
        }

        def _run_quote(payload: EngineInput) -> dict:
            mode = MODE_MAP.get(payload.mode, OperatingMode.PRE_COTIZACION)
            output = process_quotation(
                text=payload.text,
                force_mode=mode,
                client_name=payload.client_name,
                client_phone=payload.client_phone,
                client_location=payload.client_location,
            )
            return output.to_dict()

        @router.post("/quote")
        async def quote(payload: EngineInput):
            try:
                data = await run_in_threadpool(_run_quote, payload)
                return {"ok": True, "data": data}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

        @router.get("/health")
        async def engine_health():
            return {"status": "healthy", "engine": "panelin_v4"}

        app.include_router(router)
        logger.info("Panelin v4 engine API mounted at /api/v4/*")
    except Exception as e:
        logger.warning("Could not mount Panelin v4 API: %s", e)


# ── Health endpoint ──

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "panelin",
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/")
async def root():
    return {
        "service": "Panelin v5.0",
        "description": "Agno-powered quotation system for BMC Uruguay",
        "version": settings.app_version,
        "endpoints": {
            "playground": "/v1/playground",
            "agent_runs": "/v1/agents/Panelin/runs",
            "workflow_runs": "/v1/workflows/PanelinQuotationWorkflow/runs",
            "engine_v4": "/api/v4/quote",
            "legacy": "/legacy/",
            "health": "/health",
            "docs": "/docs",
        },
    }


_mount_legacy_api()
_mount_panelin_v4_api()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
