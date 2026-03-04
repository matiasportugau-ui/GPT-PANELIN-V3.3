"""
Panelin Agno — Single source of truth for configuration.

Uses pydantic-settings to read from environment variables with validation.
All configuration is centralized here instead of scattered across modules.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """PostgreSQL / Cloud SQL settings."""

    url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/panelin",
        alias="DATABASE_URL",
        description="SQLAlchemy-compatible connection string (psycopg v3 driver)",
    )
    async_url: str = Field(
        default="",
        alias="DATABASE_ASYNC_URL",
    )

    @field_validator("async_url", mode="before")
    @classmethod
    def derive_async_url(cls, v: str, info) -> str:
        if v:
            return v
        sync_url = info.data.get("url", "")
        return sync_url.replace("postgresql+psycopg://", "postgresql+psycopg_async://")

    sessions_table: str = Field(default="panelin_sessions")
    memories_table: str = Field(default="panelin_memories")
    knowledge_table: str = Field(default="panelin_knowledge")

    model_config = {"env_prefix": "", "extra": "ignore"}


class LLMSettings(BaseSettings):
    """LLM model configuration. Supports swapping providers."""

    provider: str = Field(default="openai", description="openai | anthropic | google")
    model_id: str = Field(default="gpt-4o", alias="LLM_MODEL_ID")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, alias="LLM_MAX_TOKENS")
    api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")

    model_config = {"env_prefix": "", "extra": "ignore"}


class MCPSettings(BaseSettings):
    """MCP server connection settings."""

    url: str = Field(
        default="http://localhost:8000/sse",
        alias="MCP_SERVER_URL",
    )
    transport: str = Field(
        default="sse",
        alias="MCP_TRANSPORT",
        description="sse | streamable-http",
    )
    timeout: int = Field(default=30, alias="MCP_TIMEOUT")
    include_tools: Optional[list[str]] = Field(default=None)
    exclude_tools: Optional[list[str]] = Field(default=None)

    model_config = {"env_prefix": "", "extra": "ignore"}


class SecuritySettings(BaseSettings):
    """Security & authentication settings."""

    wolf_api_key: str = Field(default="", alias="WOLF_API_KEY")
    cors_allowed_origins: str = Field(default="", alias="CORS_ALLOWED_ORIGINS")
    jwt_secret: str = Field(default="", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")

    model_config = {"env_prefix": "", "extra": "ignore"}


class KBSettings(BaseSettings):
    """Knowledge base file paths."""

    pricing_master: str = Field(default="bromyros_pricing_master.json", alias="KB_PRICING_MASTER")
    accessories_catalog: str = Field(default="accessories_catalog.json", alias="KB_ACCESSORIES")
    bom_rules: str = Field(default="bom_rules.json", alias="KB_BOM_RULES")
    bmc_core: str = Field(default="BMC_Base_Conocimiento_GPT-2.json", alias="KB_CORE")
    gcs_bucket: str = Field(default="", alias="KB_GCS_BUCKET")

    model_config = {"env_prefix": "", "extra": "ignore"}


class SheetsSettings(BaseSettings):
    """Google Sheets CRM integration."""

    spreadsheet_id: str = Field(default="", alias="SHEETS_SPREADSHEET_ID")
    tab_2026: str = Field(default="Administrador de Cotizaciones 2026", alias="SHEETS_TAB_2026")
    tab_admin: str = Field(default="Admin.", alias="SHEETS_TAB_ADMIN")

    model_config = {"env_prefix": "", "extra": "ignore"}


class AppSettings(BaseSettings):
    """Top-level application settings that compose all sub-settings."""

    app_name: str = Field(default="Panelin Agno", alias="APP_NAME")
    version: str = "5.0.0"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8080, alias="PORT")

    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    mcp: MCPSettings = Field(default_factory=MCPSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    kb: KBSettings = Field(default_factory=KBSettings)
    sheets: SheetsSettings = Field(default_factory=SheetsSettings)

    model_config = {"env_prefix": "", "extra": "ignore"}


@lru_cache
def get_settings() -> AppSettings:
    """Return cached singleton settings. Reads .env on first call."""
    return AppSettings()
