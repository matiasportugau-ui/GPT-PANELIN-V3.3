"""Centralized runtime configuration for the Agno migration."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Single source of truth for runtime configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    app_name: str = "panelin-agno"
    app_version: str = "5.0.0"
    environment: str = "production"
    debug: bool = False
    log_level: str = "INFO"

    # Database / Cloud SQL
    database_url: str | None = None
    db_host: str | None = None
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str | None = None
    db_name: str = "app_database"
    db_connection_name: str | None = None

    # Agno DB table names
    agno_db_schema: str = "ai"
    agno_session_table: str = "panelin_sessions"
    agno_memory_table: str = "panelin_memories"
    agno_traces_table: str = "panelin_traces"
    agno_spans_table: str = "panelin_spans"

    # Model provider
    panelin_model_provider: Literal["openai", "anthropic"] = "openai"
    openai_api_key: str | None = None
    openai_model_id: str = "gpt-4o-mini"
    anthropic_api_key: str | None = None
    anthropic_model_id: str = "claude-sonnet-4-5-20250929"
    enable_llm_response_step: bool = True

    # Agent/Workflow behavior
    panelin_agent_id: str = "panelin-agent"
    panelin_workflow_id: str = "panelin-quotation-workflow"
    panelin_num_history_runs: int = 8
    panelin_enable_memory_v2: bool = True
    panelin_enable_tracing: bool = True
    panelin_enable_telemetry: bool = True
    panelin_enable_authorization: bool = False
    panelin_jwt_verification_key: str | None = None
    panelin_jwt_algorithm: str = "RS256"
    panelin_jwt_verify_audience: bool = False

    # MCP integration
    panelin_enable_mcp_tools: bool = True
    panelin_mcp_transport: Literal["sse", "streamable-http"] = "sse"
    panelin_mcp_sse_url: str = "http://localhost:8000/sse"
    panelin_mcp_streamable_http_url: str = "http://localhost:8000/mcp"
    panelin_mcp_timeout_seconds: int = 20
    panelin_mcp_include_tools_csv: str = ""
    panelin_mcp_exclude_tools_csv: str = ""

    # Legacy API integration
    wolf_api_url: str = "http://localhost:8080"
    wolf_api_key: str | None = None

    # Knowledge / pgvector (advanced phase)
    panelin_enable_knowledge: bool = False
    panelin_knowledge_dir: str = "."
    panelin_pgvector_table: str = "panelin_knowledge"
    panelin_embedding_model_id: str = "text-embedding-3-small"

    # CORS
    cors_allow_origins: str = ""

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @staticmethod
    def _parse_csv(raw_value: str) -> list[str]:
        return [item.strip() for item in raw_value.split(",") if item.strip()]

    @property
    def cors_origins(self) -> list[str]:
        return self._parse_csv(self.cors_allow_origins)

    @property
    def mcp_include_tools(self) -> list[str]:
        return self._parse_csv(self.panelin_mcp_include_tools_csv)

    @property
    def mcp_exclude_tools(self) -> list[str]:
        return self._parse_csv(self.panelin_mcp_exclude_tools_csv)

    @property
    def preferred_mcp_url(self) -> str:
        if self.panelin_mcp_transport == "streamable-http":
            return self.panelin_mcp_streamable_http_url
        return self.panelin_mcp_sse_url

    @property
    def has_model_credentials(self) -> bool:
        if self.panelin_model_provider == "anthropic":
            return bool(self.anthropic_api_key)
        return bool(self.openai_api_key)

    @property
    def use_llm_response_step(self) -> bool:
        return self.enable_llm_response_step and self.has_model_credentials

    @property
    def postgres_db_url(self) -> str | None:
        """Build a SQLAlchemy-compatible PostgreSQL URL for Cloud SQL or TCP."""
        if self.database_url:
            return self.database_url

        if self.db_connection_name:
            user = quote_plus(self.db_user)
            db_name = quote_plus(self.db_name)
            if self.db_password:
                pwd = quote_plus(self.db_password)
                return (
                    f"postgresql+psycopg://{user}:{pwd}@/{db_name}"
                    f"?host=/cloudsql/{self.db_connection_name}"
                )
            return f"postgresql+psycopg://{user}@/{db_name}?host=/cloudsql/{self.db_connection_name}"

        if self.db_host:
            user = quote_plus(self.db_user)
            host = quote_plus(self.db_host)
            db_name = quote_plus(self.db_name)
            if self.db_password:
                pwd = quote_plus(self.db_password)
                return f"postgresql+psycopg://{user}:{pwd}@{host}:{self.db_port}/{db_name}"
            return f"postgresql+psycopg://{user}@{host}:{self.db_port}/{db_name}"

        return None

    def build_postgres_db(self):
        """Create an Agno PostgresDb instance, or None if no DB URL exists."""
        db_url = self.postgres_db_url
        if not db_url:
            return None

        from agno.db.postgres import PostgresDb

        return PostgresDb(
            db_url=db_url,
            db_schema=self.agno_db_schema,
            session_table=self.agno_session_table,
            memory_table=self.agno_memory_table,
            traces_table=self.agno_traces_table,
            spans_table=self.agno_spans_table,
        )

    def build_authorization_config(self):
        """Create AgentOS JWT authorization config when enabled."""
        if not self.panelin_enable_authorization:
            return None
        if not self.panelin_jwt_verification_key:
            return None

        from agno.os.config import AuthorizationConfig

        return AuthorizationConfig(
            verification_keys=[self.panelin_jwt_verification_key],
            algorithm=self.panelin_jwt_algorithm,
            verify_audience=self.panelin_jwt_verify_audience,
        )


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings()
