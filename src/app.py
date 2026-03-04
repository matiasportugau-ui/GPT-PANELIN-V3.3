"""Agno + AgentOS entrypoint for Panelin migration."""

from __future__ import annotations

import importlib
import os

from agno.os import AgentOS

from src.agent.panelin import build_panelin_agent
from src.agent.workflow import build_panelin_workflow
from src.core.config import get_settings


def create_app():
    settings = get_settings()
    shared_db = settings.build_postgres_db()

    workflow = build_panelin_workflow(settings=settings)
    agent = build_panelin_agent(settings=settings, workflow=workflow, db=shared_db)

    legacy_app_module = importlib.import_module("app")
    legacy_app = getattr(legacy_app_module, "app")

    agent_os = AgentOS(
        id="panelin-agent-os",
        name="Panelin AgentOS",
        description="AgentOS for GPT-PANELIN migration with deterministic workflow backend.",
        db=shared_db,
        agents=[agent],
        workflows=[workflow],
        base_app=legacy_app,
        on_route_conflict="preserve_base_app",
        authorization=settings.panelin_enable_authorization,
        authorization_config=settings.build_authorization_config(),
        tracing=settings.panelin_enable_tracing,
        telemetry=settings.panelin_enable_telemetry,
        cors_allowed_origins=settings.cors_origins or None,
    )
    return agent_os.get_app()


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
