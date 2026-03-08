"""Panelin runtime composition: Agent + Workflow + MCP + DB."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.db.sqlite import SqliteDb
from agno.guardrails import PIIDetectionGuardrail, PromptInjectionGuardrail
from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat
from agno.tools import tool
from src.agent.mcp_compat import load_mcp_tooling
from src.agent.workflow import _price_output_guardrail, build_panelin_workflow, run_panelin_workflow
from src.core.config import Settings
from src.quotation.service import QuotationService
from src.quotation.tools import build_quotation_tools

logger = logging.getLogger(__name__)


class PanelinRuntime:
    """Assembles all runtime components required by AgentOS."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = self._build_db()
        self.quotation_service = QuotationService(settings)
        self.workflow = build_panelin_workflow(settings, db=self.db)
        self.workflow_tool = self._build_workflow_tool()
        self.mcp_tools = self._build_mcp_tools()
        self.agent = self._build_agent()

    def _build_db(self) -> Any:
        db_url = self.settings.resolved_db_url
        if db_url:
            return PostgresDb(
                db_url=db_url,
                db_schema=self.settings.db_schema,
                session_table=self.settings.db_session_table,
                memory_table=self.settings.db_memory_table,
                metrics_table=self.settings.db_metrics_table,
                eval_table=self.settings.db_eval_table,
                knowledge_table=self.settings.db_knowledge_table,
                traces_table=self.settings.db_traces_table,
                spans_table=self.settings.db_spans_table,
                approvals_table=self.settings.db_approvals_table,
            )

        Path("artifacts").mkdir(exist_ok=True)
        return SqliteDb(
            db_file="artifacts/panelin_agentos.db",
            session_table=self.settings.db_session_table,
            memory_table=self.settings.db_memory_table,
            metrics_table=self.settings.db_metrics_table,
            eval_table=self.settings.db_eval_table,
            knowledge_table=self.settings.db_knowledge_table,
        )

    def _build_model(self):
        provider = self.settings.model_provider.strip().lower()
        if provider == "anthropic":
            return Claude(
                id=self.settings.anthropic_model_id,
                api_key=self.settings.anthropic_api_key,
            )
        return OpenAIChat(
            id=self.settings.openai_model_id,
            api_key=self.settings.openai_api_key,
        )

    def _build_workflow_tool(self):
        runtime = self

        @tool(name="workflow_panelin_v4")
        def workflow_panelin_v4(
            text: str,
            mode: str = "pre_cotizacion",
            session_id: str | None = None,
            user_id: str | None = None,
        ) -> dict[str, Any]:
            """Ejecuta el workflow determinístico classify→...→SAI→response."""
            return run_panelin_workflow(
                runtime.workflow,
                text=text,
                mode=mode,
                session_id=session_id,
                user_id=user_id,
            )

        return workflow_panelin_v4

    def _build_mcp_tools(self):
        if not self.settings.enable_mcp_tools:
            return None

        try:
            MCPTools, SSEClientParams, StreamableHTTPClientParams = load_mcp_tooling()
            headers = None
            if self.settings.mcp_auth_header_value:
                headers = {
                    self.settings.mcp_auth_header_name: self.settings.mcp_auth_header_value,
                }

            if self.settings.mcp_transport == "streamable-http":
                params = StreamableHTTPClientParams(
                    url=self.settings.mcp_streamable_http_url,
                    headers=headers,
                )
                return MCPTools(
                    transport="streamable-http",
                    server_params=params,
                    timeout_seconds=self.settings.mcp_timeout_seconds,
                    include_tools=self.settings.mcp_include_tools_list or None,
                    exclude_tools=self.settings.mcp_exclude_tools_list or None,
                )

            params = SSEClientParams(
                url=self.settings.mcp_sse_url,
                headers=headers,
                timeout=self.settings.mcp_timeout_seconds,
            )
            return MCPTools(
                transport="sse",
                server_params=params,
                timeout_seconds=self.settings.mcp_timeout_seconds,
                include_tools=self.settings.mcp_include_tools_list or None,
                exclude_tools=self.settings.mcp_exclude_tools_list or None,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("MCPTools disabled: %s", exc)
            return None

    def _build_agent(self) -> Agent:
        domain_tools = build_quotation_tools(self.quotation_service)
        tools = [self.workflow_tool, *domain_tools]
        if self.mcp_tools is not None:
            tools.append(self.mcp_tools)

        return Agent(
            id="panelin-agent",
            name="Panelin Agente Comercial",
            model=self._build_model(),
            db=self.db,
            tools=tools,
            markdown=True,
            add_history_to_context=True,
            num_history_runs=6,
            update_memory_on_run=self.settings.enable_memory,
            enable_user_memories=self.settings.enable_memory,
            pre_hooks=[
                PromptInjectionGuardrail(),
                PIIDetectionGuardrail(),
            ],
            post_hooks=[_price_output_guardrail],
            instructions=[
                "Habla en español rioplatense profesional.",
                "No inventes precios ni disponibilidad: usa workflow_panelin_v4 y tools de KB.",
                "Para cotizaciones formales pide nombre, teléfono y dirección de obra.",
                "Si la consulta es técnica, explica riesgo SRE y recomendaciones.",
            ],
        )

    async def startup(self) -> None:
        if self.mcp_tools is not None:
            try:
                await self.mcp_tools.connect()
            except Exception as exc:  # noqa: BLE001
                logger.warning("No se pudo conectar MCP al iniciar: %s", exc)

    async def shutdown(self) -> None:
        if self.mcp_tools is not None:
            try:
                await self.mcp_tools.close()
            except Exception as exc:  # noqa: BLE001
                logger.warning("No se pudo cerrar MCP limpiamente: %s", exc)

