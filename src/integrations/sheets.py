"""
Panelin v5.0 — Google Sheets Integration Tools

Wraps the existing Wolf API Google Sheets endpoints as standalone functions
that the Agno agent can call as tools.
"""

from __future__ import annotations

import json
from typing import Optional

import httpx

from src.core.config import get_settings


def _get_client() -> tuple[str, dict[str, str]]:
    settings = get_settings()
    headers = {}
    if settings.wolf_api_key:
        headers["X-API-Key"] = settings.wolf_api_key
    return settings.wolf_api_url, headers


def search_clients(query: str, tab: Optional[str] = None) -> str:
    """Busca clientes en Google Sheets por nombre, teléfono o consulta.

    Args:
        query: Término de búsqueda.
        tab: Pestaña específica (opcional).

    Returns:
        JSON con resultados de búsqueda.
    """
    base, headers = _get_client()
    params = {"q": query}
    if tab:
        params["tab"] = tab

    try:
        resp = httpx.get(f"{base}/sheets/search", params=params, headers=headers, timeout=15)
        return resp.text
    except Exception as e:
        return json.dumps({"error": str(e)})


def add_consultation(
    cliente: str,
    consulta: str,
    telefono: str = "",
    origen: str = "panelin_agent",
) -> str:
    """Registra una nueva consulta en Google Sheets.

    Args:
        cliente: Nombre del cliente.
        consulta: Descripción de la consulta.
        telefono: Teléfono del cliente.
        origen: Canal de origen.

    Returns:
        JSON con confirmación.
    """
    base, headers = _get_client()
    payload = {
        "cliente": cliente,
        "consulta": consulta,
        "telefono": telefono,
        "origen": origen,
    }
    try:
        resp = httpx.post(f"{base}/sheets/consultations", json=payload, headers=headers, timeout=15)
        return resp.text
    except Exception as e:
        return json.dumps({"error": str(e)})


def add_quotation_line(
    row_number: int,
    quote_id: str,
    total_usd: float,
    detalle: str = "",
) -> str:
    """Agrega una línea de cotización a Google Sheets.

    Args:
        row_number: Número de fila a actualizar.
        quote_id: ID de la cotización.
        total_usd: Total en USD.
        detalle: Detalle adicional.

    Returns:
        JSON con confirmación.
    """
    base, headers = _get_client()
    payload = {
        "row_number": row_number,
        "quote_id": quote_id,
        "total_usd": total_usd,
        "detalle": detalle,
    }
    try:
        resp = httpx.post(f"{base}/sheets/quotation_line", json=payload, headers=headers, timeout=15)
        return resp.text
    except Exception as e:
        return json.dumps({"error": str(e)})


def get_sheet_stats() -> str:
    """Obtiene estadísticas del Google Sheet de cotizaciones.

    Returns:
        JSON con cantidad de filas, últimas actualizaciones, etc.
    """
    base, headers = _get_client()
    try:
        resp = httpx.get(f"{base}/sheets/stats", headers=headers, timeout=15)
        return resp.text
    except Exception as e:
        return json.dumps({"error": str(e)})
