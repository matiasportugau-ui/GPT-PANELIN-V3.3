from __future__ import annotations

from functools import lru_cache
from typing import Literal
from urllib.parse import quote_plus

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracion centralizada para la arquitectura Panelin + Agno."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "development"
    debug: bool = False

    host: str = "0.0.0.0"
    port: int = 8080

    model_provider: Literal["openai", "anthropic"] = "openai"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5-20250929"
    response_with_llm: bool = True

    database_url: str | None = None
    db_user: str = "postgres"
    db_password: str | None = None
    db_name: str = "app_database"
    db_host: str | None = None
    db_port: int = 5432
    db_schema: str = "ai"
    cloudsql_connection_name: str | None = None

    db_session_table: str = "panelin_sessions"
    db_memory_table: str = "panelin_memories"
    db_metrics_table: str = "panelin_metrics"
    db_traces_table: str = "panelin_traces"
    db_spans_table: str = "panelin_spans"
    db_knowledge_table: str = "panelin_knowledge"
    db_components_table: str = "panelin_components"
    db_component_configs_table: str = "panelin_component_configs"
    db_component_links_table: str = "panelin_component_links"
    db_versions_table: str = "panelin_versions"

    mcp_sse_url: str = "http://127.0.0.1:8000/sse"
    mcp_transport: Literal["sse", "streamable-http"] = "sse"
    mcp_timeout_seconds: int = 10
    enable_mcp_tools: bool = True
    mcp_tool_name_prefix: str | None = None
    mcp_include_tools: list[str] = Field(default_factory=list)
    mcp_exclude_tools: list[str] = Field(default_factory=list)

    cors_allow_origins: list[str] = Field(default_factory=list)

    wolf_api_base_url: str = "http://127.0.0.1:8080"
    wolf_api_key: str | None = None

    kb_enable_pgvector: bool = False
    kb_pgvector_table: str = "panelin_knowledge_vectors"
    kb_embedder_model: str = "text-embedding-3-small"

    agentos_authorization: bool = False
    agentos_jwt_verification_keys: list[str] = Field(default_factory=list)
    agentos_jwt_algorithm: str = "HS256"
    agentos_verify_audience: bool = False
    agentos_tracing: bool = True

    strict_price_guardrail: bool = True

    @field_validator(
        "mcp_include_tools",
        "mcp_exclude_tools",
        "agentos_jwt_verification_keys",
        "cors_allow_origins",
        mode="before",
    )
    @classmethod
    def _parse_csv_list(cls, value: object) -> object:
        if value is None:
            return []
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value

    @property
    def postgres_dsn(self) -> str:
        """Build DSN para Postgres (incluye formato Cloud SQL por socket)."""
        if self.database_url:
            return self.database_url

        auth = self.db_user
        if self.db_password:
            auth = f"{self.db_user}:{quote_plus(self.db_password)}"

        if self.cloudsql_connection_name:
            # Cloud SQL en Cloud Run: host como Unix socket.
            return (
                f"postgresql+psycopg://{auth}@/{self.db_name}"
                f"?host=/cloudsql/{self.cloudsql_connection_name}"
            )

        host = self.db_host or "127.0.0.1"
        return f"postgresql+psycopg://{auth}@{host}:{self.db_port}/{self.db_name}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
