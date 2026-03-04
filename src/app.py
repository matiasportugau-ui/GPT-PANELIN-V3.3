"""
Panelin Agno — Punto de Entrada Principal
==========================================

Expone el agente Panelin via AgentOS con todos los endpoints automáticos:
  - /health — Health check
  - /v1/agents/{agent_id}/runs — Crear/continuar conversación
  - /v1/agents/{agent_id}/sessions — Gestión de sesiones
  - /v1/agents/{agent_id}/memory — Memoria conversacional
  - /docs — Swagger UI
  + 50+ endpoints adicionales de AgentOS

También monta los endpoints legacy de Wolf API para backward compatibility.

Uso:
    uvicorn src.app:app --host 0.0.0.0 --port 8080
    # o para desarrollo:
    python -m src.app
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


def _build_db():
    """Construye la conexión PostgreSQL para persistencia de sesiones y memoria."""
    from src.core.config import get_settings
    from agno.db.postgres import PostgresDb

    settings = get_settings()
    if not settings.database_url or settings.database_url.startswith("postgresql://panelin:panelin@localhost"):
        logger.warning("DATABASE_URL no configurada o usando default local. Sesiones no persistidas.")
        return None

    try:
        db = PostgresDb(
            db_url=settings.database_url,
            db_schema=settings.db_schema,
            create_schema=True,
        )
        return db
    except Exception as exc:
        logger.warning(f"No se pudo conectar a PostgreSQL: {exc}. Continuando sin persistencia.")
        return None


def build_agent_os():
    """Construye el AgentOS con el agente Panelin y todos sus componentes."""
    from agno.os import AgentOS
    from src.agent.panelin import build_panelin_agent_with_mcp
    from src.agent.workflow import build_quotation_workflow
    from src.core.config import get_settings

    settings = get_settings()

    db = _build_db()

    # Agente conversacional principal
    panelin_agent = build_panelin_agent_with_mcp(db=db)

    # Workflow determinístico (pipeline v4.0)
    quotation_workflow = build_quotation_workflow(db=db)

    agent_os = AgentOS(
        id="panelin-agno",
        name="Panelin AgentOS",
        description="Sistema de cotizaciones técnico-comerciales BMC Uruguay — Agno Framework",
        version="4.0.0",
        db=db,
        agents=[panelin_agent],
        workflows=[quotation_workflow],
        cors_allowed_origins=settings.cors_allow_origins,
        tracing=settings.is_production,
        auto_provision_dbs=True,
        telemetry=False,
    )

    return agent_os


def create_app() -> FastAPI:
    """Factory principal de la aplicación FastAPI.

    Monta:
      1. AgentOS con todos sus endpoints automáticos
      2. Endpoints legacy de Wolf API (backward compatibility)
      3. Middleware de CORS

    Returns:
        Aplicación FastAPI lista para servir.
    """
    from src.core.config import get_settings
    from wolf_api.main import app as wolf_app

    settings = get_settings()

    # Crear base app con la misma configuración de Wolf API legacy
    base_app = FastAPI(
        title="Panelin Agno API",
        description=(
            "Sistema de cotizaciones BMC Uruguay con Agno Framework. "
            "Incluye endpoints AgentOS + API legacy Wolf."
        ),
        version="4.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS desde configuración (no hardcodeado)
    base_app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Montar endpoints legacy Wolf API bajo /api/v3
    base_app.mount("/api/v3", wolf_app)

    # Crear AgentOS y obtener su FastAPI app
    try:
        agent_os = build_agent_os()
        # AgentOS se integra en base_app (preserva nuestras rutas)
        agent_os_instance = agent_os
        agent_os_app = agent_os.get_app()

        # Montar AgentOS en /agno para acceso directo
        base_app.mount("/agno", agent_os_app)

        logger.info("AgentOS montado correctamente en /agno")
    except Exception as exc:
        logger.error(f"Error inicializando AgentOS: {exc}. API legacy disponible en /api/v3")

    return base_app


# Instancia de la app para uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.app:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8080")),
        reload=os.environ.get("ENVIRONMENT", "development") == "development",
        log_level="info",
    )
