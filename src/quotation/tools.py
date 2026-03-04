"""
Panelin Agno — Agno Tool Wrappers
===================================

Expone las funcionalidades del motor panelin_v4 como herramientas (@tool)
para que el agente conversacional las invoque según sea necesario.

Estas herramientas son el "puente" entre el agente Agno y el motor determinístico.
El agente llama a las herramientas — el motor ejecuta la lógica de negocio.

Costo: $0.00 por tool call (Python puro, sin LLM)
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from agno.tools import tool

from src.quotation.service import get_quotation_service


@tool
def calcular_cotizacion_completa(
    texto: str,
    modo: Optional[str] = None,
    nombre_cliente: Optional[str] = None,
) -> str:
    """Calcula una cotización técnico-comercial completa para paneles de construcción BMC.

    Ejecuta el pipeline determinístico de 9 etapas: clasificación → parseo → SRE →
    BOM → pricing → validación → SAI. Retorna la cotización en JSON.

    IMPORTANTE: Todos los precios vienen EXCLUSIVAMENTE del catálogo KB de BMC.
    No se inventan precios. IVA 22% siempre incluido.

    Args:
        texto: Descripción en lenguaje natural de la solicitud de cotización.
               Ejemplo: "necesito cotizar techo ISOROOF 80mm para nave de 20x10m"
        modo: Modo de operación opcional: "informativo", "pre_cotizacion", "formal"
        nombre_cliente: Nombre del cliente para la cotización (opcional)

    Returns:
        JSON con cotización completa incluyendo BOM, precios, validaciones y SAI score
    """
    service = get_quotation_service()
    output = service.full_pipeline(
        text=texto,
        force_mode=modo,
        client_name=nombre_cliente,
    )
    result = service.output_to_dict(output)
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def verificar_precio_panel(
    familia: str,
    sub_familia: str,
    espesor_mm: int,
) -> str:
    """Consulta el precio por m² de un panel específico del catálogo BMC.

    Busca en bromyros_pricing_master.json. Si no se encuentra, retorna error
    explícito — NUNCA inventa precios.

    Args:
        familia: Familia del panel (ISOROOF, ISODEC, ISOPANEL, ISOWALL, ISOFRIG)
        sub_familia: Sub-familia (EPS, PIR, PUR, STONE_WOOL, etc.)
        espesor_mm: Espesor en milímetros (20-250)

    Returns:
        JSON con precio/m² IVA incluido o mensaje de error si no se encuentra
    """
    from panelin_v4.engine.pricing_engine import _find_panel_price_m2
    price = _find_panel_price_m2(familia, sub_familia, espesor_mm)
    if price is not None:
        return json.dumps({
            "encontrado": True,
            "familia": familia,
            "sub_familia": sub_familia,
            "espesor_mm": espesor_mm,
            "precio_m2_usd_iva_inc": price,
            "iva_incluido": True,
            "fuente": "bromyros_pricing_master.json",
        }, ensure_ascii=False)
    return json.dumps({
        "encontrado": False,
        "familia": familia,
        "sub_familia": sub_familia,
        "espesor_mm": espesor_mm,
        "mensaje": "Precio no encontrado en catálogo. Consultar vendedor para precio actualizado.",
    }, ensure_ascii=False)


@tool
def calcular_bom(
    familia: str,
    sub_familia: str,
    espesor_mm: int,
    uso: str,
    largo_m: float,
    ancho_m: float,
    tipo_estructura: str = "metal",
) -> str:
    """Calcula el Bill of Materials (BOM) para una instalación de paneles.

    Determina cantidades de paneles y todos los accesorios necesarios según
    los sistemas constructivos de BMC (bom_rules.json).

    Args:
        familia: Familia del panel (ISOROOF, ISODEC, ISOPANEL, ISOWALL, ISOFRIG)
        sub_familia: Sub-familia del panel (EPS, PIR, PUR, etc.)
        espesor_mm: Espesor del panel en mm
        uso: Tipo de uso ("techo", "cubierta", "pared", "camara_fria")
        largo_m: Largo del área a cubrir en metros
        ancho_m: Ancho del área a cubrir en metros
        tipo_estructura: Tipo de estructura de soporte ("metal", "madera", "hormigon")

    Returns:
        JSON con lista de materiales (paneles + accesorios) con cantidades
    """
    service = get_quotation_service()
    from panelin_v4.engine.bom_engine import calculate_bom as _calc_bom
    bom = _calc_bom(
        familia=familia,
        sub_familia=sub_familia,
        thickness_mm=espesor_mm,
        uso=uso,
        length_m=largo_m,
        width_m=ancho_m,
        structure_type=tipo_estructura,
    )
    return json.dumps(bom.to_dict(), ensure_ascii=False, indent=2)


@tool
def clasificar_solicitud(texto: str) -> str:
    """Clasifica el tipo y modo de una solicitud de cotización.

    Identifica el tipo (techo/pared/accesorio/update/etc.) y el modo
    (informativo/pre_cotizacion/formal) desde texto en español natural.

    Args:
        texto: Texto de la solicitud del usuario

    Returns:
        JSON con request_type, operating_mode y confianza de clasificación
    """
    from panelin_v4.engine.classifier import classify_request
    result = classify_request(texto)
    return json.dumps({
        "tipo": result.request_type.value if hasattr(result.request_type, "value") else str(result.request_type),
        "modo": result.operating_mode.value if hasattr(result.operating_mode, "value") else str(result.operating_mode),
        "confianza": getattr(result, "confidence", None),
    }, ensure_ascii=False)


@tool
def validar_vano_autoportancia(
    familia: str,
    sub_familia: str,
    espesor_mm: int,
    vano_m: float,
) -> str:
    """Valida si un vano es estructuralmente compatible con el panel seleccionado.

    Consulta los datos de autoportancia del catálogo técnico BMC.
    Retorna si el vano es válido y el máximo permitido.

    Args:
        familia: Familia del panel
        sub_familia: Sub-familia del panel
        espesor_mm: Espesor del panel en mm
        vano_m: Vano libre a verificar en metros

    Returns:
        JSON con validación: es_valido, vano_maximo_m, recomendaciones
    """
    from panelin_v4.engine.bom_engine import _get_autoportancia_m
    max_vano = _get_autoportancia_m(familia, sub_familia, espesor_mm)
    if max_vano is None:
        return json.dumps({
            "valido": None,
            "vano_solicitado_m": vano_m,
            "vano_maximo_m": None,
            "mensaje": "Datos de autoportancia no disponibles para esta combinación. Consultar especificaciones técnicas.",
        }, ensure_ascii=False)

    es_valido = vano_m <= max_vano
    return json.dumps({
        "valido": es_valido,
        "vano_solicitado_m": vano_m,
        "vano_maximo_m": max_vano,
        "familia": familia,
        "sub_familia": sub_familia,
        "espesor_mm": espesor_mm,
        "mensaje": (
            f"Vano {vano_m}m válido para {familia} {espesor_mm}mm (máx {max_vano}m)"
            if es_valido else
            f"⚠️ Vano {vano_m}m SUPERA autoportancia máxima de {max_vano}m para {familia} {espesor_mm}mm. "
            "Se requieren apoyos intermedios o panel de mayor espesor."
        ),
    }, ensure_ascii=False)


@tool
def buscar_accesorio(
    tipo: str,
    familia: Optional[str] = None,
    espesor_mm: Optional[int] = None,
) -> str:
    """Busca un accesorio en el catálogo BMC por tipo y compatibilidad.

    Args:
        tipo: Tipo de accesorio (gotero_frontal, babeta, cumbrera, perfil_u, silicona, etc.)
        familia: Familia de panel para filtrar compatibilidad (opcional)
        espesor_mm: Espesor de panel para compatibilidad específica (opcional)

    Returns:
        JSON con datos del accesorio: SKU, nombre, precio, compatibilidad
    """
    from panelin_v4.engine.bom_engine import _find_accessory
    acc = _find_accessory(tipo, familia or "", espesor_mm)
    if acc:
        return json.dumps({
            "encontrado": True,
            "tipo": tipo,
            "sku": acc.get("sku"),
            "nombre": acc.get("name"),
            "precio_unit_usd_iva_inc": acc.get("precio_unit_iva_inc"),
            "compatibilidad": acc.get("compatibilidad", []),
            "fuente": "accessories_catalog.json",
        }, ensure_ascii=False)
    return json.dumps({
        "encontrado": False,
        "tipo": tipo,
        "mensaje": f"Accesorio '{tipo}' no encontrado en catálogo para familia={familia}, espesor={espesor_mm}mm",
    }, ensure_ascii=False)
