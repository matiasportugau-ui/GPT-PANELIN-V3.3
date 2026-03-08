"""Application settings for Panelin + Agno."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Single source of truth for runtime configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Panelin AgentOS"
    app_env: str = Field(default="dev", alias="APP_ENV")

    # --- Model/provider ---
    model_provider: str = Field(default="openai", alias="PANELIN_MODEL_PROVIDER")
    openai_model_id: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL_ID")
    anthropic_model_id: str = Field(
        default="claude-sonnet-4-5-20250929",
        alias="ANTHROPIC_MODEL_ID",
    )
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    enable_llm_response: bool = Field(default=True, alias="ENABLE_LLM_RESPONSE")

    # --- Database (Cloud SQL compatible) ---
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    db_schema: str = Field(default="panelin", alias="DB_SCHEMA")
    db_session_table: str = Field(default="panelin_sessions", alias="DB_SESSION_TABLE")
    db_memory_table: str = Field(default="panelin_memories", alias="DB_MEMORY_TABLE")
    db_metrics_table: str = Field(default="panelin_metrics", alias="DB_METRICS_TABLE")
    db_eval_table: str = Field(default="panelin_evals", alias="DB_EVAL_TABLE")
    db_knowledge_table: str = Field(default="panelin_knowledge", alias="DB_KNOWLEDGE_TABLE")
    db_traces_table: str = Field(default="panelin_traces", alias="DB_TRACES_TABLE")
    db_spans_table: str = Field(default="panelin_spans", alias="DB_SPANS_TABLE")
    db_approvals_table: str = Field(default="panelin_approvals", alias="DB_APPROVALS_TABLE")

    cloud_sql_connection_name: str | None = Field(default=None, alias="DB_CONNECTION_NAME")
    db_user: str | None = Field(default=None, alias="DB_USER")
    db_password: str | None = Field(default=None, alias="DB_PASSWORD")
    db_name: str | None = Field(default=None, alias="DB_NAME")

    # --- MCP ---
    enable_mcp_tools: bool = Field(default=True, alias="ENABLE_MCP_TOOLS")
    mcp_transport: str = Field(default="sse", alias="MCP_TRANSPORT")
    mcp_sse_url: str = Field(default="http://127.0.0.1:8000/sse", alias="MCP_SSE_URL")
    mcp_streamable_http_url: str = Field(
        default="http://127.0.0.1:8000/mcp",
        alias="MCP_STREAMABLE_HTTP_URL",
    )
    mcp_timeout_seconds: int = Field(default=15, alias="MCP_TIMEOUT_SECONDS")
    mcp_include_tools: str = Field(default="", alias="MCP_INCLUDE_TOOLS")
    mcp_exclude_tools: str = Field(default="", alias="MCP_EXCLUDE_TOOLS")
    mcp_auth_header_name: str = Field(default="X-API-Key", alias="MCP_AUTH_HEADER_NAME")
    mcp_auth_header_value: str | None = Field(default=None, alias="WOLF_API_KEY")

    # --- Knowledge / memory ---
    enable_memory: bool = Field(default=True, alias="ENABLE_MEMORY")
    enable_knowledge: bool = Field(default=False, alias="ENABLE_KNOWLEDGE")
    knowledge_pgvector_table: str = Field(
        default="panelin_knowledge_vectors",
        alias="KNOWLEDGE_PGVECTOR_TABLE",
    )
    knowledge_json_path: str = Field(
        default="BMC_Base_Conocimiento_GPT-2.json",
        alias="KNOWLEDGE_JSON_PATH",
    )
    knowledge_bootstrap_on_start: bool = Field(
        default=False,
        alias="KNOWLEDGE_BOOTSTRAP_ON_START",
    )

    # --- Compatibility / paths ---
    catalog_path: str = Field(default="wolf_api/catalog.json", alias="CATALOG_PATH")
    output_pdf_dir: str = Field(default="artifacts/quotes", alias="OUTPUT_PDF_DIR")

    # --- AgentOS / security ---
    cors_allow_origins: str = Field(default="", alias="CORS_ALLOW_ORIGINS")
    agentos_authorization: bool = Field(default=False, alias="AGENTOS_AUTHORIZATION")
    jwt_verification_keys: str = Field(default="", alias="JWT_VERIFICATION_KEYS")
    jwt_algorithm: str = Field(default="RS256", alias="JWT_ALGORITHM")
    verify_audience: bool = Field(default=False, alias="JWT_VERIFY_AUDIENCE")
    tracing_enabled: bool = Field(default=True, alias="AGENTOS_TRACING")

    @property
    def resolved_db_url(self) -> str | None:
        """Resolve SQLAlchemy URL for PostgresDb (Cloud SQL compatible)."""
        if self.database_url:
            return self.database_url

        if (
            self.cloud_sql_connection_name
            and self.db_user
            and self.db_password
            and self.db_name
        ):
            user = quote_plus(self.db_user)
            password = quote_plus(self.db_password)
            socket_host = quote_plus(f"/cloudsql/{self.cloud_sql_connection_name}")
            return (
                f"postgresql+psycopg://{user}:{password}@/{self.db_name}"
                f"?host={socket_host}"
            )

        return None

    @property
    def cors_allow_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

    @property
    def mcp_include_tools_list(self) -> list[str]:
        return [tool.strip() for tool in self.mcp_include_tools.split(",") if tool.strip()]

    @property
    def mcp_exclude_tools_list(self) -> list[str]:
        return [tool.strip() for tool in self.mcp_exclude_tools.split(",") if tool.strip()]

    @property
    def jwt_verification_keys_list(self) -> list[str]:
        return [key.strip() for key in self.jwt_verification_keys.split(",") if key.strip()]

    @property
    def output_pdf_dir_path(self) -> Path:
        return Path(self.output_pdf_dir)

    @property
    def knowledge_json_path_obj(self) -> Path:
        return Path(self.knowledge_json_path)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

