"""
Panelin v5.0 - Agno Application Entry Point
==============================================

Serves the Panelin agent via Agno Playground, exposing 50+ AgentOS
endpoints automatically. Also mounts the legacy Wolf API for backward
compatibility.

Usage:
    # Development (with auto-reload)
    python -m src.app

    # Production (via uvicorn)
    uvicorn src.app:app --host 0.0.0.0 --port 8080

    # With Agno Playground UI
    Visit https://app.agno.com/playground after starting the server
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.config import get_settings
from src.agent.panelin import create_panelin_agent
from src.agent.workflow import create_quotation_workflow

logger = logging.getLogger(__name__)

_mcp_tools = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager.

    Initializes MCP connection on startup, cleans up on shutdown.
    """
    global _mcp_tools
    settings = get_settings()

    # Initialize MCP tools if configured
    if settings.mcp.url:
        try:
            from agno.tools.mcp import MCPTools
            _mcp_tools = MCPTools(
                transport=settings.mcp.transport,
                url=settings.mcp.url,
            )
            await _mcp_tools.connect()
            logger.info(f"Connected to MCP server at {settings.mcp.url}")
        except Exception as e:
            logger.warning(f"MCP connection failed (non-fatal): {e}")
            _mcp_tools = None

    yield

    # Cleanup
    if _mcp_tools:
        try:
            await _mcp_tools.close()
        except Exception:
            pass


def _create_storage():
    """Create PostgresStorage if database is configured."""
    settings = get_settings()
    if not settings.db.password:
        logger.info("Database not configured — running without session persistence")
        return None

    try:
        from agno.storage.postgres import PostgresStorage
        storage = PostgresStorage(
            table_name="panelin_sessions",
            db_url=settings.db.url,
        )
        logger.info("PostgresStorage initialized")
        return storage
    except Exception as e:
        logger.warning(f"PostgresStorage init failed (non-fatal): {e}")
        return None


def _get_agents():
    """Create and return all agents/workflows for AgentOS."""
    settings = get_settings()
    storage = _create_storage()

    agent = create_panelin_agent(
        provider=settings.llm.provider,
        model_id=settings.llm.model_id,
        storage=storage,
        mcp_tools=_mcp_tools,
    )

    workflow = create_quotation_workflow(
        model_id=settings.llm.model_id,
        storage=storage,
    )

    return [agent, workflow]


# Create the FastAPI app
app = FastAPI(
    title="Panelin API v5.0",
    description="BMC Uruguay - Sistema de Cotizaciones con Agno Framework",
    version="5.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {
        "service": "Panelin API",
        "version": "5.0.0",
        "architecture": "agno",
        "status": "ok",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "mcp_connected": _mcp_tools is not None,
    }


# Mount legacy Wolf API routes for backward compatibility
try:
    from wolf_api.main import app as wolf_app
    app.mount("/wolf", wolf_app)
    logger.info("Wolf API mounted at /wolf")
except ImportError:
    logger.info("Wolf API not available — skipping mount")


# Mount Panelin v4 engine API routes
from panelin_v4.engine.classifier import OperatingMode
from panelin_v4.engine.quotation_engine import process_quotation
from panelin_v4.evaluator.sai_engine import calculate_sai as calc_sai
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool


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


def _resolve_mode(raw_mode: str | None) -> OperatingMode:
    mode_key = (raw_mode or "pre_cotizacion").strip().lower()
    if mode_key not in MODE_MAP:
        valid = ", ".join(sorted(MODE_MAP.keys()))
        raise ValueError(f"Invalid mode '{raw_mode}'. Valid: {valid}")
    return MODE_MAP[mode_key]


@app.post("/api/quote")
async def api_quote(payload: EngineInput):
    try:
        mode = _resolve_mode(payload.mode)
        output = await run_in_threadpool(
            process_quotation,
            text=payload.text,
            force_mode=mode,
            client_name=payload.client_name,
            client_phone=payload.client_phone,
            client_location=payload.client_location,
        )
        return {"ok": True, "data": output.to_dict()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@app.post("/api/sai-score")
async def api_sai_score(payload: EngineInput):
    try:
        mode = _resolve_mode(payload.mode)
        output = await run_in_threadpool(
            process_quotation,
            text=payload.text,
            force_mode=mode,
            client_name=payload.client_name,
            client_phone=payload.client_phone,
            client_location=payload.client_location,
        )
        sai = calc_sai(output)
        return {"ok": True, "data": {
            "quote_id": output.quote_id,
            "sai": sai.to_dict(),
        }}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# Agno Playground endpoint for agent interaction
@app.post("/api/chat")
async def api_chat(payload: dict):
    """Chat endpoint for the Panelin agent.

    Accepts: {"message": "...", "session_id": "..."}
    Returns: {"response": "...", "session_id": "..."}
    """
    message = payload.get("message", "")
    session_id = payload.get("session_id")

    settings = get_settings()
    storage = _create_storage()

    agent = create_panelin_agent(
        provider=settings.llm.provider,
        model_id=settings.llm.model_id,
        storage=storage,
        session_id=session_id,
        mcp_tools=_mcp_tools,
    )

    response = await agent.arun(message)
    return {
        "response": response.content,
        "session_id": session_id or getattr(response, "session_id", None),
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.app:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
    )
