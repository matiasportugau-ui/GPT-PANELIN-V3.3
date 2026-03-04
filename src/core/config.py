"""
Panelin v5.0 — Centralized configuration via pydantic-settings.

Single source of truth for all runtime settings. Values are loaded from
environment variables (and .env files in development).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class PanelinSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Application ──
    app_name: str = "Panelin"
    app_version: str = "5.0.0"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = False
    log_level: str = "INFO"
    port: int = 8080

    # ── LLM Provider ──
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_temperature: float = 0.3
    openai_max_tokens: int = 4000

    # ── Database (Cloud SQL) ──
    database_url: str = Field(
        default="postgresql+psycopg://panelin:panelin@localhost:5432/panelin",
        alias="DATABASE_URL",
    )
    db_session_table: str = "panelin_sessions"
    db_memory_table: str = "panelin_memory"
    db_knowledge_table: str = "panelin_knowledge"

    # ── MCP Server ──
    mcp_server_url: str = Field(default="http://localhost:8000/sse", alias="MCP_SERVER_URL")
    mcp_transport: str = Field(default="sse", alias="MCP_TRANSPORT")

    # ── Wolf API ──
    wolf_api_key: str = Field(default="", alias="WOLF_API_KEY")
    wolf_api_url: str = Field(
        default="https://panelin-api-642127786762.us-central1.run.app",
        alias="WOLF_API_URL",
    )

    # ── CORS ──
    cors_allowed_origins: str = Field(default="", alias="CORS_ALLOWED_ORIGINS")

    # ── KB Paths ──
    kb_root: Path = _PROJECT_ROOT
    kb_pricing_master: str = "bromyros_pricing_master.json"
    kb_accessories: str = "accessories_catalog.json"
    kb_bom_rules: str = "bom_rules.json"
    kb_core: str = "BMC_Base_Conocimiento_GPT-2.json"

    # ── Google Sheets ──
    sheets_spreadsheet_id: str = Field(default="", alias="SHEETS_SPREADSHEET_ID")
    google_credentials_path: str = Field(
        default="", alias="GOOGLE_SHEETS_CREDENTIALS_PATH",
    )

    # ── PDF ──
    pdf_output_dir: str = "panelin_reports/output"

    # ── IVA ──
    iva_rate: float = 0.22

    @property
    def cors_origins_list(self) -> list[str]:
        if not self.cors_allowed_origins:
            return []
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> PanelinSettings:
    return PanelinSettings()
