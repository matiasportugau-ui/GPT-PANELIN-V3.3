"""
Panelin Agno — Application Entry Point

Serves the Panelin agent via Agno Playground, which provides:
- Chat API endpoints (POST /v1/runs)
- Session management (CRUD)
- Memory management (CRUD)
- Health checks
- Interactive API docs at /docs

Also mounts the existing Wolf API routes for backward compatibility.
"""

from __future__ import annotations

import logging
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.agent.panelin import (
    create_panelin_agent,
    create_db,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("panelin.app")


def create_app() -> FastAPI:
    """Create the FastAPI application with Agno Playground + Wolf API."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="Panelin Agno — Sistema de cotizaciones para paneles BMC Uruguay",
        version=settings.version,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    cors_origins = settings.security.cors_allowed_origins
    allowed_origins = [o.strip() for o in cors_origins.split(",") if o.strip()] if cors_origins else []
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": settings.version, "service": "panelin-agno"}

    @app.get("/ready")
    async def ready():
        return {
            "status": "ready",
            "version": settings.version,
            "environment": settings.environment,
            "llm_provider": settings.llm.provider,
            "llm_model": settings.llm.model_id,
        }

    db = create_db(settings)
    agent = create_panelin_agent(db=db)

    try:
        from agno.os import AgentOS

        agent_os = AgentOS(
            name="Panelin",
            agents=[agent],
            base_app=app,
            cors_allowed_origins=allowed_origins or None,
        )
        app = agent_os.get_app()
        logger.info("AgentOS mounted — endpoints: /agents, /sessions, /memories, /docs")
    except ImportError:
        logger.warning("agno.os not available — running without AgentOS endpoints")
    except Exception as e:
        logger.warning(f"AgentOS init failed: {e} — running without AgentOS endpoints")

    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from wolf_api.main import app as wolf_app
        for route in wolf_app.routes:
            if hasattr(route, "path") and route.path not in ("/health", "/ready", "/docs", "/redoc", "/openapi.json"):
                app.routes.append(route)
        logger.info("Wolf API routes mounted for backward compatibility")
    except ImportError:
        logger.warning("wolf_api not available — Wolf API routes not mounted")
    except Exception as e:
        logger.warning(f"Failed to mount Wolf API routes: {e}")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
