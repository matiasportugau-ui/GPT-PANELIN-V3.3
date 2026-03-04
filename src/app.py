"""
Panelin v5.0 — AgentOS Application Entry Point

Exposes the Panelin agent and QuotationWorkflow via AgentOS, which
auto-generates 50+ REST endpoints including:
    - POST /v1/agents/{agent_id}/runs  — Run the agent
    - POST /v1/workflows/{workflow_id}/runs — Run the workflow
    - Session management, tracing, health checks

Usage:
    python -m src.app          # Start with uvicorn
    ag run src/app.py          # Start with Agno CLI

The legacy Wolf API routes are mounted alongside AgentOS routes.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.core.config import get_settings
from src.agent.panelin import create_panelin_agent
from src.agent.workflow import create_quotation_workflow


settings = get_settings()


def _build_db():
    """Build PostgresDb if DATABASE_URL is configured."""
    if not settings.database_url:
        return None
    try:
        from agno.db.postgres import PostgresDb
        return PostgresDb(
            db_url=settings.database_url,
            session_table=settings.db_session_table,
            memory_table=settings.db_memory_table,
            auto_upgrade_schema=True,
        )
    except Exception:
        return None


def _build_mcp_tools():
    """Build MCPTools if MCP server URL is configured."""
    if not settings.mcp_server_url:
        return None
    try:
        from agno.tools.mcp import MCPTools
        return MCPTools(
            url=settings.mcp_server_url,
            transport=settings.mcp_transport,
        )
    except Exception:
        return None


db = _build_db()
mcp_tools = _build_mcp_tools()

panelin_agent = create_panelin_agent(
    db=db,
    mcp_tools=mcp_tools,
)

quotation_workflow = create_quotation_workflow(db=db)

try:
    from agno.os.app import AgentOS

    agent_os = AgentOS(
        name="Panelin",
        description="Sistema de cotizaciones BMC Uruguay — paneles de construcción",
        version=settings.app_version,
        db=db,
        agents=[panelin_agent],
        workflows=[quotation_workflow],
        cors_allowed_origins=settings.cors_origins_list or ["*"],
    )
    app = agent_os.get_app()
except ImportError:
    from fastapi import FastAPI
    app = FastAPI(
        title="Panelin API v5",
        version=settings.app_version,
    )

    @app.get("/")
    async def root():
        return {"service": "Panelin API", "version": settings.app_version}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}


try:
    from wolf_api.main import app as wolf_app
    from starlette.routing import Mount

    for route in wolf_app.routes:
        if hasattr(route, "path") and route.path not in ("/", "/docs", "/redoc", "/openapi.json"):
            app.routes.append(route)
except ImportError:
    pass


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", settings.port))
    uvicorn.run(
        "src.app:app",
        host="0.0.0.0",
        port=port,
        reload=not settings.is_production,
    )
