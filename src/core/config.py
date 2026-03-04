"""
Panelin Agno — Configuración centralizada
==========================================

Fuente única de verdad para toda la configuración de la aplicación.
Usa pydantic-settings para validación y carga desde variables de entorno.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings


KB_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Configuración global de Panelin Agno.

    Todas las variables se leen desde el entorno. No hay defaults con
    credenciales — si una variable requerida falta, la app falla al iniciar.
    """

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False}

    # ── Servidor ─────────────────────────────────────────────────────────────
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8080)
    debug: bool = Field(default=False)
    environment: str = Field(default="production")

    # ── Seguridad ─────────────────────────────────────────────────────────────
    wolf_api_key: str = Field(default="", description="API key para autenticación HTTP")
    kb_write_password: str = Field(default="", description="Password para escritura en KB")
    wolf_kb_write_password: str = Field(default="", description="Password MCP para file_ops y wolf_kb_write")
    cors_origins: str = Field(default="", description="Orígenes CORS separados por coma")

    @property
    def cors_origins_list(self) -> List[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        return origins if origins else ["*"]

    # ── Base de datos (Cloud SQL / PostgreSQL) ─────────────────────────────
    database_url: str = Field(
        default="",
        description="PostgreSQL connection string (postgresql+psycopg://user:pass@host/db)",
    )

    @property
    def agno_db_url(self) -> str:
        """URL para Agno PostgresDb (psycopg driver, no asyncpg)."""
        url = self.database_url
        if url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
        return url

    # ── LLM ─────────────────────────────────────────────────────────────────
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o-mini", description="Modelo LLM para formateo de respuestas")
    anthropic_api_key: str = Field(default="", description="Anthropic API key (opcional, para fallback)")

    # ── MCP Server ───────────────────────────────────────────────────────────
    mcp_server_url: str = Field(
        default="http://localhost:8000/sse",
        description="URL del servidor MCP (SSE transport)",
    )
    wolf_api_url: str = Field(
        default="https://panelin-api-642127786762.us-central1.run.app",
        description="URL base del Wolf API en Cloud Run",
    )

    # ── Google Cloud ─────────────────────────────────────────────────────────
    kb_gcs_bucket: str = Field(default="", description="GCS bucket para KB JSONL")
    sheets_spreadsheet_id: str = Field(default="", description="ID de Google Sheets principal")
    sheets_tab_2026: str = Field(default="2026")
    sheets_tab_admin: str = Field(default="Admin.")
    sheets_cotizaciones_id: str = Field(default="")

    # ── Knowledge Base (rutas de archivos) ───────────────────────────────────
    pricing_master_path: Path = Field(
        default=KB_ROOT / "bromyros_pricing_master.json",
    )
    accessories_catalog_path: Path = Field(
        default=KB_ROOT / "accessories_catalog.json",
    )
    bom_rules_path: Path = Field(
        default=KB_ROOT / "bom_rules.json",
    )
    bmc_kb_path: Path = Field(
        default=KB_ROOT / "BMC_Base_Conocimiento_GPT-2.json",
    )

    # ── Agno Session Tables ──────────────────────────────────────────────────
    agent_session_table: str = Field(default="panelin_agent_sessions")
    workflow_session_table: str = Field(default="panelin_workflow_sessions")

    # ── Negocio ──────────────────────────────────────────────────────────────
    iva_rate: float = Field(default=0.22, description="Tasa IVA Uruguay")
    currency: str = Field(default="USD")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retorna la instancia singleton de configuración."""
    return Settings()


settings = get_settings()
