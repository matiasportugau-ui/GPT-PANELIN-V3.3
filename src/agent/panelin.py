"""Panelin conversational agent built on Agno."""

from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path
from typing import Any, Optional

from agno.agent import Agent
from agno.db.base import AsyncBaseDb, BaseDb
from agno.knowledge import FileSystemKnowledge, Knowledge
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.memory.manager import MemoryManager
from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat
from agno.vectordb.pgvector import PgVector

from src.core.config import Settings
from src.quotation.service import QuotationService
from src.quotation.tools import build_quotation_tools

logger = logging.getLogger(__name__)


def _build_model(settings: Settings) -> OpenAIChat | Claude:
    if settings.model_provider == "anthropic":
        return Claude(
            id=settings.anthropic_model_id,
            api_key=settings.anthropic_api_key,
            temperature=0.1,
        )
    return OpenAIChat(
        id=settings.openai_model_id,
        api_key=settings.openai_api_key,
        temperature=0.1,
    )


def _build_knowledge(settings: Settings) -> Knowledge | FileSystemKnowledge | None:
    base_path = settings.knowledge_base_path
    if not base_path.exists():
        logger.warning("Knowledge base path does not exist: %s", base_path)
        return None

    if settings.enable_vector_knowledge and settings.resolved_db_url and settings.openai_api_key:
        try:
            vector_db = PgVector(
                table_name=settings.pgvector_table,
                schema=settings.pgvector_schema,
                db_url=settings.resolved_db_url,
                embedder=OpenAIEmbedder(api_key=settings.openai_api_key),
                create_schema=True,
            )
            return Knowledge(
                name="panelin-kb",
                description="Base de conocimiento de productos y reglas BMC Uruguay.",
                vector_db=vector_db,
                max_results=settings.knowledge_max_results,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Vector knowledge disabled due to init error: %s", exc)

    return FileSystemKnowledge(
        base_dir=str(base_path),
        max_results=settings.knowledge_max_results,
        include_patterns=["*.json"],
        exclude_patterns=["**/archive/**", "**/.git/**"],
    )


def _import_mcp_types() -> tuple[Any, Any, Any] | None:
    """Import MCP tooling, handling local `mcp/` module shadowing."""
    try:
        from agno.tools.mcp import MCPTools
        from agno.tools.mcp.params import SSEClientParams, StreamableHTTPClientParams

        return MCPTools, SSEClientParams, StreamableHTTPClientParams
    except Exception as first_error:  # noqa: BLE001
        logger.warning("Initial MCP import failed: %s", first_error)

    workspace_root = Path(__file__).resolve().parents[2]
    original_sys_path = list(sys.path)
    shadowed_modules = [name for name in list(sys.modules.keys()) if name == "mcp" or name.startswith("mcp.")]

    try:
        for name in shadowed_modules:
            sys.modules.pop(name, None)

        sys.path = [
            p
            for p in original_sys_path
            if Path(p or ".").resolve() != workspace_root
        ]
        importlib.import_module("mcp")

        from agno.tools.mcp import MCPTools
        from agno.tools.mcp.params import SSEClientParams, StreamableHTTPClientParams

        return MCPTools, SSEClientParams, StreamableHTTPClientParams
    except Exception as retry_error:  # noqa: BLE001
        logger.warning("MCP import retry failed: %s", retry_error)
        return None
    finally:
        sys.path = original_sys_path


def _build_mcp_tools(settings: Settings) -> Any | None:
    if not settings.enable_mcp_tools:
        return None

    imported = _import_mcp_types()
    if imported is None:
        return None
    MCPTools, SSEClientParams, StreamableHTTPClientParams = imported

    include_tools = settings.mcp_include_tools or None
    exclude_tools = settings.mcp_exclude_tools or None
    prefix = settings.mcp_tool_name_prefix or None

    try:
        if settings.mcp_transport == "streamable-http":
            params = StreamableHTTPClientParams(url=settings.mcp_sse_url)
        else:
            params = SSEClientParams(url=settings.mcp_sse_url, timeout=float(settings.mcp_timeout_seconds))

        return MCPTools(
            transport=settings.mcp_transport,
            server_params=params,
            timeout_seconds=settings.mcp_timeout_seconds,
            include_tools=include_tools,
            exclude_tools=exclude_tools,
            tool_name_prefix=prefix,
            refresh_connection=False,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("MCP tools disabled due to configuration error: %s", exc)
        return None


def build_panelin_agent(
    settings: Settings,
    db: BaseDb | AsyncBaseDb | None = None,
    service: QuotationService | None = None,
) -> Agent:
    """Build the conversational agent used by AgentOS."""
    quotation_service = service or QuotationService()
    model = _build_model(settings)
    domain_tools = build_quotation_tools(quotation_service)
    mcp_tools = _build_mcp_tools(settings)

    tools: list[Any] = [*domain_tools]
    if mcp_tools is not None:
        tools.append(mcp_tools)

    memory_manager: MemoryManager | None = None
    if db is not None:
        memory_manager = MemoryManager(model=model, db=db)

    return Agent(
        id="panelin-conversacional",
        name="Panelin Conversacional",
        model=model,
        db=db,
        memory_manager=memory_manager,
        enable_agentic_memory=memory_manager is not None,
        update_memory_on_run=memory_manager is not None,
        add_memories_to_context=memory_manager is not None,
        add_history_to_context=True,
        num_history_runs=8,
        search_session_history=True,
        add_session_state_to_context=True,
        knowledge=_build_knowledge(settings),
        add_knowledge_to_context=True,
        tools=tools,
        instructions=[
            "Eres Panelin, asesor técnico-comercial de BMC Uruguay.",
            "Responde SIEMPRE en español rioplatense claro.",
            "NUNCA inventes precios: usa exclusivamente resultados del motor o tools.",
            "Si faltan datos técnicos, pide datos concretos (luz, uso, estructura, medidas).",
            "Explica riesgos estructurales y nivel SRE cuando aplique.",
            "Para cotización formal, indica explícitamente requisitos pendientes.",
        ],
        markdown=True,
        telemetry=True,
    )
