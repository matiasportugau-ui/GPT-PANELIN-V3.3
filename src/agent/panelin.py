"""Agente conversacional Panelin — BMC Uruguay.

Este agente posee el razonamiento, la conversación y la memoria.
El backend controla COMPLETAMENTE el ciclo de vida de la sesión.

Características:
- Modelo swappable: GPT-4o ↔ Claude ↔ Gemini (sin cambiar el resto del código)
- PostgresStorage para memoria conversacional persistente (Cloud SQL)
- MCPTools para conectar los 18 tools del servidor MCP existente
- Tools de dominio para cotizaciones directas sin pasar por el workflow
- Sistema de guardrails: nunca inventa precios
- Todo en español
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from agno.agent import Agent
from agno.models.openai import OpenAIChat

logger = logging.getLogger(__name__)


_PANELIN_SYSTEM_PROMPT = """Eres **Panelin**, el asistente técnico-comercial de **BMC Uruguay** especializado
en paneles de construcción: ISODEC, ISOPANEL, ISOROOF, ISOWALL e ISOFRIG.

## TU ROL
Ayudás a clientes, distribuidores y arquitectos a:
- Cotizar paneles (techo, pared, habitaciones, cámaras frías)
- Calcular materiales necesarios (BOM — Bill of Materials)
- Verificar si un panel soporta una determinada luz (autoportancia)
- Consultar especificaciones técnicas y precios
- Registrar consultas en el sistema CRM de BMC

## REGLAS CRÍTICAS — SEGUIR SIEMPRE:

### Precios
🚫 NUNCA inventes, estimes ni asumas precios
✅ Los precios SIEMPRE vienen de la herramienta `consultar_precio` o del resultado de `cotizar_panel`
✅ Todos los precios incluyen IVA 22% (Uruguay)
✅ Si no hay precio disponible en el KB, decilo claramente y derivá a ventas BMC

### Idioma
✅ Responde SIEMPRE en español rioplatense (uruguayo)
✅ Usá "vos" en lugar de "tú"

### Cotizaciones
- Para cotizaciones INFORMATIVAS: podés dar estimaciones sin todos los datos
- Para cotizaciones PRE-COTIZACIÓN: necesitás familia, espesor y dimensiones aproximadas
- Para cotizaciones FORMALES: necesitás nombre, teléfono, dirección de obra Y datos técnicos completos

### Derivación
🚫 NUNCA derives a proveedores externos o competidores
✅ Para instalación, derivá SIEMPRE a los agentes de ventas BMC Uruguay
✅ Website oficial: https://bmcuruguay.com.uy

## FLUJO DE COTIZACIÓN ESTÁNDAR:
1. Entender qué necesita el cliente (¿techo? ¿pared? ¿qué familia? ¿espesor?)
2. Si falta información, hacer UNA pregunta concreta a la vez
3. Con la información suficiente, usar `cotizar_panel` para el cálculo
4. Presentar el resultado de forma clara con BOM resumido y precio total
5. Si el modo es FORMAL, solicitar datos del cliente para el CRM

## SISTEMA DE PANELES BMC:
- **ISODEC EPS/PIR**: Panel sandwich para techos residenciales y comerciales
- **ISOROOF 3G**: Techo curvo o inclinado, alto rendimiento
- **ISOPANEL EPS**: Panel multipropósito (techo y pared)
- **ISOWALL PIR**: Panel de pared con mayor aislamiento térmico
- **ISOFRIG PIR**: Panel para cámaras frigoríficas

## ESPESORES DISPONIBLES: 80, 100, 120, 150, 200mm (según familia y disponibilidad)
## PENDIENTE MÍNIMA PARA TECHOS: 7% (≈4°)
## AUTOPORTANCIA: varía por espesor y familia — siempre verificar con `verificar_autoportancia`

Empezá cada conversación de forma amigable y preguntando en qué podés ayudar.
Si hay historia de conversación, continuá desde donde se quedó el cliente."""


def build_panelin_agent(
    model_id: Optional[str] = None,
    temperature: float = 0.2,
    db=None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    mcp_server_url: Optional[str] = None,
    mcp_transport: str = "sse",
    include_mcp_tools: bool = True,
) -> Agent:
    """Construye y retorna el agente Panelin configurado.

    Args:
        model_id: ID del modelo LLM (default: gpt-4o del env o settings)
        temperature: Temperatura del modelo (default: 0.2 — respuestas consistentes)
        db: PostgresDb instance para persistencia de sesión (opcional)
        session_id: ID de sesión para memoria conversacional
        user_id: ID de usuario para RBAC y memoria personalizada
        mcp_server_url: URL del servidor MCP (default: http://localhost:8000)
        mcp_transport: Transporte MCP: 'sse' o 'streamable-http'
        include_mcp_tools: Si True, conecta las 18 tools del servidor MCP

    Returns:
        Agent configurado y listo para usar
    """
    effective_model = model_id or os.environ.get("OPENAI_MODEL", "gpt-4o")
    effective_mcp_url = mcp_server_url or os.environ.get("MCP_SERVER_URL", "http://localhost:8000")

    # Domain tools — siempre disponibles (no requieren MCP)
    from src.quotation.tools import (
        cotizar_panel,
        calcular_bom,
        verificar_autoportancia,
        consultar_precio,
        procesar_lote,
    )

    tools = [
        cotizar_panel,
        calcular_bom,
        verificar_autoportancia,
        consultar_precio,
        procesar_lote,
    ]

    # MCP tools — conecta al servidor MCP existente (18 tools)
    # Nota: MCPTools requiere context manager async para SSE/streamable-http
    # Se agregan en build_panelin_agent_with_mcp() para uso async
    # Para uso sync simple, se usan solo las domain tools

    agent = Agent(
        name="Panelin",
        model=OpenAIChat(id=effective_model, temperature=temperature),
        instructions=_PANELIN_SYSTEM_PROMPT,
        tools=tools,
        db=db,
        session_id=session_id,
        user_id=user_id,
        add_history_to_context=True,
        num_history_runs=10,
        markdown=True,
        show_tool_calls=False,
    )

    return agent


async def build_panelin_agent_with_mcp(
    model_id: Optional[str] = None,
    temperature: float = 0.2,
    db=None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    mcp_server_url: Optional[str] = None,
    mcp_transport: str = "sse",
) -> tuple[Agent, object]:
    """Versión async del builder que incluye MCPTools conectado al servidor MCP.

    Retorna (agent, mcp_tools_context) — el caller debe cerrar el contexto MCP
    cuando termine.

    Uso:
        agent, mcp_ctx = await build_panelin_agent_with_mcp(...)
        try:
            response = await agent.arun("Hola, necesito cotizar...")
        finally:
            await mcp_ctx.__aexit__(None, None, None)
    """
    from agno.tools.mcp import MCPTools
    from src.quotation.tools import (
        cotizar_panel,
        calcular_bom,
        verificar_autoportancia,
        consultar_precio,
        procesar_lote,
    )

    effective_model = model_id or os.environ.get("OPENAI_MODEL", "gpt-4o")
    effective_mcp_url = mcp_server_url or os.environ.get("MCP_SERVER_URL", "http://localhost:8000")

    mcp_url = (
        f"{effective_mcp_url}/sse"
        if mcp_transport == "sse" and not effective_mcp_url.endswith("/sse")
        else effective_mcp_url
    )

    mcp_ctx = MCPTools(
        url=mcp_url,
        transport=mcp_transport,
        # Include only safe read tools by default (exclude file write tools)
        include_tools=[
            "price_check",
            "catalog_search",
            "bom_calculate",
            "persist_conversation",
            "register_correction",
            "save_customer",
            "lookup_customer",
            "batch_bom_calculate",
            "bulk_price_check",
            "full_quotation",
            "task_status",
            "task_result",
            "task_list",
        ],
    )

    try:
        await mcp_ctx.__aenter__()
        mcp_tools_available = True
    except Exception as exc:
        logger.warning("MCP server not available at %s: %s", mcp_url, exc)
        mcp_tools_available = False
        mcp_ctx = None

    tools = [
        cotizar_panel,
        calcular_bom,
        verificar_autoportancia,
        consultar_precio,
        procesar_lote,
    ]
    if mcp_tools_available and mcp_ctx:
        tools.append(mcp_ctx)

    agent = Agent(
        name="Panelin",
        model=OpenAIChat(id=effective_model, temperature=temperature),
        instructions=_PANELIN_SYSTEM_PROMPT,
        tools=tools,
        db=db,
        session_id=session_id,
        user_id=user_id,
        add_history_to_context=True,
        num_history_runs=10,
        markdown=True,
        show_tool_calls=False,
    )

    return agent, mcp_ctx


def get_postgres_db(database_url: Optional[str] = None):
    """Crea una instancia de PostgresDb para persistencia de sesión.

    Args:
        database_url: Connection string PostgreSQL. Si None, usa DATABASE_URL del env.
                      Formato Cloud SQL: postgresql+psycopg://user:pass@/db?host=/cloudsql/PROJECT:REGION:INSTANCE

    Returns:
        PostgresDb instance o None si no hay configuración de DB
    """
    url = database_url or os.environ.get("DATABASE_URL")
    if not url:
        logger.info("DATABASE_URL no configurado — sesiones no se persistirán")
        return None

    try:
        from agno.db.postgres import PostgresDb
        return PostgresDb(
            db_url=url,
            session_table="panelin_agent_sessions",
        )
    except Exception as exc:
        logger.warning("No se pudo conectar a PostgreSQL: %s", exc)
        return None
