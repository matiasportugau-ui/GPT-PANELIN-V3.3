"""
Panelin v5.0 — Agno Tool Wrappers
====================================

Wraps domain functions as Agno-compatible tools that can be attached
to agents. Each tool is a plain Python function decorated for Agno.
"""

from __future__ import annotations

import json
from typing import Optional

from src.quotation.service import QuotationService


def quote_from_text(
    text: str,
    mode: str = "pre_cotizacion",
    client_name: Optional[str] = None,
    client_phone: Optional[str] = None,
    client_location: Optional[str] = None,
) -> str:
    """Genera una cotización completa a partir de texto libre en español.

    Args:
        text: Descripción del proyecto en texto libre (ej: "Necesito 6 paneles ISODEC 100mm para techo de 10x7m")
        mode: Modo de operación: 'informativo', 'pre_cotizacion', o 'formal'
        client_name: Nombre del cliente (opcional)
        client_phone: Teléfono del cliente (opcional)
        client_location: Ubicación del proyecto (opcional)

    Returns:
        JSON con la cotización completa incluyendo BOM, precios y validación.
    """
    from panelin_v4.engine.classifier import OperatingMode

    mode_map = {
        "informativo": OperatingMode.INFORMATIVO,
        "pre_cotizacion": OperatingMode.PRE_COTIZACION,
        "formal": OperatingMode.FORMAL,
    }
    force_mode = mode_map.get(mode.lower(), OperatingMode.PRE_COTIZACION)

    output = QuotationService.process_full(
        text=text,
        force_mode=force_mode,
        client_name=client_name,
        client_phone=client_phone,
        client_location=client_location,
    )
    return output.to_json()


def validate_quotation_request(
    text: str,
    mode: str = "pre_cotizacion",
) -> str:
    """Valida una solicitud de cotización sin generar precios.

    Retorna clasificación, parsing, riesgo estructural y validación.

    Args:
        text: Descripción del proyecto en texto libre
        mode: Modo de operación: 'informativo', 'pre_cotizacion', o 'formal'

    Returns:
        JSON con clasificación, request parseado, SRE y validación.
    """
    from panelin_v4.engine.classifier import OperatingMode

    mode_map = {
        "informativo": OperatingMode.INFORMATIVO,
        "pre_cotizacion": OperatingMode.PRE_COTIZACION,
        "formal": OperatingMode.FORMAL,
    }
    force_mode = mode_map.get(mode.lower(), OperatingMode.PRE_COTIZACION)

    svc = QuotationService
    classification = svc.classify(text, force_mode=force_mode)
    request = svc.parse(text)
    assumptions = svc.apply_defaults(request, classification.operating_mode)
    request.assumptions_used.extend(assumptions)
    sre = svc.calculate_sre(request)
    bom = svc.calculate_bom(request)
    pricing = svc.calculate_pricing(bom, request)
    validation = svc.validate(request, sre, bom, pricing, classification.operating_mode)

    return json.dumps({
        "classification": classification.to_dict(),
        "request": request.to_dict(),
        "sre": sre.to_dict(),
        "validation": validation.to_dict(),
    }, ensure_ascii=False, indent=2)


def check_product_price(
    familia: str,
    sub_familia: str = "EPS",
    thickness_mm: int = 100,
) -> str:
    """Consulta el precio de un panel desde la base de conocimiento.

    Los precios incluyen IVA 22%. NUNCA se inventan precios.

    Args:
        familia: Familia del producto (ISODEC, ISOROOF, ISOPANEL, ISOWALL, ISOFRIG)
        sub_familia: Sub-familia (EPS, PIR, 3G)
        thickness_mm: Espesor en milímetros

    Returns:
        JSON con precio por m² o mensaje de que no se encontró.
    """
    from panelin_v4.engine.pricing_engine import _find_panel_price_m2

    price = _find_panel_price_m2(familia, sub_familia, thickness_mm)
    if price is not None:
        return json.dumps({
            "found": True,
            "familia": familia,
            "sub_familia": sub_familia,
            "thickness_mm": thickness_mm,
            "price_usd_m2": price,
            "iva_included": True,
            "source": "bromyros_pricing_master",
        }, ensure_ascii=False)
    return json.dumps({
        "found": False,
        "familia": familia,
        "sub_familia": sub_familia,
        "thickness_mm": thickness_mm,
        "message": f"Precio no encontrado para {familia} {sub_familia} {thickness_mm}mm en la base de conocimiento.",
    }, ensure_ascii=False)


def search_accessories(
    tipo: str,
    familia: Optional[str] = None,
    thickness_mm: Optional[int] = None,
) -> str:
    """Busca accesorios compatibles en el catálogo.

    Args:
        tipo: Tipo de accesorio (gotero_frontal, cumbrera, perfil_u, varilla, etc.)
        familia: Familia del panel para compatibilidad (opcional)
        thickness_mm: Espesor del panel para compatibilidad (opcional)

    Returns:
        JSON con el accesorio encontrado y su precio.
    """
    from panelin_v4.engine.bom_engine import _find_accessory

    acc = _find_accessory(tipo, familia or "UNIVERSAL", thickness_mm)
    if acc:
        return json.dumps({
            "found": True,
            "tipo": tipo,
            "sku": acc.get("sku"),
            "name": acc.get("name"),
            "precio_unit_iva_inc": acc.get("precio_unit_iva_inc"),
            "compatibilidad": acc.get("compatibilidad", []),
        }, ensure_ascii=False)
    return json.dumps({
        "found": False,
        "tipo": tipo,
        "message": f"No se encontró accesorio tipo '{tipo}' en el catálogo.",
    }, ensure_ascii=False)


def calculate_sai_score(
    text: str,
    mode: str = "pre_cotizacion",
) -> str:
    """Calcula el System Accuracy Index (SAI) de una cotización.

    El SAI mide la calidad de la cotización en una escala de 0-100.

    Args:
        text: Descripción del proyecto en texto libre
        mode: Modo de operación

    Returns:
        JSON con score SAI, grado (A-F), y detalle de penalidades/bonuses.
    """
    from panelin_v4.engine.classifier import OperatingMode

    mode_map = {
        "informativo": OperatingMode.INFORMATIVO,
        "pre_cotizacion": OperatingMode.PRE_COTIZACION,
        "formal": OperatingMode.FORMAL,
    }
    force_mode = mode_map.get(mode.lower(), OperatingMode.PRE_COTIZACION)

    output = QuotationService.process_full(text=text, force_mode=force_mode)
    sai = QuotationService.calculate_sai(output)
    return json.dumps({
        "quote_id": output.quote_id,
        "mode": output.mode,
        "status": output.status,
        "sai": sai.to_dict(),
    }, ensure_ascii=False, indent=2)


PANELIN_TOOLS = [
    quote_from_text,
    validate_quotation_request,
    check_product_price,
    search_accessories,
    calculate_sai_score,
]
