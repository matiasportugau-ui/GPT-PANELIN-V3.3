"""
Panelin v5.0 - Centralized Configuration
==========================================

Single source of truth for all environment-driven settings.
Uses pydantic-settings for validation, type coercion, and .env support.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Cloud SQL (PostgreSQL) connection settings."""

    host: str = Field("localhost", alias="DB_HOST")
    port: int = Field(5432, alias="DB_PORT")
    name: str = Field("panelin", alias="DB_NAME")
    user: str = Field("postgres", alias="DB_USER")
    password: str = Field("", alias="DB_PASSWORD")
    cloud_sql_connection: str = Field("", alias="CLOUD_SQL_CONNECTION_NAME")

    model_config = {"env_prefix": "", "populate_by_name": True}

    @property
    def url(self) -> str:
        """SQLAlchemy-compatible connection string for psycopg (v3)."""
        if self.cloud_sql_connection:
            return (
                f"postgresql+psycopg://{self.user}:{self.password}"
                f"@/{self.name}?host=/cloudsql/{self.cloud_sql_connection}"
            )
        return (
            f"postgresql+psycopg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )


class LLMSettings(BaseSettings):
    """LLM provider configuration — model-agnostic."""

    provider: str = Field("openai", alias="LLM_PROVIDER")
    model_id: str = Field("gpt-4o", alias="LLM_MODEL_ID")
    temperature: float = Field(0.3, alias="LLM_TEMPERATURE")
    max_tokens: int = Field(4096, alias="LLM_MAX_TOKENS")
    openai_api_key: str = Field("", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field("", alias="ANTHROPIC_API_KEY")
    google_api_key: str = Field("", alias="GOOGLE_API_KEY")

    model_config = {"env_prefix": "", "populate_by_name": True}


class MCPSettings(BaseSettings):
    """MCP server connection settings."""

    transport: str = Field("sse", alias="MCP_TRANSPORT")
    url: str = Field("http://localhost:8000/sse", alias="MCP_URL")
    timeout: int = Field(30, alias="MCP_TIMEOUT")

    model_config = {"env_prefix": "", "populate_by_name": True}


class SecuritySettings(BaseSettings):
    """Authentication and authorization settings."""

    wolf_api_key: str = Field("", alias="WOLF_API_KEY")
    kb_write_password: str = Field("", alias="KB_WRITE_PASSWORD")
    jwt_secret: str = Field("", alias="JWT_SECRET")
    cors_origins: str = Field("", alias="CORS_ALLOWED_ORIGINS")

    model_config = {"env_prefix": "", "populate_by_name": True}

    @property
    def cors_origins_list(self) -> list[str]:
        if not self.cors_origins:
            return []
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


class GCSSettings(BaseSettings):
    """Google Cloud Storage settings."""

    bucket: str = Field("", alias="KB_GCS_BUCKET")

    model_config = {"env_prefix": "", "populate_by_name": True}


class SheetsSettings(BaseSettings):
    """Google Sheets CRM integration settings."""

    spreadsheet_id: str = Field("", alias="SHEETS_SPREADSHEET_ID")
    tab_2026: str = Field("Administrador de Cotizaciones 2026", alias="SHEETS_TAB_2026")
    tab_2025: str = Field("2.0 -  Administrador de Cotizaciones", alias="SHEETS_TAB_2025")
    tab_admin: str = Field("Admin.", alias="SHEETS_TAB_ADMIN")

    model_config = {"env_prefix": "", "populate_by_name": True}


class Settings(BaseSettings):
    """Root settings — aggregates all sub-configs."""

    app_name: str = "Panelin"
    app_version: str = "5.0.0"
    environment: str = Field("development", alias="ENVIRONMENT")
    debug: bool = Field(False, alias="DEBUG")
    port: int = Field(8080, alias="PORT")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    mcp: MCPSettings = Field(default_factory=MCPSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    gcs: GCSSettings = Field(default_factory=GCSSettings)
    sheets: SheetsSettings = Field(default_factory=SheetsSettings)

    model_config = {"env_prefix": "", "populate_by_name": True, "env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
