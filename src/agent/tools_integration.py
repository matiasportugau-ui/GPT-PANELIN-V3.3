"""
Panelin Agno — Integration Tools
==================================

Herramientas Agno que envuelven los sistemas externos existentes:
    - PDF generation (panelin_reports/ via wolf_api)
    - Google Sheets (CRM integration via wolf_api)
    - Wolf API endpoints (pricing lookup, catalog search)

Estas herramientas permiten al agente invocar la infraestructura existente
sin modificarla. El agente puede generar PDFs, registrar cotizaciones en
Sheets, y buscar en el catálogo completo.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import httpx
from agno.tools import tool

from src.core.config import settings


def _get_wolf_headers() -> dict:
    """Headers de autenticación para Wolf API."""
    return {
        "X-API-Key": settings.wolf_api_key or os.getenv("WOLF_API_KEY", ""),
        "Content-Type": "application/json",
    }


def _get_wolf_base_url() -> str:
    """URL base del Wolf API."""
    return settings.wolf_api_url.rstrip("/")


@tool
def buscar_productos_catalogo(
    query: str,
    familia: Optional[str] = None,
    espesor_mm: Optional[int] = None,
    limite: int = 10,
) -> str:
    """Busca productos en el catálogo completo de BMC Uruguay.

    Consulta el Wolf API para búsqueda con filtros. Retorna productos
    con SKU, descripción, especificaciones y precio.

    Args:
        query: Texto de búsqueda libre (ej: "techo 80mm aislante")
        familia: Filtrar por familia de producto (ISOROOF, ISODEC, etc.)
        espesor_mm: Filtrar por espesor en mm
        limite: Máximo número de resultados (default: 10)

    Returns:
        JSON con lista de productos encontrados
    """
    url = f"{_get_wolf_base_url()}/find_products"
    payload: Dict[str, Any] = {"query": query, "limit": limite}
    if familia:
        payload["familia"] = familia
    if espesor_mm:
        payload["espesor_mm"] = espesor_mm

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload, headers=_get_wolf_headers())
            response.raise_for_status()
            return json.dumps(response.json(), ensure_ascii=False, indent=2)
    except httpx.TimeoutException:
        return json.dumps({"error": "Timeout consultando catálogo. Intentá de nuevo."}, ensure_ascii=False)
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"Error del servidor: {e.response.status_code}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Error consultando catálogo: {str(e)}"}, ensure_ascii=False)


@tool
def consultar_reglas_negocio() -> str:
    """Consulta las reglas de negocio vigentes de BMC Uruguay.

    Retorna: tasa IVA, moneda, política de flete, espesores disponibles,
    y otras reglas configuradas en el Wolf API.

    Returns:
        JSON con reglas de negocio actuales
    """
    url = f"{_get_wolf_base_url()}/business_rules"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, headers=_get_wolf_headers())
            response.raise_for_status()
            return json.dumps(response.json(), ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "iva_rate": 0.22,
            "currency": "USD",
            "nota": f"No se pudo conectar al Wolf API: {str(e)}. Usando valores por defecto.",
        }, ensure_ascii=False)


@tool
def registrar_consulta_sheets(
    nombre_cliente: str,
    telefono: str,
    descripcion_obra: str,
    origen: str = "Agno",
    asignado_a: Optional[str] = None,
) -> str:
    """Registra una consulta de cliente en Google Sheets (CRM).

    Agrega una fila en la hoja de consultas del año activo con los
    datos del cliente y la descripción de la obra.

    Args:
        nombre_cliente: Nombre del cliente
        telefono: Teléfono de contacto (formato uruguayo: 09XXXXXXX)
        descripcion_obra: Descripción de la obra o consulta
        origen: Origen del lead (default: "Agno")
        asignado_a: Vendedor asignado (opcional)

    Returns:
        JSON con confirmación del registro o mensaje de error
    """
    url = f"{_get_wolf_base_url()}/sheets/consultations"
    payload = {
        "nombre": nombre_cliente,
        "telefono": telefono,
        "descripcion": descripcion_obra,
        "origen": origen,
        "estado": "Pendiente",
    }
    if asignado_a:
        payload["asignado"] = asignado_a

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(url, json=payload, headers=_get_wolf_headers())
            response.raise_for_status()
            return json.dumps({
                "registrado": True,
                "mensaje": f"Consulta de {nombre_cliente} registrada en Sheets",
                "datos": response.json(),
            }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "registrado": False,
            "error": f"No se pudo registrar en Sheets: {str(e)}",
            "nota": "Registrá manualmente: el lead fue atendido.",
        }, ensure_ascii=False)


@tool
def generar_pdf_cotizacion(
    datos_cotizacion: str,
    nombre_cliente: str,
    nombre_obra: Optional[str] = None,
    subir_a_drive: bool = True,
) -> str:
    """Genera un PDF profesional de la cotización y lo sube a Google Drive.

    Usa el sistema de generación PDF existente (ReportLab + Drive upload).
    El PDF incluye: header BMC, tabla de materiales, totales, y datos bancarios.

    Args:
        datos_cotizacion: JSON string con los datos de la cotización (output del motor v4)
        nombre_cliente: Nombre del cliente para el PDF
        nombre_obra: Descripción de la obra (opcional)
        subir_a_drive: Si True, sube el PDF a Google Drive y retorna la URL

    Returns:
        JSON con URL del PDF en Drive o mensaje de error
    """
    url = f"{_get_wolf_base_url()}/cotizaciones/generar_pdf"

    try:
        quote_data = json.loads(datos_cotizacion) if isinstance(datos_cotizacion, str) else datos_cotizacion
    except json.JSONDecodeError:
        return json.dumps({"error": "datos_cotizacion debe ser un JSON válido"}, ensure_ascii=False)

    payload = {
        "cliente": {
            "nombre": nombre_cliente,
            "obra": nombre_obra or "A confirmar",
        },
        "cotizacion": quote_data,
        "subir_drive": subir_a_drive,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload, headers=_get_wolf_headers())
            response.raise_for_status()
            result = response.json()
            return json.dumps({
                "generado": True,
                "url": result.get("drive_url") or result.get("url"),
                "mensaje": f"PDF generado para {nombre_cliente}",
            }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "generado": False,
            "error": f"Error generando PDF: {str(e)}",
        }, ensure_ascii=False)


@tool
def persistir_conversacion(
    session_id: str,
    mensajes: str,
    metadata: Optional[str] = None,
) -> str:
    """Persiste el historial de conversación en Google Cloud Storage.

    Usa el endpoint /kb/conversations del Wolf API para archivar la
    conversación en JSONL para análisis y aprendizaje futuro.

    Args:
        session_id: ID de la sesión conversacional
        mensajes: JSON array string con los mensajes de la conversación
        metadata: JSON string con metadata adicional (cliente, cotización, etc.)

    Returns:
        JSON con confirmación de persistencia
    """
    url = f"{_get_wolf_base_url()}/kb/conversations"

    try:
        msgs = json.loads(mensajes) if isinstance(mensajes, str) else mensajes
        meta = json.loads(metadata) if metadata and isinstance(metadata, str) else metadata
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"JSON inválido: {str(e)}"}, ensure_ascii=False)

    payload = {
        "session_id": session_id,
        "messages": msgs,
        "metadata": meta or {},
        "source": "panelin_agno",
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(url, json=payload, headers=_get_wolf_headers())
            response.raise_for_status()
            return json.dumps({"persistido": True, "session_id": session_id}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "persistido": False,
            "error": f"Error persistiendo conversación: {str(e)}",
        }, ensure_ascii=False)
