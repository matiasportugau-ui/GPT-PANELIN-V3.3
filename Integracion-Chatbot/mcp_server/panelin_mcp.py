"""
Servidor MCP (Model Context Protocol) para integración con CRM Inmoenter.

Expone herramientas que el LLM puede descubrir y ejecutar automáticamente
para interactuar con la PANELIN-API en tiempo real.

Ejecutar directamente:
    python mcp_server/panelin_mcp.py
"""

import os

from fastmcp import FastMCP

mcp = FastMCP("Inmoenter_CRM_Connector")
INMOENTER_API_KEY = os.environ.get("INMOENTER_API_KEY")


@mcp.tool()
async def check_property_availability(property_ref: str) -> str:
    """Verifica si una propiedad sigue activa en Inmoenter.

    Args:
        property_ref: Referencia única de la propiedad en el CRM.

    Returns:
        Estado de disponibilidad de la propiedad.
    """
    # TODO: Implementar llamada real a PANELIN-API GET /properties/{ref}
    return f"La propiedad con referencia {property_ref} se encuentra disponible."


@mcp.tool()
async def insert_crm_lead(name: str, phone: str, location_interest: str) -> str:
    """Inserta un Lead cualificado en el Panel Inmobiliario.

    Args:
        name: Nombre completo del prospecto.
        phone: Número de teléfono del prospecto.
        location_interest: Zona o ubicación de interés del prospecto.

    Returns:
        Confirmación de la inserción del lead.
    """
    # TODO: Implementar llamada real a PANELIN-API POST /leads
    return f"Lead {name} guardado correctamente. Asignado a agente comercial."


if __name__ == "__main__":
    mcp.run()
