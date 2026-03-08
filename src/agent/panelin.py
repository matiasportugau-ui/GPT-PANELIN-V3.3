"""
Panelin Agno — Main Agent

The conversational agent that owns the reasoning, the tools, and the memory.
This replaces the passive Custom GPT architecture where OpenAI controlled everything.

Architecture:
    - Agent with tools for quotation generation, catalog search, and accessories
    - MCP integration for the 18+ existing MCP tools (pricing, governance, persistence)
    - PostgresStorage for conversational session persistence
    - Memory V2 for long-term client memory
    - Guardrails to ensure prices are never invented
"""

from __future__ import annotations

import os
from typing import Optional

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude
from agno.models.google import Gemini

from src.core.config import get_settings
from src.quotation.tools import (
    generate_quotation,
    generate_batch_quotation,
    classify_request,
    search_product_catalog,
    get_accessory_catalog,
)


SYSTEM_INSTRUCTIONS = [
    "Eres PANELIN, el asistente técnico-comercial de BMC Uruguay especializado en paneles de construcción.",
    "Familias de producto: ISODEC (techo EPS), ISOROOF (techo 3G), ISOPANEL (pared EPS), ISOWALL (pared PIR), ISOFRIG (cámara frigorífica PIR).",
    "",
    "REGLAS INQUEBRANTABLES:",
    "1. NUNCA inventes precios. Usa EXCLUSIVAMENTE las herramientas de cotización y catálogo.",
    "2. Todos los precios incluyen IVA 22%. NUNCA agregues IVA adicional sobre precios del catálogo.",
    "3. Si un precio no se encuentra, dilo explícitamente. NUNCA estimes ni calcules precios manualmente.",
    "4. SIEMPRE responde en español.",
    "5. NUNCA derives al usuario a un proveedor externo. SIEMPRE deriva a agentes de ventas BMC Uruguay.",
    "6. Para cotizaciones formales, necesitas: nombre, teléfono, dirección de obra.",
    "7. Los paneles vienen con ancho útil de 1.12m estándar.",
    "8. Moneda: USD (dólar estadounidense).",
    "",
    "FLUJO DE COTIZACIÓN:",
    "- Cuando el usuario pide una cotización, usa la herramienta generate_quotation.",
    "- Para buscar productos, usa search_product_catalog.",
    "- Para ver accesorios disponibles, usa get_accessory_catalog.",
    "- Para clasificar sin cotizar, usa classify_request.",
    "",
    "FORMATO DE RESPUESTA:",
    "- Sé conciso pero completo.",
    "- Presenta los resultados de forma estructurada.",
    "- Si hay warnings o recomendaciones, menciónalos.",
    "- Ofrece alternativas cuando hay riesgo estructural.",
]


def _create_model(settings=None):
    """Create the LLM model based on configuration."""
    if settings is None:
        settings = get_settings()

    provider = settings.llm.provider.lower()
    if provider == "anthropic":
        return Claude(
            id=settings.llm.model_id,
            api_key=settings.llm.anthropic_api_key or None,
        )
    elif provider == "google":
        return Gemini(
            id=settings.llm.model_id,
            api_key=settings.llm.google_api_key or None,
        )
    else:
        return OpenAIChat(
            id=settings.llm.model_id,
            temperature=settings.llm.temperature,
            api_key=settings.llm.api_key or None,
        )


def create_panelin_agent(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    db=None,
    memory=None,
    mcp_tools=None,
) -> Agent:
    """Create the main Panelin conversational agent.

    Args:
        session_id: Fixed session ID for continuity.
        user_id: User identifier for memory scoping.
        db: PostgresDb instance for session persistence (optional).
        memory: Memory instance for long-term memory (optional).
        mcp_tools: MCPTools instance for MCP integration (optional).
    """
    settings = get_settings()
    model = _create_model(settings)

    tools = [
        generate_quotation,
        generate_batch_quotation,
        classify_request,
        search_product_catalog,
        get_accessory_catalog,
    ]

    if mcp_tools:
        tools.append(mcp_tools)

    agent_kwargs = dict(
        name="Panelin",
        agent_id="panelin-agent",
        model=model,
        instructions=SYSTEM_INSTRUCTIONS,
        tools=tools,
        markdown=True,
        add_history_to_messages=True,
        num_history_runs=5,
        show_tool_calls=True,
        debug_mode=settings.debug,
    )

    if db:
        agent_kwargs["db"] = db

    if memory:
        agent_kwargs["memory"] = memory
        agent_kwargs["enable_agentic_memory"] = True

    if session_id:
        agent_kwargs["session_id"] = session_id

    if user_id:
        agent_kwargs["user_id"] = user_id

    return Agent(**agent_kwargs)


def create_db(settings=None):
    """Create PostgresDb for session persistence."""
    if settings is None:
        settings = get_settings()

    try:
        from agno.db.postgres import PostgresDb
        return PostgresDb(
            table_name=settings.db.sessions_table,
            db_url=settings.db.url,
        )
    except ImportError:
        return None


def create_memory(settings=None, model=None):
    """Create Memory V2 for long-term client memory."""
    if settings is None:
        settings = get_settings()
    if model is None:
        model = _create_model(settings)

    try:
        from agno.memory.v2.memory import Memory
        from agno.memory.v2.db.postgres import PostgresMemoryDb

        memory_db = PostgresMemoryDb(
            table_name=settings.db.memories_table,
            connection_string=settings.db.url,
        )
        return Memory(model=model, db=memory_db)
    except ImportError:
        return None


async def create_mcp_tools(settings=None):
    """Create MCPTools for MCP server integration. Must be used as async context manager."""
    if settings is None:
        settings = get_settings()

    from agno.tools.mcp import MCPTools

    mcp_tools = MCPTools(
        url=settings.mcp.url,
        transport=settings.mcp.transport,
        include_tools=settings.mcp.include_tools,
        exclude_tools=settings.mcp.exclude_tools,
    )
    return mcp_tools
