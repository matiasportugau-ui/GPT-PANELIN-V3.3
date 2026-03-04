"""Panelin conversational agent assembly (Agno Agent + tools + MCP + memory)."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
import logging
import re
import sys
from typing import Any

from agno.agent import Agent
from agno.exceptions import OutputCheckError
from agno.memory.manager import MemoryManager
from agno.knowledge.filesystem import FileSystemKnowledge

from src.agent.models import build_chat_model
from src.core.config import AppSettings, get_settings
from src.quotation.service import QuotationService
from src.quotation.tools import build_domain_tools, build_integration_tools

logger = logging.getLogger(__name__)

_PRICE_TOKEN = re.compile(r"(?:usd|\$)\s*\d", re.IGNORECASE)


def _price_guardrail(run_output, **_: Any) -> None:
    """Output guardrail: avoid price answers without tool evidence."""
    content = str(getattr(run_output, "content", "") or "")
    mentions_price = "precio" in content.lower() or bool(_PRICE_TOKEN.search(content))
    if not mentions_price:
        return

    tool_calls = getattr(run_output, "tools", None) or []
    if not tool_calls:
        raise OutputCheckError(
            "La respuesta parece incluir precio sin evidencia de tools/KB. "
            "Debes consultar fuentes de precios antes de responder."
        )


@contextmanager
def _without_project_root_on_sys_path(project_root: Path):
    """Temporarily remove project root from sys.path to avoid mcp package shadowing."""
    original_sys_path = list(sys.path)
    filtered = []
    for entry in sys.path:
        if not entry:
            continue
        try:
            if Path(entry).resolve() == project_root:
                continue
        except Exception:
            pass
        filtered.append(entry)
    sys.path = filtered

    existing_mcp = sys.modules.get("mcp")
    if existing_mcp is not None:
        existing_file = getattr(existing_mcp, "__file__", "") or ""
        if existing_file.startswith(str(project_root)):
            del sys.modules["mcp"]

    try:
        yield
    finally:
        sys.path = original_sys_path


def _build_mcp_toolkit(settings: AppSettings):
    """Build MCPTools connected to existing SSE/HTTP MCP server."""
    if not settings.panelin_enable_mcp_tools:
        return None

    project_root = settings.project_root
    try:
        with _without_project_root_on_sys_path(project_root):
            from agno.tools.mcp import MCPTools, SSEClientParams, StreamableHTTPClientParams

        include_tools = settings.mcp_include_tools or None
        exclude_tools = settings.mcp_exclude_tools or None

        if settings.panelin_mcp_transport == "streamable-http":
            server_params = StreamableHTTPClientParams(
                url=settings.panelin_mcp_streamable_http_url,
                timeout=timedelta(seconds=settings.panelin_mcp_timeout_seconds),
            )
        else:
            server_params = SSEClientParams(
                url=settings.panelin_mcp_sse_url,
                timeout=float(settings.panelin_mcp_timeout_seconds),
                sse_read_timeout=300.0,
            )

        return MCPTools(
            transport=settings.panelin_mcp_transport,
            server_params=server_params,
            include_tools=include_tools,
            exclude_tools=exclude_tools,
            timeout_seconds=settings.panelin_mcp_timeout_seconds,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("MCPTools disabled due to import/config error: %s", exc)
        return None


def _build_knowledge(settings: AppSettings):
    if not settings.panelin_enable_knowledge:
        return None
    knowledge_root = (settings.project_root / settings.panelin_knowledge_dir).resolve()
    if not knowledge_root.exists():
        logger.warning("Knowledge directory not found: %s", knowledge_root)
        return None
    return FileSystemKnowledge(
        base_dir=str(knowledge_root),
        include_patterns=["*.json", "*.md"],
        exclude_patterns=["**/.git/**", "**/__pycache__/**"],
    )


def _build_memory_manager(settings: AppSettings, db):
    if not settings.panelin_enable_memory_v2 or db is None or not settings.has_model_credentials:
        return None
    return MemoryManager(
        model=build_chat_model(settings),
        db=db,
        update_memories=True,
        add_memories=True,
        delete_memories=False,
    )


def build_panelin_agent(
    settings: AppSettings | None = None,
    workflow=None,
    service: QuotationService | None = None,
    db=None,
) -> Agent:
    """Create the conversational Panelin agent."""
    cfg = settings or get_settings()
    quotation_service = service or QuotationService()
    shared_db = db or cfg.build_postgres_db()

    tools: list[Any] = []
    tools.extend(build_domain_tools(cfg, quotation_service, workflow=workflow))
    tools.extend(build_integration_tools(cfg))

    mcp_toolkit = _build_mcp_toolkit(cfg)
    if mcp_toolkit is not None:
        tools.append(mcp_toolkit)

    knowledge = _build_knowledge(cfg)
    memory_manager = _build_memory_manager(cfg, shared_db)

    return Agent(
        id=cfg.panelin_agent_id,
        name="Panelin Agent",
        description=(
            "Asistente técnico-comercial de BMC Uruguay para cotizaciones "
            "determinísticas de paneles constructivos."
        ),
        model=build_chat_model(cfg),
        db=shared_db,
        memory_manager=memory_manager,
        enable_agentic_memory=memory_manager is not None,
        update_memory_on_run=memory_manager is not None,
        knowledge=knowledge,
        add_knowledge_to_context=knowledge is not None,
        add_history_to_context=True,
        num_history_runs=cfg.panelin_num_history_runs,
        add_session_state_to_context=True,
        tools=tools,
        markdown=True,
        search_knowledge=knowledge is not None,
        instructions=[
            "Responde siempre en español rioplatense claro y profesional.",
            "Nunca inventes precios, SKUs ni stock: usa tools, KB o workflow.",
            "Para cotizaciones complejas, prioriza ejecutar el workflow determinístico.",
            "Si faltan datos de obra, solicita los campos faltantes explícitamente.",
            "Incluye advertencias técnicas cuando el riesgo estructural sea alto.",
        ],
        post_hooks=[_price_guardrail],
        telemetry=cfg.panelin_enable_telemetry,
        debug_mode=cfg.debug,
    )
