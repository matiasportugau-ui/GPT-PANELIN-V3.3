"""Agno tool wrappers for Panelin quotation domain functions.

These tools are registered on the Panelin conversational agent.
Each tool calls the QuotationService which wraps the v4 engine.

Pricing rule: NUNCA se inventan precios. Solo se usan datos del KB.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy singleton service — initialized once on first use
_service: Optional[object] = None


def _get_service():
    global _service
    if _service is None:
        from src.quotation.service import QuotationService
        _service = QuotationService()
    return _service


def cotizar_panel(
    texto: str,
    modo: Optional[str] = None,
) -> str:
    """Genera una cotización completa de paneles BMC a partir de texto libre en español.

    Ejecuta el pipeline completo v4: clasificación → parseo → SRE → BOM → precios →
    validación → SAI. Los precios vienen exclusivamente de la base de conocimiento.

    Args:
        texto: Descripción del proyecto en español. Ejemplo: 'Necesito techo ISODEC
               EPS 100mm para una nave de 20x12m con estructura metálica'
        modo: Modo de cotización opcional ('informativo', 'pre_cotizacion', 'formal').
              Si se omite, se detecta automáticamente.

    Returns:
        JSON string con el resultado completo del pipeline incluyendo BOM, precios y
        validación.
    """
    try:
        svc = _get_service()
        result = svc.process(texto, mode=modo)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as exc:
        logger.error("cotizar_panel error: %s", exc)
        return json.dumps({"error": str(exc), "ok": False})


def calcular_bom(
    familia: str,
    sub_familia: str,
    espesor_mm: int,
    largo_m: float,
    ancho_m: float,
    uso: str = "techo",
    tipo_estructura: str = "metal",
) -> str:
    """Calcula el Bill of Materials (lista de materiales) para un proyecto.

    Retorna la lista de paneles, accesorios, fijaciones y sellantes necesarios
    con sus cantidades exactas calculadas por el motor determinístico.

    Args:
        familia: Familia de panel: ISODEC, ISOROOF, ISOPANEL, ISOWALL, ISOFRIG
        sub_familia: Sub-familia: EPS, PIR, 3G
        espesor_mm: Espesor del panel en mm (ej: 80, 100, 120, 150)
        largo_m: Largo/longitud del área en metros
        ancho_m: Ancho del área en metros
        uso: 'techo' o 'pared'
        tipo_estructura: 'metal' u 'hormigon'

    Returns:
        JSON string con el BOM completo: items, área, conteos y advertencias.
    """
    try:
        svc = _get_service()
        parsed = {
            "familia": familia,
            "sub_familia": sub_familia,
            "thickness_mm": espesor_mm,
            "length_m": largo_m,
            "width_m": ancho_m,
            "uso": uso,
            "structure_type": tipo_estructura,
        }
        result = svc.bom(parsed)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as exc:
        logger.error("calcular_bom error: %s", exc)
        return json.dumps({"error": str(exc), "ok": False})


def verificar_autoportancia(
    familia: str,
    sub_familia: str,
    espesor_mm: int,
    luz_m: float,
) -> str:
    """Verifica si un panel puede soportar una determinada luz (distancia entre apoyos).

    Consulta las tablas de autoportancia de la base de conocimiento para verificar
    si el espesor elegido es estructuralmente adecuado para la luz solicitada.

    Args:
        familia: Familia de panel: ISODEC, ISOROOF, ISOPANEL
        sub_familia: Sub-familia: EPS, PIR, 3G
        espesor_mm: Espesor en mm
        luz_m: Distancia entre apoyos en metros (luz libre)

    Returns:
        JSON string con estado (ok/warning/bloqueado), margen de seguridad y
        alternativas si aplica.
    """
    try:
        from panelin_v4.engine.sre_engine import calculate_sre
        from panelin_v4.engine.parser import QuoteRequest

        req = QuoteRequest(
            familia=familia,
            sub_familia=sub_familia,
            thickness_mm=espesor_mm,
            span_m=luz_m,
            uso="techo",
        )
        result = calculate_sre(req)
        d = _sre_to_dict(result)
        return json.dumps(d, ensure_ascii=False, default=str)
    except Exception as exc:
        logger.error("verificar_autoportancia error: %s", exc)
        return json.dumps({"error": str(exc), "ok": False})


def consultar_precio(
    familia: str,
    sub_familia: str,
    espesor_mm: int,
) -> str:
    """Consulta el precio por m² de un panel desde la base de conocimiento de precios.

    IMPORTANTE: Los precios vienen EXCLUSIVAMENTE de la base de conocimiento (KB).
    Nunca se inventan ni se estiman precios.

    Args:
        familia: Familia de panel: ISODEC, ISOROOF, ISOPANEL, ISOWALL, ISOFRIG
        sub_familia: Sub-familia: EPS, PIR, 3G
        espesor_mm: Espesor en mm

    Returns:
        JSON string con precio por m² (IVA 22% incluido) o null si no disponible.
    """
    try:
        from panelin_v4.engine.pricing_engine import _find_panel_price_m2
        price = _find_panel_price_m2(familia, sub_familia, espesor_mm)
        if price is None:
            return json.dumps({
                "precio_m2_usd": None,
                "iva_incluido": True,
                "mensaje": f"Precio no disponible para {familia} {sub_familia} {espesor_mm}mm. "
                           "Consulte con el equipo de ventas BMC Uruguay.",
            }, ensure_ascii=False)
        return json.dumps({
            "precio_m2_usd": price,
            "iva_incluido": True,
            "familia": familia,
            "sub_familia": sub_familia,
            "espesor_mm": espesor_mm,
        }, ensure_ascii=False)
    except Exception as exc:
        logger.error("consultar_precio error: %s", exc)
        return json.dumps({"error": str(exc), "ok": False})


def procesar_lote(textos: list[str]) -> str:
    """Procesa múltiples cotizaciones en lote.

    Args:
        textos: Lista de descripciones de proyectos en español

    Returns:
        JSON string con array de resultados y estadísticas del lote.
    """
    try:
        svc = _get_service()
        results = svc.batch(textos)
        return json.dumps({
            "ok": True,
            "total": len(results),
            "cotizaciones": results,
        }, ensure_ascii=False, default=str)
    except Exception as exc:
        logger.error("procesar_lote error: %s", exc)
        return json.dumps({"error": str(exc), "ok": False})


def _sre_to_dict(result) -> dict:
    """Convert SRE result to dict."""
    if hasattr(result, "__dict__"):
        d = {}
        for k, v in result.__dict__.items():
            if not k.startswith("_"):
                d[k] = v.value if hasattr(v, "value") else v
        return d
    return {}
