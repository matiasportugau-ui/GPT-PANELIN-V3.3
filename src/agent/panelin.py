"""
Panelin v5.0 — Main Agno Agent
=================================

The conversational agent that understands user queries, invokes the
quotation pipeline, connects to MCP tools, and maintains session memory.

Architecture:
    User message → Agent (understands intent)
        → If quotation request: runs the Workflow (7 deterministic steps + LLM respond)
        → If simple question: answers directly using Knowledge + tools
        → All conversations persisted via PostgresDb
"""

from __future__ import annotations

import logging
from typing import Optional

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.db.postgres import PostgresDb

from src.core.config import get_settings
from src.quotation.tools import PANELIN_TOOLS

logger = logging.getLogger(__name__)

PANELIN_SYSTEM_INSTRUCTIONS = """\
Eres **Panelin**, el asistente técnico-comercial de **BMC Uruguay** especializado en 
cotizaciones de paneles de construcción (ISODEC, ISOPANEL, ISOROOF, ISOWALL, ISOFRIG).

═══ REGLAS ABSOLUTAS ═══

1. **Idioma**: Siempre respondes en español
2. **Precios**: NUNCA inventes un precio. Todos los precios vienen exclusivamente de la 
   base de conocimiento (bromyros_pricing_master.json y accessories_catalog.json). 
   Si no encontrás un precio, decí explícitamente "precio no disponible en KB".
3. **IVA**: Todos los precios del catálogo YA incluyen IVA 22%. NUNCA sumes IVA adicional.
4. **Derivación**: NUNCA derives a proveedores externos. Siempre derivá a agentes de 
   ventas de BMC Uruguay (099 163 612, comercial@bmcuruguay.com.uy).
5. **Cotizaciones formales**: Requieren nombre, teléfono y dirección de obra.
6. **Formato teléfono Uruguay**: 09XXXXXXX (9 dígitos) o +598XXXXXXXX
7. **Moneda**: Siempre USD con 2 decimales
8. **Audio**: No podés procesar archivos de audio.

═══ PRODUCTOS BMC ═══

- **ISODEC** (EPS/PIR): Paneles para techo con junta machihembrada. Espesores: 30-200mm.
- **ISOROOF 3G**: Panel autoportante para techos de grandes luces. Espesores: 30-200mm.
- **ISOPANEL** (EPS): Paneles para pared/fachada. Espesores: 30-200mm.
- **ISOWALL** (PIR): Paneles ignífugos para pared. Espesores: 50-200mm.
- **ISOFRIG** (PIR): Paneles para cámaras frigoríficas. Espesores: 50-200mm.

═══ FLUJO DE COTIZACIÓN ═══

Cuando el usuario pide una cotización:
1. Usá la herramienta `quote_from_text` con el texto del usuario
2. Analizá el resultado y presentálo de forma clara y profesional
3. Si faltan datos, preguntá lo necesario antes de cotizar

Para consultas simples de precio: usá `check_product_price`
Para validación técnica: usá `validate_quotation_request`
Para buscar accesorios: usá `search_accessories`

═══ FORMATO DE RESPUESTA ═══

- Usa formato markdown para tablas de materiales
- Incluí siempre: producto, cantidad, precio unitario, subtotal
- Muestra el total general al final
- Si hay advertencias técnicas, mencionalas
- Para pre-cotizaciones: indica "sujeto a confirmación de datos"
- Para cotizaciones formales: incluí quote_id y datos del cliente
"""


def build_panelin_agent(
    model_id: Optional[str] = None,
    enable_mcp: bool = False,
    mcp_url: Optional[str] = None,
    db: Optional[PostgresDb] = None,
) -> Agent:
    """Build the main Panelin conversational agent.

    Args:
        model_id: LLM model identifier (default from settings)
        enable_mcp: Whether to connect to the MCP server
        mcp_url: Override MCP server URL
        db: PostgresDb instance for session persistence

    Returns:
        Configured Agno Agent ready to serve.
    """
    settings = get_settings()

    if model_id is None:
        model_id = settings.default_model_id

    model = OpenAIChat(id=model_id)

    tools = list(PANELIN_TOOLS)

    if enable_mcp:
        try:
            from agno.tools.mcp import MCPTools
            url = mcp_url or settings.mcp_server_url
            mcp_tools = MCPTools(url=url, transport="sse")
            tools.append(mcp_tools)
            logger.info("MCP tools connected at %s", url)
        except Exception as e:
            logger.warning("MCP tools unavailable: %s", e)

    if db is None:
        try:
            db = PostgresDb(
                db_url=settings.db_url,
                session_table="panelin_sessions",
            )
            logger.info("PostgresDb configured for session storage")
        except Exception as e:
            logger.warning("PostgresDb unavailable, sessions will not persist: %s", e)
            db = None

    agent = Agent(
        name="Panelin",
        model=model,
        instructions=[PANELIN_SYSTEM_INSTRUCTIONS],
        tools=tools,
        db=db,
        markdown=True,
        show_tool_calls=True,
        description="Asistente técnico-comercial de BMC Uruguay para cotizaciones de paneles",
    )

    return agent


def get_agent() -> Agent:
    """Get a pre-configured Panelin agent (convenience function)."""
    return build_panelin_agent()
