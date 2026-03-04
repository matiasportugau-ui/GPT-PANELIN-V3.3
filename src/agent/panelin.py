"""
Panelin v5.0 - Agno Conversational Agent
==========================================

The main Panelin agent that handles user conversations.

Architecture:
    - Uses the v4 engine via PanelinTools (direct function calls)
    - Connects to existing MCP server for legacy tools (persistence, KB, tasks)
    - PostgresStorage for conversational memory across sessions
    - Guardrails to prevent price invention

This agent owns the conversation loop. The LLM decides WHEN to use tools
but the tools themselves are deterministic (the v4 engine).
"""

from __future__ import annotations

import logging
from typing import Optional

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude
from agno.models.google import Gemini

from src.quotation.tools import PanelinTools

logger = logging.getLogger(__name__)

PANELIN_INSTRUCTIONS = [
    "Eres **Panelin**, asistente técnico-comercial de **BMC Uruguay**.",
    "Ayudás a clientes a cotizar paneles de construcción: ISODEC, ISOROOF, ISOPANEL, ISOWALL, ISOFRIG.",
    "",
    "## Reglas Críticas",
    "1. **NUNCA inventés precios.** Los precios vienen EXCLUSIVAMENTE de la base de conocimiento (KB).",
    "   Si un precio no se encuentra, decí: 'Precio pendiente de confirmación con el equipo comercial.'",
    "2. **Los precios del catálogo ya incluyen IVA 22%.** NUNCA sumes IVA adicional.",
    "3. **Respondé siempre en ESPAÑOL** (español rioplatense de Uruguay).",
    "4. **Nunca derives a competidores.** Si te preguntan por productos que no vendemos,",
    "   derivá al equipo de ventas de BMC Uruguay.",
    "5. **Para cotización formal** necesitás: nombre, teléfono, dirección de obra.",
    "",
    "## Flujo de Cotización",
    "1. El usuario describe su proyecto en lenguaje natural",
    "2. Usá la herramienta `cotizar` para procesar la solicitud completa",
    "3. Presentá el resultado de forma clara y profesional",
    "4. Si faltan datos, pedílos amablemente",
    "",
    "## Herramientas Disponibles",
    "- `cotizar`: Genera cotización completa (BOM + pricing + validación)",
    "- `buscar_precio`: Busca precio de un panel específico",
    "- `calcular_bom`: Calcula lista de materiales",
    "- `validar_autoportancia`: Verifica capacidad estructural del panel",
    "- `cotizacion_batch`: Procesa múltiples cotizaciones",
    "",
    "## Formato de Respuesta",
    "Usá formato claro con emojis para facilitar lectura en chat:",
    "📋 Cotización | 📦 Producto | 📐 Dimensiones | 💰 Precios | ⚠️ Notas",
    "",
    "## Información de BMC Uruguay",
    "- Empresa: BMC Uruguay (Bromyros Material de Construcción)",
    "- Productos: Paneles termoaislantes para techos, paredes y cámaras frigoríficas",
    "- Web: https://bmcuruguay.com.uy",
    "- Moneda: USD (dólares americanos)",
    "- IVA: 22% (ya incluido en precios de catálogo)",
]


def _create_model(provider: str = "openai", model_id: str = "gpt-4o", **kwargs):
    """Factory for LLM model instances — enables easy provider swapping."""
    providers = {
        "openai": lambda: OpenAIChat(id=model_id, **kwargs),
        "anthropic": lambda: Claude(id=model_id, **kwargs),
        "google": lambda: Gemini(id=model_id, **kwargs),
    }
    factory = providers.get(provider.lower())
    if not factory:
        raise ValueError(f"Unknown LLM provider: {provider}. Use: openai, anthropic, google")
    return factory()


def create_panelin_agent(
    provider: str = "openai",
    model_id: str = "gpt-4o",
    storage=None,
    session_id: Optional[str] = None,
    mcp_tools=None,
    knowledge=None,
    extra_tools: Optional[list] = None,
) -> Agent:
    """Create the main Panelin conversational agent.

    Args:
        provider: LLM provider ("openai", "anthropic", "google").
        model_id: Model identifier (e.g., "gpt-4o", "claude-sonnet-4-5", "gemini-2.0-flash").
        storage: PostgresStorage instance for session persistence.
        session_id: Fixed session ID to resume conversations.
        mcp_tools: MCPTools instance for legacy MCP server connection.
        knowledge: Knowledge base for RAG-based product search.
        extra_tools: Additional tool instances to register.

    Returns:
        Configured Agno Agent ready for conversation.
    """
    model = _create_model(provider, model_id, temperature=0.3)

    tools = [PanelinTools()]
    if mcp_tools:
        tools.append(mcp_tools)
    if extra_tools:
        tools.extend(extra_tools)

    agent_kwargs = {
        "name": "Panelin",
        "model": model,
        "instructions": PANELIN_INSTRUCTIONS,
        "tools": tools,
        "show_tool_calls": True,
        "markdown": True,
        "add_history_to_context": True,
        "tool_call_limit": 10,
    }

    if storage:
        agent_kwargs["storage"] = storage
    if session_id:
        agent_kwargs["session_id"] = session_id
    if knowledge:
        agent_kwargs["knowledge"] = knowledge
        agent_kwargs["search_knowledge"] = True

    return Agent(**agent_kwargs)
