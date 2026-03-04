"""
Panelin Agno — Tool wrappers for the quotation engine.

These functions are registered as Agno tools so the agent can
invoke them during conversation. Each tool has a docstring that
the LLM uses as its description.
"""

from __future__ import annotations

import json
from typing import Optional

from src.quotation.service import QuotationService


def generate_quotation(
    text: str,
    force_mode: Optional[str] = None,
    client_name: Optional[str] = None,
    client_phone: Optional[str] = None,
    client_location: Optional[str] = None,
) -> str:
    """Genera una cotización completa para paneles BMC Uruguay.

    Procesa el texto del usuario a través del pipeline determinístico v4:
    clasificación → parsing → riesgo estructural → BOM → pricing → validación.

    Args:
        text: Descripción del proyecto en español (ej: "10 paneles ISODEC 100mm para techo de 8x12m").
        force_mode: Modo forzado (informativo | pre_cotizacion | formal). Si no se especifica, se auto-detecta.
        client_name: Nombre del cliente (opcional).
        client_phone: Teléfono del cliente (opcional, formato 09XXXXXXX).
        client_location: Ubicación de la obra (opcional).

    Returns:
        JSON con la cotización completa incluyendo BOM, precios y validación.
    """
    result = QuotationService.full_pipeline(
        text=text,
        force_mode=force_mode,
        client_name=client_name,
        client_phone=client_phone,
        client_location=client_location,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


def generate_batch_quotation(
    requests_json: str,
    force_mode: Optional[str] = None,
) -> str:
    """Genera múltiples cotizaciones en lote.

    Args:
        requests_json: JSON array con objetos que contienen al menos 'text'.
            Ejemplo: [{"text": "ISODEC 100mm 10x12m techo"}, {"text": "ISOPANEL 50mm pared 8x3m"}]
        force_mode: Modo forzado para todas las cotizaciones.

    Returns:
        JSON array con las cotizaciones completas.
    """
    requests = json.loads(requests_json)
    results = QuotationService.batch_pipeline(requests, force_mode=force_mode)
    return json.dumps(results, ensure_ascii=False, indent=2)


def classify_request(text: str) -> str:
    """Clasifica una solicitud de cotización sin procesarla completa.

    Determina el tipo de solicitud (techo, pared, accesorios, etc.)
    y el modo operativo (informativo, pre_cotizacion, formal).

    Args:
        text: Texto de la solicitud en español.

    Returns:
        JSON con tipo de solicitud, modo operativo y señales de detección.
    """
    result = QuotationService.classify(text)
    return json.dumps(result, ensure_ascii=False, indent=2)


def search_product_catalog(
    familia: Optional[str] = None,
    thickness_mm: Optional[int] = None,
    uso: Optional[str] = None,
) -> str:
    """Busca productos disponibles en el catálogo BMC Uruguay.

    Args:
        familia: Familia de producto (ISODEC, ISOROOF, ISOPANEL, ISOWALL, ISOFRIG).
        thickness_mm: Espesor en milímetros (30, 50, 80, 100, 150, 200).
        uso: Uso previsto (techo, pared, camara).

    Returns:
        JSON con productos encontrados y sus especificaciones.
    """
    import os
    from pathlib import Path

    kb_root = Path(os.environ.get("KB_ROOT", "."))
    pricing_path = kb_root / os.environ.get("KB_PRICING_MASTER", "bromyros_pricing_master.json")

    try:
        with open(pricing_path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return json.dumps({"error": "Catálogo de precios no encontrado"})

    if isinstance(data, dict) and "data" in data:
        data = data["data"]
    products = data.get("products", data.get("items", []))
    if isinstance(products, dict):
        items = []
        for k, v in products.items():
            if isinstance(v, dict):
                v["_key"] = k
                items.append(v)
        products = items

    results = []
    for p in products:
        if not isinstance(p, dict):
            continue
        p_fam = str(p.get("familia", p.get("family", ""))).upper()
        p_thick = p.get("espesor_mm", p.get("thickness"))
        p_uso = str(p.get("uso", p.get("application", ""))).lower()

        if familia and familia.upper() not in p_fam:
            continue
        if thickness_mm and p_thick is not None:
            try:
                if int(float(p_thick)) != thickness_mm:
                    continue
            except (ValueError, TypeError):
                continue
        if uso and uso.lower() not in p_uso:
            continue

        results.append({
            "sku": p.get("sku", p.get("SKU", "")),
            "nombre": p.get("nombre", p.get("name", "")),
            "familia": p_fam,
            "espesor_mm": p_thick,
            "pricing": p.get("pricing", {}),
        })

    return json.dumps({"total": len(results), "productos": results[:20]}, ensure_ascii=False, indent=2)


def get_accessory_catalog() -> str:
    """Devuelve el catálogo completo de accesorios BMC con precios.

    Incluye goteros, babetas, cumbreras, fijaciones, selladores, etc.
    Todos los precios incluyen IVA 22%.

    Returns:
        JSON con lista de accesorios disponibles.
    """
    import os
    from pathlib import Path

    kb_root = Path(os.environ.get("KB_ROOT", "."))
    acc_path = kb_root / os.environ.get("KB_ACCESSORIES", "accessories_catalog.json")

    try:
        with open(acc_path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return json.dumps({"error": "Catálogo de accesorios no encontrado"})

    accesorios = data.get("accesorios", [])
    summary = [
        {
            "sku": a.get("sku"),
            "nombre": a.get("name"),
            "tipo": a.get("tipo"),
            "precio_usd_iva_inc": a.get("precio_unit_iva_inc"),
            "compatibilidad": a.get("compatibilidad", []),
        }
        for a in accesorios
    ]
    return json.dumps({"total": len(summary), "accesorios": summary}, ensure_ascii=False, indent=2)
