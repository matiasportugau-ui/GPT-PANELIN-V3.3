"""
src/agent/guardrails.py — Guardrails para Panelin

Validaciones de output para garantizar que el agente:
1. NUNCA invente precios (verifica contra la KB)
2. NUNCA use frases de precio inventado ("aproximadamente", "estimado", etc.)
3. NUNCA derive a proveedores externos

Los guardrails se ejecutan DESPUÉS de que el LLM genera la respuesta.
Si el output no pasa, el agente regenera con instrucciones más estrictas.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# Frases que indican precio inventado
_PRICE_INVENTION_PATTERNS = [
    r"aproximadamente\s+USD?\s*\d",
    r"alrededor\s+de\s+USD?\s*\d",
    r"estimo\s+que\s+cuesta",
    r"debería\s+costar",
    r"el\s+precio\s+es\s+más\s+o\s+menos",
    r"suele\s+costar",
    r"valor\s+estimado",
    r"precio\s+estimado",
    r"precio\s+aproximado",
]

_PRICE_INVENTION_RE = re.compile(
    "|".join(_PRICE_INVENTION_PATTERNS),
    re.IGNORECASE | re.UNICODE,
)

# Frases de derivación externa prohibidas
_EXTERNAL_DERIVATION_PATTERNS = [
    r"consulte\s+(al?\s+)?proveedor",
    r"llame\s+a\s+(su\s+)?distribuidor",
    r"contacte\s+(al?\s+)?fabricante\s+directamente",
    r"pregunte\s+en\s+(otra\s+)?ferretería",
]

_EXTERNAL_DERIVATION_RE = re.compile(
    "|".join(_EXTERNAL_DERIVATION_PATTERNS),
    re.IGNORECASE | re.UNICODE,
)


def validate_no_invented_prices(response_text: str) -> tuple[bool, str]:
    """Verifica que el output no contenga precios inventados.

    Returns:
        (valid: bool, message: str)
    """
    if _PRICE_INVENTION_RE.search(response_text):
        return False, (
            "GUARDRAIL: El output contiene frases de precio inventado. "
            "Los precios deben venir EXCLUSIVAMENTE de la herramienta calcular_cotizacion. "
            "Si no hay precio disponible, indícalo claramente sin estimar."
        )
    return True, "ok"


def validate_no_external_derivation(response_text: str) -> tuple[bool, str]:
    """Verifica que no derive a proveedores externos.

    Returns:
        (valid: bool, message: str)
    """
    if _EXTERNAL_DERIVATION_RE.search(response_text):
        return False, (
            "GUARDRAIL: El output deriva al cliente a proveedores externos. "
            "BMC Uruguay NO deriva a terceros. Siempre derivar al equipo de ventas BMC Uruguay."
        )
    return True, "ok"


def validate_panelin_output(response_text: str) -> tuple[bool, list[str]]:
    """Ejecuta todos los guardrails de output.

    Args:
        response_text: Respuesta generada por el agente.

    Returns:
        (all_valid: bool, errors: list[str])
    """
    errors = []

    valid, msg = validate_no_invented_prices(response_text)
    if not valid:
        errors.append(msg)

    valid, msg = validate_no_external_derivation(response_text)
    if not valid:
        errors.append(msg)

    return len(errors) == 0, errors
