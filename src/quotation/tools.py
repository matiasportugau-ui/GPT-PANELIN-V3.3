"""
Panelin Agno — Agno Tool Wrappers
====================================

Envuelve las funciones del dominio como @tool para el agente Agno.
Cada tool es determinístico: el LLM llama la tool, el engine calcula.

REGLAS:
  - Precios SIEMPRE de la KB — nunca inventados
  - Si el precio no existe → error explícito, nunca inventar
  - Respuestas siempre en español
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def calcular_cotizacion(
    texto: str,
    modo: str = "pre_cotizacion",
    nombre_cliente: Optional[str] = None,
    telefono_cliente: Optional[str] = None,
    ubicacion_cliente: Optional[str] = None,
) -> str:
    """Calcula una cotización completa de paneles de construcción BMC Uruguay.

    Ejecuta el pipeline determinístico v4.0:
    clasificar → parsear → SRE → BOM → precios → validar

    Args:
        texto: Descripción libre del proyecto en español.
            Ejemplo: "Techo ISODEC 100mm, 10x8 metros, 2 aguas, estructura metálica"
        modo: Modo de operación — informativo | pre_cotizacion | formal.
            pre_cotizacion aplica supuestos cuando faltan datos.
            formal requiere todos los datos y bloquea si hay errores críticos.
        nombre_cliente: Nombre del cliente (opcional).
        telefono_cliente: Teléfono de contacto (opcional).
        ubicacion_cliente: Ubicación / departamento (opcional).

    Returns:
        Resumen de la cotización con precios en USD (IVA incluido).
        Los precios vienen exclusivamente de la KB de BMC Uruguay.
    """
    from src.quotation.service import QuotationRequest, get_quotation_service

    service = get_quotation_service()
    request = QuotationRequest(
        text=texto,
        mode=modo,
        client_name=nombre_cliente,
        client_phone=telefono_cliente,
        client_location=ubicacion_cliente,
    )
    result = service.calculate(request)
    return result.to_summary()


def calcular_cotizacion_detallada(
    texto: str,
    modo: str = "pre_cotizacion",
    nombre_cliente: Optional[str] = None,
    telefono_cliente: Optional[str] = None,
    ubicacion_cliente: Optional[str] = None,
) -> dict:
    """Cotización completa con BOM detallado, precios por ítem y validaciones.

    Igual que calcular_cotizacion pero retorna dict con todos los datos
    estructurados para procesamiento posterior o generación de PDF.

    Args:
        texto: Descripción libre del proyecto en español.
        modo: Modo de operación — informativo | pre_cotizacion | formal.
        nombre_cliente: Nombre del cliente (opcional).
        telefono_cliente: Teléfono de contacto (opcional).
        ubicacion_cliente: Ubicación / departamento (opcional).

    Returns:
        Dict con quote_id, BOM completo, precios por ítem, validaciones y SAI score.
    """
    from src.quotation.service import QuotationRequest, get_quotation_service

    service = get_quotation_service()
    request = QuotationRequest(
        text=texto,
        mode=modo,
        client_name=nombre_cliente,
        client_phone=telefono_cliente,
        client_location=ubicacion_cliente,
    )
    result = service.calculate(request)
    return result.to_dict()


def buscar_productos(consulta: str) -> str:
    """Busca productos en el catálogo de BMC Uruguay.

    Busca en el catálogo de paneles (ISODEC, ISOPANEL, ISOROOF, ISOWALL, ISOFRIG)
    y accesorios. Los precios son los reales de catálogo con IVA 22% incluido.

    Args:
        consulta: Término de búsqueda (ej: "ISODEC 100mm", "perfil U", "gotero").

    Returns:
        Lista de productos encontrados con SKU, nombre y precio.
        Máximo 20 resultados.
    """
    from src.quotation.service import get_quotation_service

    service = get_quotation_service()
    products = service.search_products(consulta)

    if not products:
        return f"No se encontraron productos para: {consulta}"

    lines = [f"Productos encontrados para '{consulta}':"]
    for p in products[:10]:
        sku = p.get("sku", p.get("SKU", "S/N"))
        name = p.get("nombre", p.get("name", p.get("tipo", "Sin nombre")))
        price = (
            p.get("precio_unit_iva_inc")
            or p.get("pricing", {}).get("sale_iva_inc")
            or p.get("pricing", {}).get("web_iva_inc")
            if isinstance(p.get("pricing"), dict)
            else None
        )
        price_str = f"USD {price:.2f} (IVA inc.)" if price else "Precio a consultar"
        lines.append(f"  • [{sku}] {name} — {price_str}")

    return "\n".join(lines)


def obtener_precios_paneles(
    familia: str,
    espesor_mm: Optional[int] = None,
) -> str:
    """Obtiene la lista de precios de paneles por familia y espesor.

    Los precios vienen EXCLUSIVAMENTE de bromyros_pricing_master.json.
    Nunca se inventan precios — si no existe en KB retorna error.

    Args:
        familia: Familia del panel — ISODEC | ISOPANEL | ISOROOF | ISOWALL | ISOFRIG.
        espesor_mm: Espesor en mm (ej: 50, 75, 100, 120, 150). Opcional.

    Returns:
        Lista de precios encontrados en USD/m² con IVA incluido.
    """
    from src.core.config import get_settings

    settings = get_settings()
    if not settings.pricing_master_path.exists():
        return "Error: archivo de precios no disponible"

    with open(settings.pricing_master_path, encoding="utf-8") as f:
        data = json.load(f)

    products = data if isinstance(data, list) else []
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                products.extend(v)

    familia_upper = familia.upper()
    lines = [f"Precios {familia_upper}{f' {espesor_mm}mm' if espesor_mm else ''}:"]
    found = 0

    for p in products:
        if not isinstance(p, dict):
            continue

        sku = str(p.get("sku", p.get("SKU", ""))).upper()
        name = str(p.get("nombre", p.get("name", ""))).upper()
        fam = str(p.get("familia", p.get("family", ""))).upper()

        if familia_upper not in sku and familia_upper not in name and familia_upper not in fam:
            continue

        thickness = p.get("espesor_mm", p.get("thickness"))
        if espesor_mm and thickness:
            try:
                if int(float(thickness)) != espesor_mm:
                    continue
            except (ValueError, TypeError):
                pass

        pricing = p.get("pricing", {})
        price = None
        if isinstance(pricing, dict):
            price = pricing.get("sale_iva_inc", pricing.get("web_iva_inc"))

        thickness_str = f"{int(float(thickness))}mm" if thickness else "?"
        price_str = f"USD {float(price):.2f}/m² (IVA inc.)" if price else "precio a consultar"
        lines.append(f"  • {name} {thickness_str} — {price_str}")
        found += 1
        if found >= 15:
            break

    if found == 0:
        return f"No se encontraron precios para {familia_upper} en la KB. Verificar catálogo."

    return "\n".join(lines)


def calcular_bom_manual(
    familia: str,
    sub_familia: str,
    espesor_mm: int,
    uso: str,
    largo_m: float,
    ancho_m: float,
    tipo_estructura: str = "metal",
    tipo_techo: Optional[str] = None,
) -> str:
    """Calcula el BOM (Lista de Materiales) directamente con parámetros explícitos.

    Útil cuando los datos ya están parseados y se quiere solo el BOM.
    No invoca LLM — es 100% determinístico.

    Args:
        familia: ISODEC | ISOPANEL | ISOROOF | ISOWALL | ISOFRIG.
        sub_familia: EPS | PIR | PUR | 3G.
        espesor_mm: Espesor en mm.
        uso: techo | pared | camara.
        largo_m: Largo del proyecto en metros.
        ancho_m: Ancho del proyecto en metros.
        tipo_estructura: metal | hormigon | madera.
        tipo_techo: 1_agua | 2_aguas | 4_aguas | mariposa (solo para techos).

    Returns:
        BOM con cantidades de paneles y accesorios.
    """
    from panelin_v4.engine.bom_engine import calculate_bom

    try:
        bom = calculate_bom(
            familia=familia,
            sub_familia=sub_familia,
            thickness_mm=espesor_mm,
            uso=uso,
            length_m=largo_m,
            width_m=ancho_m,
            structure_type=tipo_estructura,
            roof_type=tipo_techo,
        )
        lines = [
            f"BOM {familia} {sub_familia} {espesor_mm}mm — {uso}",
            f"Área: {bom.area_m2:.1f} m² | Paneles: {bom.panel_count} unid",
            "",
            "Materiales:",
        ]
        for item in bom.items:
            lines.append(f"  • {item.name or item.tipo}: {item.quantity} {item.unit}")
        if bom.warnings:
            lines.append("\nAdvertencias:")
            for w in bom.warnings:
                lines.append(f"  ⚠ {w}")
        return "\n".join(lines)
    except Exception as exc:
        return f"Error calculando BOM: {exc}"


def validar_solicitud_formal(texto: str) -> str:
    """Verifica si una solicitud tiene todos los datos para emitir cotización formal.

    Una cotización formal requiere: familia, espesor, uso, dimensiones completas,
    tipo de estructura, y datos del cliente. SRE score no debe ser CRITICAL.

    Args:
        texto: Descripción del proyecto a validar.

    Returns:
        Lista de campos faltantes y errores que impiden la emisión formal.
    """
    from panelin_v4.engine.parser import parse_request
    from panelin_v4.engine.classifier import classify_request, OperatingMode
    from panelin_v4.engine.sre_engine import calculate_sre

    req = parse_request(texto)
    classification = classify_request(texto)
    sre = calculate_sre(req)

    issues = []

    if not req.familia:
        issues.append("❌ Familia de panel no especificada (ISODEC, ISOPANEL, etc.)")
    if not req.thickness_mm:
        issues.append("❌ Espesor del panel no especificado (50mm, 100mm, etc.)")
    if not req.uso:
        issues.append("❌ Uso no especificado (techo, pared, cámara)")
    if not req.geometry.length_m:
        issues.append("❌ Largo del proyecto no especificado")
    if not req.geometry.width_m and not req.geometry.panel_count:
        issues.append("❌ Ancho del proyecto o número de paneles no especificado")
    if not req.structure_type:
        issues.append("⚠ Tipo de estructura no especificado (se asumirá metálica)")
    if not req.client.name:
        issues.append("⚠ Nombre del cliente no especificado")

    if sre.score > 70:
        issues.append(f"⚠ Riesgo estructural alto (SRE: {sre.score:.0f}/100) — requiere revisión técnica")

    if not issues:
        return "✅ Solicitud completa para cotización formal. Todos los datos requeridos están presentes."

    result = "Datos faltantes para cotización formal:\n"
    result += "\n".join(issues)
    result += "\n\nSolicite los datos faltantes al cliente antes de emitir."
    return result
