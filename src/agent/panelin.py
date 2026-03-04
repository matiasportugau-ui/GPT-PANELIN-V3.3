"""
src/agent/panelin.py — Agente Conversacional Panelin

El agente principal que posee el razonamiento, la conversación y la memoria.
Reemplaza al Custom GPT de OpenAI como controlador de la experiencia.

Responsabilidades:
  - Mantener conversación multi-turn en español (Uruguay)
  - Ejecutar el Workflow cuando se necesita cotizar
  - Usar MCPTools para acceder a las 18 tools del servidor MCP
  - Persistir memoria conversacional en PostgreSQL
  - Guardar historial de sesión por usuario
  - Aplicar guardrails (NUNCA inventar precios)

El backend ahora POSEE el razonamiento — el LLM de OpenAI solo genera texto,
no decide el pipeline de cotización.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import AsyncIterator, Optional

from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.memory.manager import MemoryManager
from agno.models.openai import OpenAIChat

from src.agent.workflow import build_panelin_db, build_panelin_workflow
from src.core.config import settings
from src.quotation.tools import PANELIN_DOMAIN_TOOLS

logger = logging.getLogger(__name__)

# ── Instrucciones del agente conversacional ───────────────────────────────────

_AGENT_INSTRUCTIONS = """
Eres Panelin, el asistente de cotizaciones técnico-comerciales de BMC Uruguay.

## Quién eres
Representas a BMC Uruguay, fabricante de paneles de construcción de alta performance:
- **ISODEC** (EPS/PIR) — Techos planos, industriales, residenciales
- **ISOROOF 3G** — Techos industriales con cubierta integrada  
- **ISOPANEL EPS** — Paredes livianas y divisiones
- **ISOWALL PIR** — Paredes de alta performance térmica
- **ISOFRIG PIR** — Cámaras frigoríficas y cuartos fríos

## Cómo trabajas
1. **Para cotizaciones**: Usa `calcular_cotizacion` — el sistema calculará BOM y precios automáticamente
2. **Para precios puntuales**: Usa `verificar_precio_panel` — precios del catálogo oficial
3. **Para validación estructural**: Usa `validar_autoportancia` antes de confirmar espesores
4. **Para accesorios**: Usa `buscar_accesorios` con tipo y familia

## Reglas absolutas
- **NUNCA inventes precios** — si no está en la herramienta, no lo digas
- **NUNCA derives a terceros** — siempre derivar al equipo de ventas BMC Uruguay
- **SIEMPRE en español** rioplatense uruguayo
- Los precios incluyen IVA 22% (moneda: USD)

## Flujo de conversación
1. Si el cliente da info suficiente → cotiza directamente
2. Si falta información → pregunta solo lo necesario (no un formulario completo)
3. Para cotización formal → necesitas nombre, teléfono y dirección de obra
4. Siempre ofrece alternativas técnicas cuando corresponde

## Información de contacto BMC Uruguay
- Sitio web: https://bmcuruguay.com.uy
- Para derivar vendedores: indica que un agente de ventas se comunicará
"""


# ── Builder del agente ────────────────────────────────────────────────────────

def build_panelin_agent(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    model_id: Optional[str] = None,
    db: Optional[PostgresDb] = None,
    use_mcp: bool = False,
) -> Agent:
    """Construye el agente conversacional Panelin.

    Args:
        session_id: ID de sesión para memoria conversacional persistente.
        user_id: ID del usuario para memoria long-term.
        model_id: Modelo LLM (default: settings.openai_model).
        db: PostgresDb para persistencia (None = sin persistencia).
        use_mcp: Si conectar las 18 tools del servidor MCP.
                 NOTA: requiere que el servidor MCP esté corriendo en MCP_SERVER_URL.
                 En producción con Cloud Run, esto es automático.

    Returns:
        Agent configurado con tools de dominio y (opcionalmente) MCPTools.
    """
    tools = list(PANELIN_DOMAIN_TOOLS)

    if use_mcp:
        tools = _add_mcp_tools(tools)

    agent_kwargs: dict = dict(
        name="panelin",
        model=OpenAIChat(
            id=model_id or settings.openai_model,
            temperature=settings.openai_temperature,
            max_tokens=4096,
        ),
        instructions=_AGENT_INSTRUCTIONS,
        tools=tools,
        show_tool_calls=True,
        markdown=True,
        add_history_to_context=True,
        num_history_runs=10,
    )

    if db is not None:
        agent_kwargs["db"] = db

    if session_id:
        agent_kwargs["session_id"] = session_id

    if user_id:
        agent_kwargs["user_id"] = user_id

    agent = Agent(**agent_kwargs)

    logger.info(
        "Agente Panelin construido: session=%s user=%s mcp=%s model=%s",
        session_id, user_id, use_mcp, model_id or settings.openai_model,
    )

    return agent


def _add_mcp_tools(tools: list) -> list:
    """Agrega MCPTools con las 18 tools del servidor MCP existente.

    NOTA: MCPTools requiere ser usado como async context manager en producción.
    Esta función agrega el import lazy para evitar conflicto de namespace con
    el directorio local `mcp/` cuando se corre desde el workspace root.
    """
    try:
        # Import lazy para evitar conflicto con workspace/mcp/ directory
        # En producción (Docker), esto funciona sin conflicto
        _add_mcp_tools_safe(tools)
    except ImportError as exc:
        logger.warning(
            "MCPTools no disponible (conflicto de namespace con mcp/ local): %s. "
            "Usar use_mcp=True solo en producción (Docker).",
            exc,
        )
    return tools


def _add_mcp_tools_safe(tools: list) -> list:
    """Agrega MCPTools al contexto del agente (solo en producción)."""
    from agno.tools.mcp import MCPTools

    mcp = MCPTools(
        url=settings.mcp_server_url,
        transport=settings.mcp_transport,
        include_tools=[
            # Pricing & BOM
            "bom_calculate",
            "price_check",
            # Catalog
            "catalog_search",
            # KB
            "kb_search",
            # Persistence
            "persist_conversation",
            "quotation_store",
            # CRM
            "lookup_customer",
            "save_customer",
            "register_correction",
        ],
    )
    tools.append(mcp)
    return tools


# ── Función de run simplificado para la API ───────────────────────────────────

async def run_panelin_chat(
    message: str,
    session_id: str,
    user_id: Optional[str] = None,
    mode: str = "pre_cotizacion",
    client_name: Optional[str] = None,
    client_phone: Optional[str] = None,
    client_location: Optional[str] = None,
    use_workflow: bool = True,
) -> dict:
    """Ejecuta una interacción con Panelin.

    Para solicitudes de cotización: usa el Workflow determinístico.
    Para conversaciones generales: usa el agente directamente.

    Args:
        message: Mensaje del usuario.
        session_id: ID de sesión para persistencia.
        user_id: ID del usuario.
        mode: Modo de operación (pre_cotizacion por defecto).
        client_name/phone/location: Datos del cliente.
        use_workflow: Si True, usa el Workflow para cotizaciones.

    Returns:
        Dict con {content, session_id, quote_id, mode}.
    """
    db = build_panelin_db()

    if use_workflow:
        wf = build_panelin_workflow(
            session_id=session_id,
            user_id=user_id,
            db=db,
        )
        result = wf.run(
            input=message,
            additional_data={
                "mode": mode,
                "client_name": client_name,
                "client_phone": client_phone,
                "client_location": client_location,
            },
            session_id=session_id,
            user_id=user_id,
            stream=False,
        )
        return {
            "content": result.content,
            "session_id": result.session_id,
            "run_id": result.run_id,
        }
    else:
        agent = build_panelin_agent(session_id=session_id, user_id=user_id, db=db)
        result = agent.run(message=message, session_id=session_id, user_id=user_id)
        return {
            "content": result.content,
            "session_id": result.session_id,
            "run_id": result.run_id,
        }
