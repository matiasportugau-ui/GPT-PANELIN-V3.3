"""
Panelin v5.0 — Google Sheets Integration Tools
==================================================

Wraps existing Wolf API Sheets endpoints as Agno-compatible tools.
These tools allow the agent to read/write to the BMC quotation tracker.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def sheets_read_consultations(
    estado: Optional[str] = None,
    cliente: Optional[str] = None,
    limit: int = 20,
) -> str:
    """Lee las consultas del Administrador de Cotizaciones en Google Sheets.

    Args:
        estado: Filtrar por estado (Pendiente, Enviado, Cerrado, etc.)
        cliente: Filtrar por nombre de cliente
        limit: Máximo de resultados (default 20)

    Returns:
        JSON con las consultas encontradas.
    """
    import httpx
    from src.core.config import get_settings

    settings = get_settings()
    params = {"limit": limit}
    if estado:
        params["estado"] = estado
    if cliente:
        params["cliente"] = cliente

    try:
        resp = httpx.get(
            f"http://localhost:{settings.port}/legacy/sheets/consultations",
            params=params,
            headers={"X-API-Key": settings.wolf_api_key},
            timeout=15,
        )
        return resp.text
    except Exception as e:
        return json.dumps({"error": str(e)})


def sheets_add_consultation(
    cliente: str,
    consulta: str,
    telefono: str = "",
    direccion: str = "",
    origen: str = "PANELIN",
    asignado: str = "",
) -> str:
    """Agrega una nueva consulta al Administrador de Cotizaciones en Google Sheets.

    Args:
        cliente: Nombre del cliente
        consulta: Descripción de la consulta
        telefono: Teléfono del cliente
        direccion: Dirección de la obra
        origen: Origen de la consulta (PANELIN, WEB, WHATSAPP, etc.)
        asignado: Vendedor asignado

    Returns:
        JSON con el resultado de la operación.
    """
    import httpx
    from src.core.config import get_settings

    settings = get_settings()
    try:
        resp = httpx.post(
            f"http://localhost:{settings.port}/legacy/sheets/consultations",
            json={
                "cliente": cliente,
                "consulta": consulta,
                "telefono": telefono,
                "direccion": direccion,
                "origen": origen,
                "asignado": asignado,
            },
            headers={"X-API-Key": settings.wolf_api_key},
            timeout=15,
        )
        return resp.text
    except Exception as e:
        return json.dumps({"error": str(e)})


def sheets_search(
    query: str,
    limit: int = 20,
) -> str:
    """Busca en el Administrador de Cotizaciones por cliente o consulta.

    Args:
        query: Texto de búsqueda (mínimo 2 caracteres)
        limit: Máximo de resultados

    Returns:
        JSON con los resultados de búsqueda.
    """
    import httpx
    from src.core.config import get_settings

    settings = get_settings()
    try:
        resp = httpx.get(
            f"http://localhost:{settings.port}/legacy/sheets/search",
            params={"q": query, "limit": limit},
            headers={"X-API-Key": settings.wolf_api_key},
            timeout=15,
        )
        return resp.text
    except Exception as e:
        return json.dumps({"error": str(e)})


def sheets_update_status(
    row_number: int,
    estado: str,
    comentarios: str = "",
) -> str:
    """Actualiza el estado de una consulta en Google Sheets.

    Args:
        row_number: Número de fila a actualizar
        estado: Nuevo estado (Pendiente, Enviado, Cerrado, etc.)
        comentarios: Comentarios adicionales (se agregan al existente)

    Returns:
        JSON con el resultado de la operación.
    """
    import httpx
    from src.core.config import get_settings

    settings = get_settings()
    data = {"row_number": row_number, "estado": estado}
    if comentarios:
        data["comentarios"] = comentarios

    try:
        resp = httpx.patch(
            f"http://localhost:{settings.port}/legacy/sheets/update_row",
            json=data,
            headers={"X-API-Key": settings.wolf_api_key},
            timeout=15,
        )
        return resp.text
    except Exception as e:
        return json.dumps({"error": str(e)})


SHEETS_TOOLS = [
    sheets_read_consultations,
    sheets_add_consultation,
    sheets_search,
    sheets_update_status,
]
