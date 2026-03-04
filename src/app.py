"""AgentOS application entrypoint for Panelin migration."""

from __future__ import annotations

import logging

from agno.db.base import AsyncBaseDb, BaseDb
from agno.db.in_memory import InMemoryDb
from agno.db.postgres import PostgresDb
from agno.os import AgentOS

from src.agent.panelin import build_panelin_agent
from src.agent.workflow import build_panelin_workflow
from src.core.config import Settings, get_settings
from src.quotation.service import QuotationService
from wolf_api.main import app as wolf_api_app

logger = logging.getLogger(__name__)


def _build_db(settings: Settings) -> BaseDb | AsyncBaseDb:
    if settings.use_in_memory_db or not settings.resolved_db_url:
        logger.warning(
            "Using InMemoryDb for AgentOS sessions. Configure PANELIN_DB_URL or Cloud SQL vars for persistence."
        )
        return InMemoryDb()

    return PostgresDb(
        id="panelin-postgres-db",
        db_url=settings.resolved_db_url,
        db_schema=settings.db_schema,
        session_table=settings.session_table,
        memory_table=settings.memory_table,
        traces_table=settings.traces_table,
        spans_table=settings.spans_table,
        create_schema=True,
    )


def create_agent_os(settings: Settings | None = None) -> AgentOS:
    config = settings or get_settings()
    db = _build_db(config)
    service = QuotationService()

    panelin_agent = build_panelin_agent(config, db=db, service=service)
    panelin_workflow = build_panelin_workflow(config, db=db, service=service)

    return AgentOS(
        id="panelin-agentos",
        name=config.app_name,
        description="Panelin AgentOS: agente conversacional + workflow determinístico.",
        version=config.app_version,
        db=db,
        agents=[panelin_agent],
        workflows=[panelin_workflow],
        base_app=wolf_api_app,
        on_route_conflict="preserve_base_app",
        cors_allowed_origins=config.cors_allow_origins or None,
        authorization=config.agentos_enable_auth,
        tracing=config.agentos_enable_tracing,
        enable_mcp_server=config.agentos_enable_mcp_server,
        auto_provision_dbs=True,
    )


agent_os = create_agent_os()
app = agent_os.get_app()
