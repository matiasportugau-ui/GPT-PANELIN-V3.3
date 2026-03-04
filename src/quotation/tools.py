"""
src/quotation/tools.py — Agno @tool wrappers para el engine de cotización.

Estas funciones son las tools que el agente Panelin puede llamar directamente.
Cada función es pura y determinística — sin LLM, sin I/O externo.

Expuestas al agente como tools de dominio para:
  - Calcular cotizaciones
  - Validar datos técnicos
  - Consultar catálogo de productos
  - Verificar precios del KB
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from panelin_v4.engine.bom_engine import calculate_bom
from panelin_v4.engine.classifier import classify_request
from panelin_v4.engine.parser import parse_request
from panelin_v4.engine.pricing_engine import calculate_pricing, _find_panel_price_m2
from panelin_v4.engine.sre_engine import calculate_sre
from panelin_v4.engine.validation_engine import validate_quotation
from src.quotation.service import QuotationRequest, quotation_service
from src.core.config import settings

logger = logging.getLogger(__name__)

KB_ROOT = Path(__file__).resolve().parent.parent.parent


def calcular_cotizacion(
    texto: str,
    modo: str = "pre_cotizacion",
    nombre_cliente: Optional[str] = None,
    telefono_cliente: Optional[str] = None,
    ubicacion_cliente: Optional[str] = None,
) -> str:
    """Procesa una solicitud de cotización de paneles de construcción BMC Uruguay.

    Ejecuta el pipeline completo: clasificación → parsing → SRE → BOM → precios → validación.
    Los precios vienen EXCLUSIVAMENTE de la base de conocimiento (NUNCA se inventan).
    Latencia < 0.5ms, sin llamadas LLM.

    Args:
        texto: Descripción libre del proyecto en español.
        modo: 'informativo', 'pre_cotizacion' (default), o 'formal'.
        nombre_cliente: Nombre del cliente (opcional para pre-cotización).
        telefono_cliente: Teléfono del cliente (opcional).
        ubicacion_cliente: Ubicación/dirección de la obra (opcional).

    Returns:
        JSON con resultado completo de la cotización incluyendo BOM, precios y SAI score.
    """
    request = QuotationRequest(
        text=texto,
        mode=modo,
        client_name=nombre_cliente,
        client_phone=telefono_cliente,
        client_location=ubicacion_cliente,
    )
    result = quotation_service.run(request)
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)


def verificar_precio_panel(
    familia: str,
    sub_familia: str,
    espesor_mm: int,
) -> str:
    """Verifica el precio por m² de un panel directamente desde la KB.

    Fuente: bromyros_pricing_master.json (NUNCA inventa precios).

    Args:
        familia: Familia del panel: ISODEC, ISOROOF, ISOPANEL, ISOWALL, ISOFRIG.
        sub_familia: Sub-familia: EPS, PIR, 3G.
        espesor_mm: Espesor en mm (ej: 80, 100, 120, 150).

    Returns:
        JSON con precio USD/m² IVA incluido, o error si no existe en KB.
    """
    precio = _find_panel_price_m2(familia, sub_familia, espesor_mm)
    if precio is None:
        return json.dumps({
            "encontrado": False,
            "producto": f"{familia} {sub_familia} {espesor_mm}mm",
            "mensaje": (
                f"No hay precio en KB para {familia} {sub_familia} {espesor_mm}mm. "
                "Consultar con ventas BMC Uruguay."
            ),
        }, ensure_ascii=False)
    return json.dumps({
        "encontrado": True,
        "producto": f"{familia} {sub_familia} {espesor_mm}mm",
        "precio_m2_usd": precio,
        "iva_incluido": True,
        "iva_rate": 0.22,
        "fuente": "bromyros_pricing_master.json",
    }, ensure_ascii=False)


def validar_autoportancia(
    familia: str,
    sub_familia: str,
    espesor_mm: int,
    luz_m: float,
) -> str:
    """Valida si un panel soporta la luz libre (vano) solicitada.

    Consulta las tablas de autoportancia de BOM rules. No inventa valores.

    Args:
        familia: Familia del panel.
        sub_familia: Sub-familia.
        espesor_mm: Espesor en mm.
        luz_m: Luz libre a cubrir en metros.

    Returns:
        JSON con estado (ok/warning/blocked), márgenes de seguridad y alternativas.
    """
    with open(KB_ROOT / "bom_rules.json", encoding="utf-8") as f:
        rules = json.load(f)

    tables = rules.get("autoportancia", {}).get("tablas", {})
    key = f"{familia}_{sub_familia}".upper()
    if familia.upper() == "ISOROOF":
        key = "ISOROOF_3G"

    entry = tables.get(key, {}).get(str(espesor_mm))
    if not entry:
        # Try searching all thicknesses for available options
        available = list(tables.get(key, {}).keys())
        return json.dumps({
            "valido": False,
            "estado": "sin_datos",
            "producto": f"{familia} {sub_familia} {espesor_mm}mm",
            "espesores_disponibles": available,
            "mensaje": (
                f"No hay datos de autoportancia para {familia} {sub_familia} {espesor_mm}mm. "
                f"Espesores disponibles: {available}"
            ),
        }, ensure_ascii=False)

    luz_max = entry["luz_max_m"]
    luz_segura = round(luz_max * 0.85, 2)

    if luz_m <= luz_segura:
        estado = "ok"
    elif luz_m <= luz_max:
        estado = "warning"
    else:
        estado = "blocked"

    # Find valid alternatives if blocked/warning
    alternativas = []
    for thick_str, data in tables.get(key, {}).items():
        if data.get("luz_max_m", 0) >= luz_m:
            alternativas.append({
                "espesor_mm": int(thick_str),
                "luz_max_m": data["luz_max_m"],
                "luz_segura_m": round(data["luz_max_m"] * 0.85, 2),
                "peso_kg_m2": data.get("peso_kg_m2"),
            })
    alternativas.sort(key=lambda x: x["espesor_mm"])

    return json.dumps({
        "valido": estado != "blocked",
        "estado": estado,
        "producto": f"{familia} {sub_familia} {espesor_mm}mm",
        "luz_solicitada_m": luz_m,
        "luz_maxima_m": luz_max,
        "luz_segura_m": luz_segura,
        "peso_kg_m2": entry.get("peso_kg_m2"),
        "margen_pct": round((1 - luz_m / luz_max) * 100, 1) if luz_max > 0 else 0,
        "alternativas_validas": alternativas,
        "recomendacion": (
            f"La luz de {luz_m}m está dentro del rango seguro ({luz_segura}m)."
            if estado == "ok" else
            f"La luz de {luz_m}m está entre el límite seguro ({luz_segura}m) y el máximo ({luz_max}m)."
            if estado == "warning" else
            f"La luz de {luz_m}m excede el máximo para {familia} {espesor_mm}mm ({luz_max}m). "
            f"Usar espesor mayor o apoyo intermedio."
        ),
    }, ensure_ascii=False)


def buscar_accesorios(
    tipo: Optional[str] = None,
    familia: Optional[str] = None,
) -> str:
    """Busca accesorios disponibles en el catálogo BMC Uruguay.

    Fuente: accessories_catalog.json (precios reales, IVA incluido).

    Args:
        tipo: Tipo de accesorio (ej: 'gotero_frontal', 'silicona', 'varilla').
        familia: Familia de panel compatible (ej: 'ISODEC', 'ISOROOF').

    Returns:
        JSON con lista de accesorios con SKU, nombre y precio.
    """
    with open(KB_ROOT / "accessories_catalog.json", encoding="utf-8") as f:
        catalog = json.load(f)

    accesorios = catalog.get("accesorios", [])

    if tipo:
        accesorios = [a for a in accesorios if a.get("tipo") == tipo]
    if familia:
        familia_upper = familia.upper()
        accesorios = [
            a for a in accesorios
            if familia_upper in [c.upper() for c in a.get("compatibilidad", [])]
            or "UNIVERSAL" in [c.upper() for c in a.get("compatibilidad", [])]
        ]

    resultado = [
        {
            "sku": a.get("sku"),
            "tipo": a.get("tipo"),
            "nombre": a.get("name"),
            "precio_unit_usd": a.get("precio_unit_iva_inc"),
            "unidad": a.get("unidad", "unid"),
            "compatibilidad": a.get("compatibilidad", []),
            "iva_incluido": True,
        }
        for a in accesorios
    ]

    return json.dumps({
        "total": len(resultado),
        "accesorios": resultado,
        "fuente": "accessories_catalog.json",
    }, ensure_ascii=False)


def clasificar_solicitud(texto: str) -> str:
    """Clasifica el tipo y modo de una solicitud de cotización.

    Identifica: tipo (roof/wall/room/accessories/update), modo (informativo/pre/formal),
    y si es urgente o requiere datos adicionales.

    Args:
        texto: Texto libre del cliente en español.

    Returns:
        JSON con clasificación completa.
    """
    classification = classify_request(texto)
    return json.dumps(classification.to_dict(), ensure_ascii=False)


def reglas_negocio() -> str:
    """Retorna las reglas de negocio y políticas comerciales de BMC Uruguay.

    Incluye: IVA 22%, política de derivación, moneda USD, flete, etc.

    Returns:
        JSON con reglas de negocio actuales.
    """
    return json.dumps({
        "iva_rate": 0.22,
        "iva_incluido_en_precios": True,
        "moneda": "USD",
        "pendiente_minimo_techo_pct": 7,
        "flete_defecto_usd": 280.0,
        "politica_derivacion": (
            "NUNCA derivar a proveedor externo. "
            "SIEMPRE derivar a agentes de ventas BMC Uruguay: +598 2xxx xxxx"
        ),
        "alcance_servicio": "materiales_y_asesoramiento",
        "sitio_oficial": "https://bmcuruguay.com.uy",
        "formato_telefono": "09XXXXXXX (9 dígitos) o +598XXXXXXXX",
        "datos_requeridos_cotizacion_formal": [
            "nombre_cliente",
            "telefono_cliente",
            "direccion_obra",
        ],
        "sistemas_disponibles": [
            "ISODEC EPS/PIR — techos planos y curvas",
            "ISOROOF 3G — techos industriales",
            "ISOPANEL EPS — paredes livianas",
            "ISOWALL PIR — paredes de alta performance",
            "ISOFRIG PIR — cámaras frigoríficas",
        ],
    }, ensure_ascii=False)


# Lista de todas las tools de dominio para registrar en el agente
PANELIN_DOMAIN_TOOLS = [
    calcular_cotizacion,
    verificar_precio_panel,
    validar_autoportancia,
    buscar_accesorios,
    clasificar_solicitud,
    reglas_negocio,
]
