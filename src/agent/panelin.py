"""
Panelin Agno — Agente Conversacional
======================================

Agente principal que:
  - Controla la conversación con el cliente (en español)
  - Llama al pipeline determinístico v4.0 via tools
  - Mantiene memoria conversacional en PostgreSQL (Cloud SQL)
  - Aplica guardrails: NUNCA inventa precios
  - Conecta al MCP server existente (18 tools) via SSE
  - Expone endpoints via AgentOS Playground

El agente POSEE el razonamiento — no depende de Custom GPT de OpenAI.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.decorator import tool

from src.quotation.tools import (
    buscar_productos,
    calcular_bom_manual,
    calcular_cotizacion,
    calcular_cotizacion_detallada,
    obtener_precios_paneles,
    validar_solicitud_formal,
)

logger = logging.getLogger(__name__)


# ─── Sistema de instrucciones ─────────────────────────────────────────────────

PANELIN_SYSTEM = """
Eres Panelin, el asistente comercial-técnico de BMC Uruguay especializado en paneles de construcción.

## Tu rol
- Asesor técnico y comercial de paneles (ISODEC, ISOPANEL, ISOROOF, ISOWALL, ISOFRIG)
- Genera cotizaciones técnico-comerciales profesionales
- Responde SIEMPRE en español

## Productos que maneja BMC Uruguay
- **ISODEC**: Panels de techo con chapa de acero + núcleo EPS/PIR
- **ISOROOF (3G)**: Sistema de techo modular tricapa con cubierta incorporada
- **ISOPANEL**: Paneles de pared EPS con chapa
- **ISOWALL**: Paneles de pared PIR premium
- **ISOFRIG**: Paneles para cámaras frigoríficas

## Reglas ABSOLUTAS (nunca violar)
1. **NUNCA inventar precios** — todos los precios vienen exclusivamente del catálogo oficial.
   Si un precio no existe en el catálogo, dí "consultar precio" o "precio a confirmar".
2. **NUNCA calcular precio = costo × margen** — los precios de catálogo ya incluyen IVA 22%.
3. Cuando el cliente pregunta el precio, SIEMPRE usar la tool `obtener_precios_paneles` o
   `calcular_cotizacion` para obtener valores reales.
4. En cotizaciones formales, verificar datos completos antes de emitir.
5. Los cálculos de BOM son determinísticos — no aproximar cantidades de materiales.

## Flujo de cotización
1. **Informativo**: Información rápida de productos o precios aproximados
2. **Pre-cotización**: Con supuestos razonables cuando faltan datos, no bloqueante
3. **Formal**: Todos los datos verificados, cotización oficial emitible

## Datos necesarios para cotización
- Familia y espesor del panel (ej: ISODEC 100mm)
- Uso: techo o pared
- Dimensiones: largo y ancho en metros (o número de paneles)
- Tipo de estructura: metálica, hormigón, madera
- Para techos: tipo (1 agua, 2 aguas, 4 aguas, mariposa) y span entre apoyos
- Nombre, teléfono y ubicación del cliente (para cotización formal)

## Tono y formato
- Formal pero accesible — estilo profesional técnico-comercial
- Usar tablas para BOM y precios cuando corresponda
- Incluir notas técnicas relevantes
- Señalar supuestos usados en pre-cotización
- Para cotizaciones formales, incluir número de cotización (PV4-YYYYMMDD-XXXXXXXX)
"""


# ─── Guardrail: Anti-precio-inventado ────────────────────────────────────────

@tool(
    name="verificar_precio_en_kb",
    description="OBLIGATORIO usar antes de mencionar cualquier precio. Verifica que el precio exista en el catálogo oficial BMC Uruguay.",
)
def verificar_precio_en_kb(
    familia: str,
    espesor_mm: Optional[int] = None,
) -> str:
    """Verifica que el precio de un producto exista en la KB antes de mencionarlo.

    Si no existe → informa que el precio se debe consultar directamente.
    Si existe → retorna el precio real del catálogo con IVA incluido.

    REGLA: Este verificador DEBE ser llamado antes de mencionar cualquier precio.
    """
    return obtener_precios_paneles(familia=familia, espesor_mm=espesor_mm)


# ─── Registrar tools del dominio como Agno tools ─────────────────────────────

@tool(name="calcular_cotizacion_panelin")
def tool_calcular_cotizacion(
    texto: str,
    modo: str = "pre_cotizacion",
    nombre_cliente: Optional[str] = None,
    telefono_cliente: Optional[str] = None,
    ubicacion_cliente: Optional[str] = None,
) -> str:
    """Calcula cotización completa de paneles BMC Uruguay.

    Ejecuta el pipeline determinístico v4.0 con BOM + precios reales del catálogo.
    Siempre usar esta tool cuando el cliente pide una cotización con dimensiones.

    Args:
        texto: Descripción del proyecto en español.
        modo: pre_cotizacion (default) | formal | informativo.
        nombre_cliente: Nombre del cliente.
        telefono_cliente: Teléfono del cliente.
        ubicacion_cliente: Departamento o ciudad.
    """
    return calcular_cotizacion(
        texto=texto,
        modo=modo,
        nombre_cliente=nombre_cliente,
        telefono_cliente=telefono_cliente,
        ubicacion_cliente=ubicacion_cliente,
    )


@tool(name="buscar_en_catalogo")
def tool_buscar_productos(consulta: str) -> str:
    """Busca productos en el catálogo oficial de BMC Uruguay.

    Args:
        consulta: Término de búsqueda (ej: 'ISODEC 100mm', 'perfil U', 'gotero').
    """
    return buscar_productos(consulta=consulta)


@tool(name="precios_por_familia")
def tool_precios_paneles(familia: str, espesor_mm: Optional[int] = None) -> str:
    """Obtiene lista de precios de paneles por familia y espesor del catálogo oficial.

    Precios con IVA 22% incluido. NUNCA usar precios inventados.

    Args:
        familia: ISODEC | ISOPANEL | ISOROOF | ISOWALL | ISOFRIG.
        espesor_mm: Espesor en mm (50, 75, 100, 120, 150). Opcional.
    """
    return obtener_precios_paneles(familia=familia, espesor_mm=espesor_mm)


@tool(name="validar_datos_para_formal")
def tool_validar_formal(texto: str) -> str:
    """Verifica si una solicitud tiene todos los datos para emitir cotización formal.

    Útil antes de generar una cotización oficial para identificar datos faltantes.

    Args:
        texto: Descripción del proyecto a validar.
    """
    return validar_solicitud_formal(texto=texto)


@tool(name="calcular_bom_detallado")
def tool_calcular_bom(
    familia: str,
    sub_familia: str,
    espesor_mm: int,
    uso: str,
    largo_m: float,
    ancho_m: float,
    tipo_estructura: str = "metal",
    tipo_techo: Optional[str] = None,
) -> str:
    """Calcula BOM con parámetros explícitos (útil para verificar materiales).

    Args:
        familia: ISODEC | ISOPANEL | ISOROOF | ISOWALL | ISOFRIG.
        sub_familia: EPS | PIR | PUR | 3G.
        espesor_mm: Espesor en mm.
        uso: techo | pared | camara.
        largo_m: Largo en metros.
        ancho_m: Ancho en metros.
        tipo_estructura: metal | hormigon | madera.
        tipo_techo: 1_agua | 2_aguas | 4_aguas | mariposa.
    """
    return calcular_bom_manual(
        familia=familia,
        sub_familia=sub_familia,
        espesor_mm=espesor_mm,
        uso=uso,
        largo_m=largo_m,
        ancho_m=ancho_m,
        tipo_estructura=tipo_estructura,
        tipo_techo=tipo_techo,
    )


# ─── Factory del agente ───────────────────────────────────────────────────────

def build_panelin_agent(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    db=None,
    mcp_tools=None,
) -> Agent:
    """Construye el agente Panelin listo para usar.

    Args:
        session_id: ID de sesión para memoria conversacional persistente.
        user_id: ID del usuario (cliente) para memoria entre sesiones.
        db: PostgresDb para almacenar sesiones y memoria en Cloud SQL.
        mcp_tools: MCPTools conectado al servidor MCP existente (opcional).

    Returns:
        Agent configurado con todas las tools, memoria y guardrails.
    """
    from src.core.config import get_settings

    settings = get_settings()

    model = OpenAIChat(
        id=settings.default_model,
        api_key=settings.openai_api_key or None,
        temperature=0.1,
        max_tokens=2048,
    )

    all_tools = [
        tool_calcular_cotizacion,
        tool_buscar_productos,
        tool_precios_paneles,
        tool_validar_formal,
        tool_calcular_bom,
        verificar_precio_en_kb,
    ]

    if mcp_tools is not None:
        all_tools.append(mcp_tools)

    agent = Agent(
        model=model,
        name="Panelin",
        description="Asistente técnico-comercial de BMC Uruguay para cotizaciones de paneles de construcción.",
        instructions=[PANELIN_SYSTEM],
        tools=all_tools,
        db=db,
        session_id=session_id,
        user_id=user_id,
        # Memoria conversacional
        add_history_to_context=True,
        num_history_runs=10,
        enable_agentic_memory=True,
        update_memory_on_run=True,
        # Sesión persistente
        cache_session=True,
        # Output
        markdown=True,
        stream=True,
        # Debug
        debug_mode=settings.debug,
    )

    return agent


def get_mcp_tools(mcp_url: Optional[str] = None):
    """Crea MCPTools conectado al servidor MCP existente via SSE.

    El servidor MCP expone las 18 tools de Panelin (pricing, catalog, BOM, etc.)
    via Server-Sent Events en el puerto 8000.

    Args:
        mcp_url: URL del servidor MCP SSE. Por defecto lee de PANELIN_MCP_SERVER_URL.

    Returns:
        MCPTools listo para agregar al agente, o None si el servidor no está disponible.
    """
    from src.core.config import get_settings

    settings = get_settings()
    url = mcp_url or settings.mcp_server_url

    try:
        from agno.tools.mcp import MCPTools

        mcp = MCPTools(
            url=url,
            transport="sse",
            timeout=settings.mcp_server_timeout,
        )
        logger.info(f"MCPTools conectado a {url}")
        return mcp
    except Exception as exc:
        logger.warning(f"MCP server no disponible en {url}: {exc}. Continuando sin MCP tools.")
        return None


def build_panelin_agent_with_mcp(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    db=None,
    mcp_url: Optional[str] = None,
) -> Agent:
    """Construye el agente con MCPTools + todas las tools del dominio.

    Este es el agente completo para producción con las 18 tools del MCP server.
    """
    mcp_tools = get_mcp_tools(mcp_url=mcp_url)
    return build_panelin_agent(
        session_id=session_id,
        user_id=user_id,
        db=db,
        mcp_tools=mcp_tools,
    )
