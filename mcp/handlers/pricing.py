"""Handler for the price_check MCP tool.

Loads bromyros_pricing_master.json and provides lookup by SKU, family, type,
or free-text search. All prices are in USD with IVA 22% included.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

KB_ROOT = Path(__file__).resolve().parent.parent.parent
PRICING_FILE = KB_ROOT / "bromyros_pricing_master.json"

_pricing_data: dict[str, Any] | list[Any] | None = None


def _load_pricing() -> dict[str, Any] | list[Any]:
    global _pricing_data
    if _pricing_data is None:
        with open(PRICING_FILE, encoding="utf-8") as f:
            _pricing_data = json.load(f)
    return _pricing_data


def _normalize(text: str) -> str:
    return text.lower().strip().replace("-", "").replace("_", "").replace(" ", "")


def _search_products(data: dict[str, Any] | list[Any], query: str, filter_type: str = "search",
                     thickness_mm: float | None = None) -> list[dict[str, Any]]:
    """Search pricing data for matching products."""
    results: list[dict[str, Any]] = []
    norm_query = _normalize(query)

    # Navigate the pricing structure — adapt to actual JSON shape
    products = data if isinstance(data, list) else data.get("products", data.get("items", []))
    if isinstance(products, dict):
        # Handle dict-keyed structures
        items = []
        for key, value in products.items():
            if isinstance(value, dict):
                item = dict(value)
                item["_key"] = key
                items.append(item)
            elif isinstance(value, list):
                items.extend(value)
        products = items

    for product in products:
        if not isinstance(product, dict):
            continue

        match = False
        sku = str(product.get("sku", product.get("SKU", product.get("codigo", ""))))
        family = str(product.get("familia", product.get("family", product.get("_key", ""))))
        ptype = str(product.get("tipo", product.get("type", "")))
        name = str(product.get("nombre", product.get("name", product.get("title", ""))))
        thickness = product.get("espesor_mm", product.get("thickness", product.get("espesor")))

        if filter_type == "sku" and norm_query in _normalize(sku):
            match = True
        elif filter_type == "family" and norm_query in _normalize(family):
            match = True
        elif filter_type == "type" and norm_query in _normalize(ptype):
            match = True
        elif filter_type == "search":
            searchable = _normalize(f"{sku} {family} {ptype} {name}")
            if norm_query in searchable:
                match = True

        if match and thickness_mm is not None and thickness is not None:
            try:
                if float(thickness) != float(thickness_mm):
                    match = False
            except (ValueError, TypeError):
                # If thickness cannot be parsed as a float, ignore the thickness filter
                # and keep the existing match decision.
                pass

        if match:
            results.append(product)

    return results


async def handle_price_check(arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute price_check tool and return results in v1 contract format."""
    query = arguments.get("query", "")
    filter_type = arguments.get("filter_type", "search")
    thickness_mm = arguments.get("thickness_mm")

    if not query:
        return {
            "ok": False,
            "contract_version": "v1",
            "error": {
                "code": "INVALID_FILTER",
                "message": "Query parameter is required",
                "details": {}
            }
        }

    data = _load_pricing()
    results = _search_products(data, query, filter_type, thickness_mm)

    if not results:
        return {
            "ok": False,
            "contract_version": "v1",
            "error": {
                "code": "SKU_NOT_FOUND",
                "message": f"No products found for query '{query}' (filter: {filter_type})",
                "details": {"query": query, "filter_type": filter_type}
            }
        }

    # Transform results to match contract schema
    matches = []
    for item in results[:20]:  # Cap at 20 results
        matches.append({
            "sku": item.get("sku", ""),
            "description": item.get("descripcion", item.get("description", "")),
            "thickness_mm": item.get("espesor_mm", item.get("thickness_mm")),
            "price_usd_iva_inc": item.get("precio_usd_iva_inc", item.get("price_usd_iva_inc", 0))
        })

    return {
        "ok": True,
        "contract_version": "v1",
        "matches": matches
    }
