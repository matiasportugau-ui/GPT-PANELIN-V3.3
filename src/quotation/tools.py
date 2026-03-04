"""
Panelin v5.0 — Agno tool wrappers for the quotation engine.

Each function is a standalone tool the Agno agent can call.
All prices come exclusively from KB files — NEVER invented.
"""

from __future__ import annotations

import json
from typing import Optional

from src.quotation.service import QuotationService


def calculate_quotation(
    text: str,
    mode: str = "pre_cotizacion",
    client_name: Optional[str] = None,
    client_phone: Optional[str] = None,
    client_location: Optional[str] = None,
) -> str:
    """Calcula una cotización completa de paneles BMC Uruguay.

    Ejecuta el pipeline completo: classify → parse → SRE → BOM → pricing → validate.
    Los precios provienen EXCLUSIVAMENTE de la base de conocimiento (KB).

    Args:
        text: Descripción en texto libre de lo que el cliente necesita (español).
              Ejemplo: "Isodec EPS 100mm 6 paneles de 6.5m techo completo a metal"
        mode: Modo de cotización: "informativo", "pre_cotizacion", o "formal".
        client_name: Nombre del cliente (opcional).
        client_phone: Teléfono del cliente (opcional).
        client_location: Ubicación del cliente (opcional).

    Returns:
        JSON con la cotización completa incluyendo BOM, precios, y validación.
    """
    result = QuotationService.full_pipeline(
        text=text,
        force_mode=mode,
        client_name=client_name,
        client_phone=client_phone,
        client_location=client_location,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


def classify_request(text: str) -> str:
    """Clasifica una solicitud de cotización (techo, pared, accesorios, etc.).

    Determina el tipo de solicitud y el modo de operación adecuado.

    Args:
        text: Texto de la solicitud en español.

    Returns:
        JSON con tipo de solicitud, modo, y señales de detección.
    """
    result = QuotationService.classify(text)
    return json.dumps(result, ensure_ascii=False, indent=2)


def parse_request(text: str) -> str:
    """Parsea texto libre en español a un QuoteRequest estructurado.

    Extrae familia de panel, espesor, dimensiones, tipo de estructura,
    datos del cliente, y accesorios solicitados.

    Args:
        text: Texto de la solicitud en español.

    Returns:
        JSON con los datos estructurados extraídos del texto.
    """
    result = QuotationService.parse(text)
    return json.dumps(result, ensure_ascii=False, indent=2)


def calculate_sai_score(
    text: str,
    mode: str = "pre_cotizacion",
) -> str:
    """Calcula el SAI (System Accuracy Index) para una cotización.

    El SAI es un score de 0-100 que mide la calidad de la cotización.

    Args:
        text: Texto de la solicitud para cotizar.
        mode: Modo de cotización.

    Returns:
        JSON con el score SAI, grado (A-F), y detalles de penalidades/bonos.
    """
    output = QuotationService.full_pipeline(text=text, force_mode=mode)
    sai = QuotationService.compute_sai(output)
    return json.dumps(
        {"quote_id": output["quote_id"], "sai": sai},
        ensure_ascii=False,
        indent=2,
    )
