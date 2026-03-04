"""
Panelin v5.0 — Agno Agent

The conversational agent that wraps the quotation workflow, MCP tools,
knowledge base, and session persistence.

Architecture:
    User message → Agent understands intent
        → If quotation request → delegates to QuotationWorkflow
        → If product query → uses MCP tools or Knowledge
        → If general question → answers from instructions/KB
        → All responses in Spanish
"""

from __future__ import annotations

from typing import Any, Optional

from agno.agent.agent import Agent
from agno.models.openai import OpenAIChat

from src.core.config import get_settings
from src.quotation.tools import (
    calculate_quotation,
    classify_request,
    parse_request,
    calculate_sai_score,
)


PANELIN_INSTRUCTIONS = [
    # Identity
    "Sos Panelin, el asistente técnico-comercial de BMC Uruguay para paneles de construcción.",
    "Tu objetivo es ayudar a vendedores y clientes con cotizaciones de paneles ISODEC, ISOPANEL, ISOROOF, ISOWALL e ISOFRIG.",

    # Language
    "Respondé SIEMPRE en español (variante rioplatense/uruguaya).",
    "Usá 'vos' y 'sos' en lugar de 'tú' y 'eres'.",

    # Pricing rules
    "Los precios NUNCA se inventan. Provienen EXCLUSIVAMENTE de la base de datos de BMC.",
    "Todos los precios del catálogo INCLUYEN IVA 22%. NUNCA sumes IVA encima.",
    "Si un precio no se encuentra en la KB, informá explícitamente que no está disponible.",

    # Workflow
    "Para cotizaciones, usá la herramienta calculate_quotation.",
    "Si el usuario pide clasificar o parsear un pedido, usá classify_request o parse_request.",

    # Products
    "Familias de paneles: ISODEC (techo EPS/PIR), ISOROOF (techo 3G), ISOPANEL (pared EPS), ISOWALL (pared PIR), ISOFRIG (cámaras frigoríficas PIR).",
    "Espesores disponibles: 30, 40, 50, 60, 80, 100, 120, 150, 200 mm (varía por familia).",
    "Ancho útil estándar: 1.12 m (1120 mm) para la mayoría de los paneles.",

    # SRE/Autoportancia
    "La autoportancia determina la luz máxima entre apoyos según familia/espesor.",
    "Si la luz excede la capacidad, recomendá un espesor mayor o soportes intermedios.",

    # Operating modes
    "Modo 'informativo': información general, sin cotización formal.",
    "Modo 'pre_cotizacion': cotización con supuestos declarados, validaciones flexibles.",
    "Modo 'formal': cotización completa, todas las validaciones activas, apta para PDF.",

    # Response format
    "Formateá las respuestas de forma clara usando tablas Markdown para items del BOM.",
    "Incluí el quote_id, modo, nivel SRE, y total en USD en cada cotización.",
    "Si hay warnings o datos faltantes, mencionálos claramente.",
]


def create_panelin_agent(
    db: Any = None,
    session_id: Optional[str] = None,
    mcp_tools: Any = None,
    knowledge: Any = None,
    extra_tools: Optional[list] = None,
) -> Agent:
    """Create the Panelin conversational agent.

    Args:
        db: PostgresDb for session persistence.
        session_id: Optional session ID for continuity.
        mcp_tools: Optional MCPTools instance for the 18+ MCP tools.
        knowledge: Optional Knowledge base for product search.
        extra_tools: Additional tools to register.

    Returns:
        Configured Agno Agent.
    """
    settings = get_settings()

    tools: list = [
        calculate_quotation,
        classify_request,
        parse_request,
        calculate_sai_score,
    ]

    if mcp_tools is not None:
        tools.append(mcp_tools)

    if extra_tools:
        tools.extend(extra_tools)

    agent_kwargs: dict[str, Any] = {
        "name": "Panelin",
        "model": OpenAIChat(
            id=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=settings.openai_temperature,
        ),
        "instructions": PANELIN_INSTRUCTIONS,
        "tools": tools,
        "markdown": True,
        "add_history_to_context": True,
        "num_history_runs": 10,
    }

    if db is not None:
        agent_kwargs["db"] = db
    if session_id is not None:
        agent_kwargs["session_id"] = session_id
    if knowledge is not None:
        agent_kwargs["knowledge"] = knowledge
        agent_kwargs["add_knowledge_to_context"] = True

    return Agent(**agent_kwargs)
