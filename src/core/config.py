"""
src/core/config.py — Fuente única de verdad para toda la configuración.

Usa pydantic-settings para leer de variables de entorno y .env.
Todos los módulos importan desde aquí, NUNCA de os.getenv directo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class PanelinSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ───────────────────────────────────────────────────────────────
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_temperature: float = Field(default=0.2, alias="OPENAI_TEMPERATURE")

    # ── Agno Agent ────────────────────────────────────────────────────────
    # PostgreSQL (Cloud SQL) — formato psycopg3
    # En Cloud Run: postgresql+psycopg://user:pass@/db?host=/cloudsql/PROJ:REG:INST
    database_url: str = Field(
        default="postgresql+psycopg://panelin:panelin@localhost:5432/panelin",
        alias="DATABASE_URL",
    )

    # ── MCP Server ────────────────────────────────────────────────────────
    mcp_server_url: str = Field(
        default="http://localhost:8000/sse",
        alias="MCP_SERVER_URL",
    )
    mcp_transport: str = Field(default="sse", alias="MCP_TRANSPORT")

    # ── Wolf API ──────────────────────────────────────────────────────────
    wolf_api_url: str = Field(
        default="https://panelin-api-642127786762.us-central1.run.app",
        alias="WOLF_API_URL",
    )
    wolf_api_key: str = Field(default="", alias="WOLF_API_KEY")

    # ── KB Paths ──────────────────────────────────────────────────────────
    kb_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)
    kb_pricing_master: str = Field(default="bromyros_pricing_master.json", alias="KB_PRICING_MASTER")
    kb_accessories: str = Field(default="accessories_catalog.json", alias="KB_ACCESSORIES")
    kb_bom_rules: str = Field(default="bom_rules.json", alias="KB_BOM_RULES")
    kb_core: str = Field(default="BMC_Base_Conocimiento_GPT-2.json", alias="KB_CORE")

    # ── Security ──────────────────────────────────────────────────────────
    cors_origins: str = Field(default="", alias="CORS_ORIGINS")

    # ── Google Cloud ──────────────────────────────────────────────────────
    gcs_bucket: str = Field(default="", alias="KB_GCS_BUCKET")
    sheets_spreadsheet_id: str = Field(default="", alias="SHEETS_SPREADSHEET_ID")

    # ── PDF ───────────────────────────────────────────────────────────────
    pdf_output_dir: Path = Field(
        default=Path("panelin_reports/output"), alias="PDF_OUTPUT_DIR"
    )

    # ── Runtime ───────────────────────────────────────────────────────────
    environment: str = Field(default="production", alias="ENVIRONMENT")
    port: int = Field(default=8080, alias="PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # ── IVA ───────────────────────────────────────────────────────────────
    iva_rate: float = Field(default=0.22, alias="IVA_RATE")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: str) -> str:
        return v or ""

    @property
    def cors_origins_list(self) -> list[str]:
        if not self.cors_origins:
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def kb_pricing_path(self) -> Path:
        return self.kb_root / self.kb_pricing_master

    @property
    def kb_accessories_path(self) -> Path:
        return self.kb_root / self.kb_accessories

    @property
    def kb_bom_rules_path(self) -> Path:
        return self.kb_root / self.kb_bom_rules

    @property
    def kb_core_path(self) -> Path:
        return self.kb_root / self.kb_core


# Singleton — todos los módulos importan esta instancia
settings = PanelinSettings()
