"""
Panelin Agno — Agente Conversacional
======================================

Agente conversacional para cotizaciones BMC Uruguay.
El agente posee:
    - Herramientas para invocar el motor panelin_v4
    - Memoria conversacional persistente en PostgreSQL (Cloud SQL)
    - Acceso a las 22 herramientas MCP existentes via MCPTools
    - Guardrail implícito: NUNCA inventa precios (tools son determinísticas)

Diferencia con el workflow:
    - El workflow es un pipeline SECUENCIAL determinístico
    - El agente es CONVERSACIONAL: mantiene contexto, responde preguntas,
      y decide cuándo invocar herramientas según el contexto

Uso típico:
    1. Chat libre con el cliente → el agente clasifica la intención
    2. Si es cotización → invoca calcular_cotizacion_completa()
    3. Si es consulta técnica → invoca validar_vano_autoportancia() etc.
    4. Mantiene el contexto entre mensajes de la misma sesión
"""

from __future__ import annotations

import os
from typing import List, Optional

from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.models.openai import OpenAIChat
from agno.tools import tool

from src.core.config import settings
from src.quotation.tools import (
    buscar_accesorio,
    calcular_bom,
    calcular_cotizacion_completa,
    clasificar_solicitud,
    validar_vano_autoportancia,
    verificar_precio_panel,
)


PANELIN_SYSTEM_INSTRUCTIONS = """Sos Panelin, el asistente de cotizaciones técnico-comerciales de BMC Uruguay.

MISIÓN: Ayudar a clientes y vendedores a generar cotizaciones precisas para paneles
de construcción: ISODEC, ISOPANEL, ISOROOF, ISOWALL e ISOFRIG.

CAPACIDADES:
- Cotizar paneles de techo, pared, y cámara fría
- Calcular BOM (lista de materiales) con accesorios
- Verificar precios del catálogo oficial BMC
- Validar vanos de autoportancia estructural
- Buscar accesorios compatibles por familia y espesor

REGLAS ABSOLUTAS (nunca violarlas):
1. NUNCA inventés precios — usá SIEMPRE las herramientas para consultar el catálogo
2. Si un precio no está en el catálogo, decilo explícitamente y sugerí consultar a ventas
3. El IVA 22% SIEMPRE está incluido en los precios del catálogo
4. Respondé en español rioplatense (vos, ustedes)
5. Sé técnicamente preciso — los clientes son constructores y arquitectos

MODOS DE COTIZACIÓN:
- Informativo: consulta general de precios o especificaciones
- Pre-cotización: presupuesto preliminar con datos parciales (se indican supuestos)
- Formal: cotización certificada con todos los datos completos

FAMILIAS DE PRODUCTOS:
- ISOROOF: Paneles de techo autoportante (EPS, PIR, PUR)
- ISODEC: Paneles para deck/cubierta (EPS, PIR)
- ISOPANEL: Paneles de pared interior/exterior (EPS)
- ISOWALL: Paneles de pared de alto rendimiento (PIR)
- ISOFRIG: Paneles para cámaras frigoríficas

FLUJO RECOMENDADO:
1. Si el cliente pide cotización → usá calcular_cotizacion_completa()
2. Si pregunta por precio específico → usá verificar_precio_panel()
3. Si pregunta por vano/estructura → usá validar_vano_autoportancia()
4. Si pregunta por accesorios → usá buscar_accesorio()

FORMATO DE RESPUESTA:
- Sé conciso pero completo
- Usá tablas para materiales y precios
- Destacá el total en USD con IVA incluido
- Mencioná condiciones o supuestos utilizados"""


def create_panelin_agent(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    mcp_tools: Optional[object] = None,
) -> Agent:
    """Crea el agente conversacional Panelin.

    Args:
        session_id: ID de sesión para persistencia de conversación en PostgreSQL.
                    Si se provee, el agente recuerda el historial de la sesión.
        user_id: ID del usuario para asociar memorias y preferencias.
        mcp_tools: Instancia de MCPTools conectada al servidor MCP (opcional).
                   Si se provee, el agente tiene acceso a las 22 herramientas MCP.

    Returns:
        Agente Agno configurado para cotizaciones BMC
    """
    db = None
    if settings.agno_db_url:
        db = PostgresDb(
            db_url=settings.agno_db_url,
            session_table=settings.agent_session_table,
        )

    tools_list = [
        calcular_cotizacion_completa,
        verificar_precio_panel,
        calcular_bom,
        clasificar_solicitud,
        validar_vano_autoportancia,
        buscar_accesorio,
    ]

    if mcp_tools is not None:
        tools_list.append(mcp_tools)

    agent = Agent(
        name="Panelin",
        id="panelin-bmc-uruguay",
        model=OpenAIChat(
            id=settings.openai_model,
            api_key=settings.openai_api_key or os.getenv("OPENAI_API_KEY", ""),
        ),
        description="Asistente de cotizaciones técnico-comerciales para BMC Uruguay",
        instructions=PANELIN_SYSTEM_INSTRUCTIONS,
        tools=tools_list,
        db=db,
        session_id=session_id,
        user_id=user_id,
        add_history_to_context=True,
        num_history_runs=10,
        markdown=True,
        debug_mode=settings.debug,
        add_datetime_to_context=True,
    )

    return agent


async def create_panelin_agent_with_mcp(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> tuple[Agent, object]:
    """Crea el agente Panelin con MCPTools conectado al servidor MCP SSE.

    Usa el servidor MCP existente en puerto 8000 (SSE transport).
    Retorna (agent, mcp_tools) — el llamador debe cerrar mcp_tools al terminar.

    NOTA: SSE transport está disponible pero el MCP protocol prefiere Streamable HTTP.
    Mantener SSE para compatibilidad con el servidor MCP existente.

    Args:
        session_id: ID de sesión para persistencia
        user_id: ID del usuario

    Returns:
        Tupla (agent, mcp_tools) — el llamador debe llamar await mcp_tools.close()
    """
    from agno.tools.mcp import MCPTools

    mcp_tools = MCPTools(
        url=settings.mcp_server_url,
        transport="sse",
    )
    await mcp_tools.connect()

    agent = create_panelin_agent(
        session_id=session_id,
        user_id=user_id,
        mcp_tools=mcp_tools,
    )

    return agent, mcp_tools


async def run_panelin_agent(
    message: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> str:
    """Ejecuta una interacción con el agente Panelin.

    Shortcut para uso en la API. Gestiona el ciclo de vida de MCPTools.

    Args:
        message: Mensaje del usuario en español
        session_id: ID de sesión para historial conversacional
        user_id: ID del usuario

    Returns:
        Respuesta del agente en español
    """
    if settings.mcp_server_url:
        try:
            from agno.tools.mcp import MCPTools
            async with MCPTools(url=settings.mcp_server_url, transport="sse") as mcp:
                agent = create_panelin_agent(
                    session_id=session_id,
                    user_id=user_id,
                    mcp_tools=mcp,
                )
                response = await agent.arun(message)
                if hasattr(response, "content"):
                    return response.content
                return str(response)
        except Exception:
            pass

    agent = create_panelin_agent(session_id=session_id, user_id=user_id)
    response = await agent.arun(message)
    if hasattr(response, "content"):
        return response.content
    return str(response)
