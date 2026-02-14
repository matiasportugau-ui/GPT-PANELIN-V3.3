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
    """Execute catalog_search tool and return lightweight results in v1 contract format."""
    query = arguments.get("query", "")
    category = arguments.get("category", "all")
    limit = arguments.get("limit", 5)

    # Validate query parameter
    if not query:
        return {
            "ok": False,
            "contract_version": "v1",
            "error": {
                "code": "QUERY_TOO_SHORT",
                "message": "Query parameter is required",
                "details": {"query": query}
            }
        }

    # Validate category
    valid_categories = ["techo", "pared", "camara", "accesorio", "all"]
    if category not in valid_categories:
        return {
            "ok": False,
            "contract_version": "v1",
            "error": {
                "code": "INVALID_CATEGORY",
                "message": f"Invalid category '{category}'",
                "details": {"category": category, "valid_categories": valid_categories}
            }
        }

    try:
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

            # Transform to contract format
            result_item = {
                "product_id": str(product.get("id", "")),
                "name": product.get("title", ""),
                "category": product.get("product_type", "")
            }
            
            # Add optional URL field if handle is available
            handle = product.get("handle", "")
            if handle:
                # TODO: Replace with actual shop URL or make configurable
                result_item["url"] = f"https://bmcuruguay.com/products/{handle}"
            
            # Calculate a simple relevance score based on match position
            # Lower position = higher score
            match_pos = searchable.find(norm_query)
            score = max(0.5, 1.0 - (match_pos / len(searchable))) if match_pos >= 0 else 0.5
            result_item["score"] = round(score, 2)
            
            results.append(result_item)
            if len(results) >= limit:
                break

        return {
            "ok": True,
            "contract_version": "v1",
            "results": results
        }

    except Exception as e:
        return {
            "ok": False,
            "contract_version": "v1",
            "error": {
                "code": "CATALOG_UNAVAILABLE",
                "message": f"Error searching catalog: {str(e)}",
                "details": {"exception_type": type(e).__name__}
            }
        }
