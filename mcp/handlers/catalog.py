"""Handler for the catalog_search MCP tool.

Searches shopify_catalog_v1.json for products by name, category, or keyword.
Returns lightweight results (id, title, handle, type, vendor, tags).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

KB_ROOT = Path(__file__).resolve().parent.parent.parent
CATALOG_FILE = KB_ROOT / "shopify_catalog_v1.json"

_catalog_data: list[dict[str, Any]] | None = None


def _load_catalog() -> list[dict[str, Any]]:
    global _catalog_data
    if _catalog_data is None:
        with open(CATALOG_FILE, encoding="utf-8") as f:
            raw = json.load(f)
        _catalog_data = raw if isinstance(raw, list) else raw.get("products", [])
    return _catalog_data


def _normalize(text: str) -> str:
    return text.lower().strip()


def _to_lightweight(product: dict[str, Any]) -> dict[str, Any]:
    """Extract only the fields needed for search results."""
    return {
        "id": product.get("id"),
        "title": product.get("title", ""),
        "handle": product.get("handle", ""),
        "product_type": product.get("product_type", ""),
        "vendor": product.get("vendor", ""),
        "tags": product.get("tags", ""),
        "status": product.get("status", ""),
    }


CATEGORY_MAP = {
    "techo": ["techo", "roof", "isoroof", "isodec", "cubierta"],
    "pared": ["pared", "wall", "isowall", "isopanel"],
    "camara": ["camara", "frio", "isofrig", "frigorifico"],
    "accesorio": ["accesorio", "accessory", "fijacion", "tornillo", "cumbrera", "babeta"],
}


async def handle_catalog_search(arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute catalog_search tool and return lightweight results."""
    query = arguments.get("query", "")
    category = arguments.get("category", "all")
    limit = arguments.get("limit", 5)

    if not query:
        return {"error": "Query parameter is required", "results": []}

    catalog = _load_catalog()
    norm_query = _normalize(query)

    # Determine category keywords
    category_keywords: list[str] = []
    if category != "all" and category in CATEGORY_MAP:
        category_keywords = CATEGORY_MAP[category]

    results: list[dict[str, Any]] = []
    for product in catalog:
        title = _normalize(product.get("title", ""))
        ptype = _normalize(product.get("product_type", ""))
        tags = _normalize(str(product.get("tags", "")))
        handle = _normalize(product.get("handle", ""))
        searchable = f"{title} {ptype} {tags} {handle}"

        if norm_query not in searchable:
            continue

        if category_keywords:
            if not any(kw in searchable for kw in category_keywords):
                continue

        results.append(_to_lightweight(product))
        if len(results) >= limit:
            break

    return {
        "message": f"Found {len(results)} product(s) for '{query}'",
        "results": results,
        "source": "shopify_catalog_v1.json (Level 1.6)",
        "total_catalog_size": len(catalog),
    }
