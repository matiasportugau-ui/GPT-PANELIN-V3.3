"""Central configuration for Panelin Agno Architecture.

Single source of truth for all environment variables.
Uses pydantic-settings for type-safe config with .env support.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings — loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === Application ===
    app_name: str = Field("Panelin", alias="APP_NAME")
    app_version: str = Field("4.0.0", alias="APP_VERSION")
    environment: str = Field("production", alias="ENVIRONMENT")
    debug: bool = Field(False, alias="DEBUG")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    # === OpenAI ===
    openai_api_key: str = Field("", alias="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4o", alias="OPENAI_MODEL")
    openai_temperature: float = Field(0.2, alias="OPENAI_TEMPERATURE")

    # === PostgreSQL (Cloud SQL) ===
    # Cloud SQL format: postgresql+psycopg://user:pass@/dbname?host=/cloudsql/PROJECT:REGION:INSTANCE
    database_url: Optional[str] = Field(None, alias="DATABASE_URL")

    # === MCP Server ===
    mcp_server_url: str = Field("http://localhost:8000", alias="MCP_SERVER_URL")
    mcp_transport: str = Field("sse", alias="MCP_TRANSPORT")  # "sse" or "streamable-http"

    # === Knowledge Base Paths ===
    kb_pricing_master: Path = Field(
        Path("bromyros_pricing_master.json"), alias="KB_PRICING_MASTER"
    )
    kb_accessories: Path = Field(
        Path("accessories_catalog.json"), alias="KB_ACCESSORIES"
    )
    kb_bom_rules: Path = Field(Path("bom_rules.json"), alias="KB_BOM_RULES")
    kb_bmc_core: Path = Field(
        Path("BMC_Base_Conocimiento_GPT-2.json"), alias="KB_CORE"
    )

    # === Wolf API / Security ===
    wolf_api_key: str = Field("", alias="WOLF_API_KEY")
    wolf_kb_write_password: str = Field("", alias="WOLF_KB_WRITE_PASSWORD")
    kb_write_password: str = Field("", alias="KB_WRITE_PASSWORD")

    # === CORS ===
    cors_origins: list[str] = Field(default_factory=list, alias="CORS_ORIGINS")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        if isinstance(v, list):
            return v
        return []

    # === IVA (Uruguay) ===
    iva_rate: float = Field(0.22, alias="IVA_RATE")

    # === PDF Generation ===
    pdf_output_dir: Path = Field(
        Path("panelin_reports/output"), alias="PDF_OUTPUT_DIR"
    )
    pdf_logo_path: Path = Field(Path("bmc_logo.png"), alias="PDF_LOGO_PATH")

    # === Google Cloud ===
    kb_gcs_bucket: str = Field("", alias="KB_GCS_BUCKET")
    sheets_spreadsheet_id: str = Field("", alias="SHEETS_SPREADSHEET_ID")

    @property
    def mcp_sse_url(self) -> str:
        return f"{self.mcp_server_url}/sse"

    @property
    def effective_cors_origins(self) -> list[str]:
        return self.cors_origins if self.cors_origins else ["*"]

    @property
    def has_database(self) -> bool:
        return bool(self.database_url)

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
