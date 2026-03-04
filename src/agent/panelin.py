from __future__ import annotations

import importlib.util
import json
import site
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.exceptions import OutputCheckError
from agno.knowledge.filesystem import FileSystemKnowledge
from agno.knowledge.knowledge import Knowledge
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat
from agno.tools.decorator import tool
from agno.vectordb.pgvector import PgVector

from src.agent.workflow import build_panelin_workflow
from src.core.config import Settings
from src.integration.wolf_tools import build_wolf_api_tools
from src.quotation.service import QuotationService
from src.quotation.tools import PANELIN_QUOTATION_TOOLS


REPO_ROOT = Path(__file__).resolve().parents[2]
KB_FILES = [
    "BMC_Base_Conocimiento_GPT-2.json",
    "bromyros_pricing_master.json",
    "accessories_catalog.json",
    "bom_rules.json",
]


def _ensure_external_mcp_package() -> bool:
    """Fuerza carga del paquete mcp de site-packages (evita shadowing local /mcp)."""

    def _is_local_repo_mcp(module: object) -> bool:
        module_file = getattr(module, "__file__", "")
        return str(module_file).startswith(str(REPO_ROOT / "mcp"))

    loaded = sys.modules.get("mcp")
    if loaded is not None and not _is_local_repo_mcp(loaded):
        return True

    if loaded is not None and _is_local_repo_mcp(loaded):
        del sys.modules["mcp"]

    search_roots = [site.getusersitepackages(), *site.getsitepackages()]
    for root in search_roots:
        package_init = Path(root) / "mcp" / "__init__.py"
        if not package_init.exists():
            continue
        spec = importlib.util.spec_from_file_location(
            "mcp",
            package_init,
            submodule_search_locations=[str(package_init.parent)],
        )
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        sys.modules["mcp"] = module
        spec.loader.exec_module(module)
        return True

    return False


def _build_response_model(settings: Settings):
    if settings.model_provider == "anthropic":
        return Claude(
            id=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
        )
    return OpenAIChat(
        id=settings.openai_model,
        api_key=settings.openai_api_key,
    )


def _build_postgres_db(settings: Settings) -> PostgresDb:
    return PostgresDb(
        db_url=settings.postgres_dsn,
        db_schema=settings.db_schema,
        session_table=settings.db_session_table,
        memory_table=settings.db_memory_table,
        metrics_table=settings.db_metrics_table,
        traces_table=settings.db_traces_table,
        spans_table=settings.db_spans_table,
        knowledge_table=settings.db_knowledge_table,
        components_table=settings.db_components_table,
        component_configs_table=settings.db_component_configs_table,
        component_links_table=settings.db_component_links_table,
        versions_table=settings.db_versions_table,
        create_schema=True,
    )


def _build_knowledge(settings: Settings):
    kb_paths = [str(REPO_ROOT / file_name) for file_name in KB_FILES if (REPO_ROOT / file_name).exists()]
    if settings.kb_enable_pgvector:
        vector_db = PgVector(
            table_name=settings.kb_pgvector_table,
            schema=settings.db_schema,
            db_url=settings.postgres_dsn,
            embedder=OpenAIEmbedder(
                id=settings.kb_embedder_model,
                api_key=settings.openai_api_key,
            ),
        )
        knowledge = Knowledge(name="panelin-kb", vector_db=vector_db, max_results=8)
        for path in kb_paths:
            knowledge.add_content(path=path, reader=knowledge.json_reader, upsert=True)
        return knowledge

    return FileSystemKnowledge(
        base_dir=str(REPO_ROOT),
        include_patterns=KB_FILES,
        exclude_patterns=["archive/**", "**/*.md", "**/*.rtf"],
    )


def _build_mcp_tools(settings: Settings) -> list[Any]:
    if not settings.enable_mcp_tools:
        return []
    if not _ensure_external_mcp_package():
        return []

    from agno.tools.mcp import MCPTools
    from agno.tools.mcp.params import SSEClientParams, StreamableHTTPClientParams

    include_tools = settings.mcp_include_tools or None
    exclude_tools = settings.mcp_exclude_tools or None

    if settings.mcp_transport == "sse":
        server_params = SSEClientParams(
            url=settings.mcp_sse_url,
            timeout=float(settings.mcp_timeout_seconds),
            sse_read_timeout=300.0,
        )
        toolkit = MCPTools(
            transport="sse",
            server_params=server_params,
            include_tools=include_tools,
            exclude_tools=exclude_tools,
            timeout_seconds=settings.mcp_timeout_seconds,
            tool_name_prefix=settings.mcp_tool_name_prefix,
        )
        return [toolkit]

    from datetime import timedelta

    server_params = StreamableHTTPClientParams(
        url=settings.mcp_sse_url,
        timeout=timedelta(seconds=settings.mcp_timeout_seconds),
    )
    toolkit = MCPTools(
        transport="streamable-http",
        server_params=server_params,
        include_tools=include_tools,
        exclude_tools=exclude_tools,
        timeout_seconds=settings.mcp_timeout_seconds,
        tool_name_prefix=settings.mcp_tool_name_prefix,
    )
    return [toolkit]


def _price_guardrail(run_output, **_: Any) -> None:
    content = getattr(run_output, "content", "")
    text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, default=str)
    lowered = text.lower()
    forbidden_markers = ["precio inventado", "precio estimado sin kb", "sin datos de kb pero"]
    if any(marker in lowered for marker in forbidden_markers):
        raise OutputCheckError("Guardrail: respuesta con indicios de precio no validado por KB.")


def _build_response_agent(settings: Settings, db: PostgresDb) -> Agent | None:
    if not settings.response_with_llm:
        return None
    if settings.model_provider == "openai" and not settings.openai_api_key:
        return None
    if settings.model_provider == "anthropic" and not settings.anthropic_api_key:
        return None
    return Agent(
        id="panelin-response-agent",
        name="Panelin Response Formatter",
        model=_build_response_model(settings),
        db=db,
        markdown=True,
        instructions=[
            "Responde siempre en espanol.",
            "No inventes precios ni stock.",
            "Si faltan datos de KB, dilo explicitamente.",
            "Mantener tono tecnico-comercial de BMC Uruguay.",
        ],
    )


def _build_workflow_tool(workflow):
    @tool(
        name="panelin_run_workflow",
        description="Ejecuta workflow deterministico Panelin v4 con routing explicito.",
    )
    def panelin_run_workflow(
        text: str,
        mode: str = "pre_cotizacion",
        client_name: Optional[str] = None,
        client_phone: Optional[str] = None,
        client_location: Optional[str] = None,
    ) -> dict[str, Any]:
        result = workflow.run(
            input={
                "text": text,
                "mode": mode,
                "client_name": client_name,
                "client_phone": client_phone,
                "client_location": client_location,
            }
        )
        return result.content

    return panelin_run_workflow


@dataclass
class PanelinRuntime:
    db: PostgresDb
    workflow: Any
    agent: Agent


def build_panelin_runtime(settings: Settings) -> PanelinRuntime:
    service = QuotationService()
    db = _build_postgres_db(settings)
    response_agent = _build_response_agent(settings, db)
    workflow = build_panelin_workflow(
        service=service,
        response_agent=response_agent,
        db=db,
    )

    workflow_tool = _build_workflow_tool(workflow)
    wolf_tools = build_wolf_api_tools(settings)
    mcp_tools = _build_mcp_tools(settings)

    panelin_agent = Agent(
        id="panelin-agent",
        name="Panelin Agno Agent",
        model=_build_response_model(settings),
        db=db,
        tools=[
            *PANELIN_QUOTATION_TOOLS,
            workflow_tool,
            *wolf_tools,
            *mcp_tools,
        ],
        knowledge=_build_knowledge(settings),
        add_knowledge_to_context=True,
        search_knowledge=True,
        add_history_to_context=True,
        num_history_runs=8,
        markdown=True,
        instructions=[
            "Eres Panelin, asistente de cotizaciones para paneles BMC Uruguay.",
            "El orden del pipeline de cotizacion es deterministico y no se altera.",
            "Usa panelin_run_workflow para cotizaciones tecnico-comerciales.",
            "Nunca inventes precios: siempre deben provenir de KB o tools MCP/Wolf.",
            "Si un precio no esta disponible, indicalo y solicita datos faltantes.",
        ],
        post_hooks=[_price_guardrail] if settings.strict_price_guardrail else None,
    )

    return PanelinRuntime(db=db, workflow=workflow, agent=panelin_agent)
