"""
Panelin Agno — Configuración Central
======================================

Single source of truth para toda la configuración del sistema.
Utiliza pydantic-settings para validación de variables de entorno.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

KB_ROOT = Path(__file__).resolve().parent.parent.parent


class PanelinSettings(BaseSettings):
    """Configuración global de Panelin Agno."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── LLM Provider ────────────────────────────────────────────────────────
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    default_model: str = Field(default="gpt-4o", alias="PANELIN_DEFAULT_MODEL")

    # ─── Database (Cloud SQL PostgreSQL) ─────────────────────────────────────
    database_url: str = Field(
        default="postgresql://panelin:panelin@localhost:5432/panelin",
        alias="DATABASE_URL",
    )
    db_schema: str = Field(default="panelin", alias="DB_SCHEMA")

    # ─── API Security ─────────────────────────────────────────────────────────
    wolf_api_key: str = Field(default="", alias="WOLF_API_KEY")
    kb_write_password: str = Field(default="", alias="KB_WRITE_PASSWORD")
    jwt_secret: str = Field(default="", alias="JWT_SECRET")
    # Raw string — parse via property. pydantic-settings treats List[str] env
    # vars as JSON arrays and errors on comma-separated strings.
    cors_allow_origins_raw: str = Field(
        default="http://localhost:3000",
        alias="CORS_ALLOW_ORIGINS",
    )

    @property
    def cors_allow_origins(self) -> List[str]:
        """Parses CORS_ALLOW_ORIGINS as comma-separated string."""
        raw = self.cors_allow_origins_raw.strip()
        if not raw:
            return ["http://localhost:3000"]
        return [o.strip() for o in raw.split(",") if o.strip()]

    # ─── MCP Server ───────────────────────────────────────────────────────────
    mcp_server_url: str = Field(
        default="http://localhost:8000/sse",
        alias="MCP_SERVER_URL",
    )
    mcp_server_timeout: int = Field(default=30, alias="MCP_SERVER_TIMEOUT")

    # ─── GCS / Knowledge Base ─────────────────────────────────────────────────
    kb_gcs_bucket: str = Field(default="", alias="KB_GCS_BUCKET")
    google_application_credentials: str = Field(
        default="", alias="GOOGLE_APPLICATION_CREDENTIALS"
    )

    # ─── Google Sheets CRM ────────────────────────────────────────────────────
    sheets_crm_id: str = Field(default="", alias="SHEETS_CRM_ID")
    sheets_service_account_json: str = Field(
        default="", alias="SHEETS_SERVICE_ACCOUNT_JSON"
    )

    # ─── AgentOS / Playground ─────────────────────────────────────────────────
    agno_playground_enabled: bool = Field(default=True, alias="AGNO_PLAYGROUND_ENABLED")
    agno_api_key: str = Field(default="", alias="AGNO_API_KEY")

    # ─── Knowledge Base local paths ───────────────────────────────────────────
    @property
    def pricing_master_path(self) -> Path:
        return KB_ROOT / "bromyros_pricing_master.json"

    @property
    def accessories_catalog_path(self) -> Path:
        return KB_ROOT / "accessories_catalog.json"

    @property
    def bom_rules_path(self) -> Path:
        return KB_ROOT / "bom_rules.json"

    @property
    def bmc_kb_path(self) -> Path:
        return KB_ROOT / "BMC_Base_Conocimiento_GPT-2.json"

    # ─── Environment helpers ──────────────────────────────────────────────────
    environment: str = Field(default="development", alias="ENVIRONMENT")

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def debug(self) -> bool:
        return not self.is_production


@lru_cache(maxsize=1)
def get_settings() -> PanelinSettings:
    """Singleton: retorna la configuración global (cacheada)."""
    return PanelinSettings()
