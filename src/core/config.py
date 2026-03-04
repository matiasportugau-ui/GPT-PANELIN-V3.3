"""
Panelin v5.0 — Single Source of Truth Configuration
=====================================================

All settings are loaded from environment variables with sensible defaults.
Uses pydantic-settings for validation and type coercion.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class PanelinSettings(BaseSettings):
    """Central configuration for the Panelin system."""

    model_config = {"env_prefix": "PANELIN_", "env_file": ".env", "extra": "ignore"}

    # ── Application ──
    app_name: str = "Panelin"
    app_version: str = "5.0.0"
    environment: str = Field(default="development", description="development | staging | production")
    debug: bool = False
    log_level: str = "INFO"

    # ── API ──
    port: int = 8080
    host: str = "0.0.0.0"
    cors_allowed_origins: str = Field(
        default="https://app.agno.com,https://agno.com",
        description="Comma-separated list of allowed CORS origins",
    )

    # ── Authentication ──
    wolf_api_key: str = Field(default="", alias="WOLF_API_KEY")
    jwt_secret: str = Field(default="", description="JWT signing secret for AgentOS auth")
    jwt_algorithm: str = "HS256"

    # ── Database (Cloud SQL PostgreSQL) ──
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="app_database", alias="DB_NAME")
    db_user: str = Field(default="postgres", alias="DB_USER")
    db_password: str = Field(default="", alias="DB_PASSWORD")
    db_connection_name: str = Field(default="", alias="DB_CONNECTION_NAME")

    # ── LLM Models ──
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    default_model_provider: str = "openai"
    default_model_id: str = "gpt-4o"
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")

    # ── MCP Server ──
    mcp_server_url: str = Field(
        default="http://localhost:8000/sse",
        description="MCP server SSE endpoint",
    )

    # ── Google Cloud ──
    kb_gcs_bucket: str = Field(default="", alias="KB_GCS_BUCKET")
    sheets_spreadsheet_id: str = Field(default="", alias="SHEETS_SPREADSHEET_ID")

    # ── Knowledge Base Paths ──
    pricing_master_path: str = "bromyros_pricing_master.json"
    accessories_catalog_path: str = "accessories_catalog.json"
    bom_rules_path: str = "bom_rules.json"
    bmc_kb_path: str = "BMC_Base_Conocimiento_GPT-2.json"

    @property
    def db_url(self) -> str:
        """PostgreSQL connection string for SQLAlchemy/psycopg."""
        if self.db_connection_name:
            return (
                f"postgresql+psycopg://{self.db_user}:{self.db_password}"
                f"@/{self.db_name}?host=/cloudsql/{self.db_connection_name}"
            )
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def cors_origins_list(self) -> list[str]:
        if not self.cors_allowed_origins:
            return ["*"]
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"environment must be one of {allowed}")
        return v


@lru_cache()
def get_settings() -> PanelinSettings:
    """Singleton settings instance."""
    return PanelinSettings()
