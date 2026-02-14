"""Handler for the catalog_search MCP tool.

Searches shopify_catalog_v1.json for products by name, category, or keyword.
Returns lightweight results (id, title, handle, type, vendor, tags).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

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
    """Execute catalog_search tool and return v1 contract envelope."""
    query = arguments.get("query", "")
    category = arguments.get("category", "all")
    limit = arguments.get("limit", 5)

    # Validate query parameter (contract requires minLength=2, strip whitespace)
    query_stripped = query.strip() if isinstance(query, str) else ""
    if len(query_stripped) < 2:
        return {
            "ok": False,
            "contract_version": "v1",
            "error": {
                "code": "QUERY_TOO_SHORT",
                "message": "Query parameter must be at least 2 characters long",
                "details": {"query": query}
            }
        }
    
    # Use the stripped query for processing
    query = query_stripped

    # Validate and normalize limit parameter (v1 contract: integer 1..30)
    try:
        limit_int = int(limit)
    except (TypeError, ValueError):
        # Use INTERNAL_ERROR since contract doesn't define INVALID_LIMIT
        return {
            "ok": False,
            "contract_version": "v1",
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Invalid 'limit' parameter. It must be an integer between 1 and 30.",
                "details": {"limit": limit},
            },
        }

    # Clamp to valid range
    if limit_int < 1:
        limit_int = 1
    elif limit_int > 30:
        limit_int = 30

    limit = limit_int

    # Validate category parameter
    valid_categories = ["techo", "pared", "camara", "accesorio", "all"]
    if category not in valid_categories:
        return {
            "ok": False,
            "contract_version": "v1",
            "error": {
                "code": "INVALID_CATEGORY",
                "message": f"Invalid category '{category}'. Must be one of: {', '.join(valid_categories)}",
                "details": {"category": category}
            }
        }

    try:
        catalog = _load_catalog()
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        # Catalog data file issues - use CATALOG_UNAVAILABLE
        logger.exception("Catalog data unavailable")
        return {
            "ok": False,
            "contract_version": "v1",
            "error": {
                "code": "CATALOG_UNAVAILABLE",
                "message": "Catalog data is currently unavailable",
                "details": {}
            }
        }
    except Exception:
        # Other unexpected errors during catalog loading
        logger.exception("Error loading catalog")
        return {
            "ok": False,
            "contract_version": "v1",
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Internal error processing catalog_search request",
                "details": {}
            }
        }
    
    try:
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

            # Transform to contract schema format, using the lightweight helper as the base
            lightweight = _to_lightweight(product)
            result = {
                "product_id": str(lightweight.get("id", "")),
                "name": lightweight.get("title", ""),
                "category": lightweight.get("type", ""),
            }

            # Add optional fields if available
            handle_val = lightweight.get("handle", "")
            if handle_val:
                result["url"] = f"https://bmcuruguay.uy/products/{handle_val}"
            # Simple relevance score based on position in search results
            # Score decreases linearly from 1.0 to 0.1 as more results are added
            result["score"] = min(1.0, max(0.1, 1.0 - (len(results) * 0.05)))
            
            results.append(result)
            if len(results) >= limit:
                break

        return {
            "ok": True,
            "contract_version": "v1",
            "results": results
        }

    except Exception:
        # Log the full exception for debugging
        logger.exception("Error processing catalog_search request")
        
        return {
            "ok": False,
            "contract_version": "v1",
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Internal error processing catalog_search request",
                "details": {}
            }
        }
