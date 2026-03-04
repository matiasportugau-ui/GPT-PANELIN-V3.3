"""Centralized configuration for the Agno migration stack."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="Panelin AgentOS", alias="PANELIN_APP_NAME")
    app_version: str = Field(default="5.0.0", alias="PANELIN_APP_VERSION")
    environment: str = Field(default="production", alias="PANELIN_ENV")

    # Runtime mode
    use_in_memory_db: bool = Field(default=False, alias="PANELIN_USE_IN_MEMORY_DB")

    # Database / Cloud SQL
    db_url: Optional[str] = Field(default=None, alias="PANELIN_DB_URL")
    db_user: Optional[str] = Field(default=None, alias="PANELIN_DB_USER")
    db_password: Optional[str] = Field(default=None, alias="PANELIN_DB_PASSWORD")
    db_name: str = Field(default="panelin", alias="PANELIN_DB_NAME")
    db_host: str = Field(default="localhost", alias="PANELIN_DB_HOST")
    db_port: int = Field(default=5432, alias="PANELIN_DB_PORT")
    cloud_sql_connection_name: Optional[str] = Field(
        default=None,
        alias="PANELIN_CLOUD_SQL_CONNECTION_NAME",
    )
    db_schema: str = Field(default="ai", alias="PANELIN_DB_SCHEMA")
    session_table: str = Field(default="panelin_sessions", alias="PANELIN_SESSION_TABLE")
    memory_table: str = Field(default="panelin_memories", alias="PANELIN_MEMORY_TABLE")
    traces_table: str = Field(default="panelin_traces", alias="PANELIN_TRACES_TABLE")
    spans_table: str = Field(default="panelin_spans", alias="PANELIN_SPANS_TABLE")

    # Models
    model_provider: Literal["openai", "anthropic"] = Field(
        default="openai",
        alias="PANELIN_MODEL_PROVIDER",
    )
    openai_model_id: str = Field(default="gpt-4o-mini", alias="PANELIN_OPENAI_MODEL_ID")
    anthropic_model_id: str = Field(
        default="claude-sonnet-4-5-20250929",
        alias="PANELIN_ANTHROPIC_MODEL_ID",
    )
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    enable_llm_response_step: bool = Field(default=True, alias="PANELIN_ENABLE_LLM_RESPONSE")

    # MCP integration
    mcp_transport: Literal["sse", "streamable-http"] = Field(
        default="sse",
        alias="PANELIN_MCP_TRANSPORT",
    )
    enable_mcp_tools: bool = Field(default=True, alias="PANELIN_ENABLE_MCP_TOOLS")
    mcp_sse_url: str = Field(default="http://localhost:8000/sse", alias="PANELIN_MCP_SSE_URL")
    mcp_timeout_seconds: int = Field(default=20, alias="PANELIN_MCP_TIMEOUT_SECONDS")
    mcp_include_tools_raw: str = Field(default="", alias="PANELIN_MCP_INCLUDE_TOOLS")
    mcp_exclude_tools_raw: str = Field(default="", alias="PANELIN_MCP_EXCLUDE_TOOLS")
    mcp_tool_name_prefix: str = Field(default="mcp_", alias="PANELIN_MCP_TOOL_NAME_PREFIX")

    # AgentOS
    cors_allow_origins_raw: str = Field(default="", alias="PANELIN_CORS_ALLOW_ORIGINS")
    agentos_enable_auth: bool = Field(default=False, alias="PANELIN_AGENTOS_ENABLE_AUTH")
    agentos_enable_tracing: bool = Field(default=True, alias="PANELIN_AGENTOS_ENABLE_TRACING")
    agentos_enable_mcp_server: bool = Field(default=False, alias="PANELIN_AGENTOS_ENABLE_MCP_SERVER")

    # Knowledge / Vector DB
    knowledge_base_dir: str = Field(default=".", alias="PANELIN_KNOWLEDGE_BASE_DIR")
    enable_vector_knowledge: bool = Field(default=False, alias="PANELIN_ENABLE_VECTOR_KNOWLEDGE")
    pgvector_table: str = Field(default="panelin_knowledge", alias="PANELIN_PGVECTOR_TABLE")
    pgvector_schema: str = Field(default="ai", alias="PANELIN_PGVECTOR_SCHEMA")
    knowledge_max_results: int = Field(default=12, alias="PANELIN_KNOWLEDGE_MAX_RESULTS")

    @property
    def knowledge_base_path(self) -> Path:
        return Path(self.knowledge_base_dir).resolve()

    @property
    def cors_allow_origins(self) -> list[str]:
        if not self.cors_allow_origins_raw.strip():
            return []
        return [origin.strip() for origin in self.cors_allow_origins_raw.split(",") if origin.strip()]

    @property
    def mcp_include_tools(self) -> list[str]:
        if not self.mcp_include_tools_raw.strip():
            return []
        return [name.strip() for name in self.mcp_include_tools_raw.split(",") if name.strip()]

    @property
    def mcp_exclude_tools(self) -> list[str]:
        if not self.mcp_exclude_tools_raw.strip():
            return []
        return [name.strip() for name in self.mcp_exclude_tools_raw.split(",") if name.strip()]

    @property
    def resolved_db_url(self) -> Optional[str]:
        """Resolve SQLAlchemy DSN for Cloud SQL or standard Postgres."""
        if self.use_in_memory_db:
            return None

        if self.db_url:
            return self.db_url

        if not self.db_user or not self.db_password:
            return None

        encoded_password = quote_plus(self.db_password)
        if self.cloud_sql_connection_name:
            return (
                f"postgresql+psycopg://{self.db_user}:{encoded_password}"
                f"@/{self.db_name}?host=/cloudsql/{self.cloud_sql_connection_name}"
            )

        return (
            f"postgresql+psycopg://{self.db_user}:{encoded_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
