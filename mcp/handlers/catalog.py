"""Handler for the catalog_search MCP tool.

Searches shopify_catalog_v1.json for products by name, category, or keyword.
Returns lightweight results (id, title, handle, type, vendor, tags).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from mcp_tools.contracts import CONTRACT_VERSION, CATALOG_SEARCH_ERROR_CODES

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


def _calculate_score(product: dict[str, Any], query: str, norm_query: str) -> float:
    """Calculate relevance score (0.0-1.0) based on match quality."""
    title = _normalize(product.get("title", ""))
    ptype = _normalize(product.get("product_type", ""))
    handle = _normalize(product.get("handle", ""))
    
    score = 0.0
    
    # Exact match in title gets highest score
    if norm_query == title:
        score = 1.0
    # Title starts with query
    elif title.startswith(norm_query):
        score = 0.95
    # Query is in title
    elif norm_query in title:
        score = 0.85
    # Exact match in handle
    elif norm_query == handle:
        score = 0.8
    # Handle contains query
    elif norm_query in handle:
        score = 0.7
    # Product type match
    elif norm_query in ptype:
        score = 0.6
    # General match (tags, etc)
    else:
        score = 0.5
    
    return score


def _map_to_v1_result(product: dict[str, Any], query: str, norm_query: str) -> dict[str, Any]:
    """Map product to v1 contract result format."""
    product_id = str(product.get("id", ""))
    name = product.get("title", "")
    category = product.get("product_type", "")
    handle = product.get("handle", "")
    
    # Construct URL from handle (assuming BMC Uruguay shop structure)
    url = f"https://shop.bmcuruguay.com/products/{handle}" if handle else ""
    
    # Calculate relevance score
    score = _calculate_score(product, query, norm_query)
    
    result: dict[str, Any] = {
        "product_id": product_id,
        "name": name,
        "category": category,
    }
    
    # Add optional fields
    if url:
        result["url"] = url
    result["score"] = score
    
    return result


CATEGORY_MAP = {
    "techo": ["techo", "roof", "isoroof", "isodec", "cubierta"],
    "pared": ["pared", "wall", "isowall", "isopanel"],
    "camara": ["camara", "frio", "isofrig", "frigorifico"],
    "accesorio": ["accesorio", "accessory", "fijacion", "tornillo", "cumbrera", "babeta"],
}


async def handle_catalog_search(arguments: dict[str, Any], legacy_format: bool = False) -> dict[str, Any]:
    """Execute catalog_search tool and return lightweight results in v1 contract format.
    
    Args:
        arguments: Tool arguments containing query, category, limit
        legacy_format: If True, return legacy format for backwards compatibility
    
    Returns:
        v1 contract envelope: {ok, contract_version, results} or {ok, contract_version, error}
    """
    query = arguments.get("query", "")
    category = arguments.get("category", "all")
    limit = arguments.get("limit", 5)

    # Strip whitespace from query before validation
    query = query.strip()

    # Validate query parameter (minLength: 2 per contract)
    if not query or len(query) < 2:
        error_response = {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": CATALOG_SEARCH_ERROR_CODES["QUERY_TOO_SHORT"],
                "message": "Query parameter is required and must be at least 2 characters long",
            }
        }
        if legacy_format:
            return {"error": "Query parameter is required and must be at least 2 characters long", "results": []}
        logger.debug("Wrapped catalog_search error response in v1 envelope")
        return error_response
    
    # Validate and clamp limit parameter (must be in range [1, 30] per contract)
    try:
        limit = int(limit)
        if limit < 1:
            limit = 1
        elif limit > 30:
            limit = 30
    except (ValueError, TypeError):
        limit = 5  # Use default if conversion fails

    try:
        catalog = _load_catalog()
    except Exception as e:
        error_response = {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": CATALOG_SEARCH_ERROR_CODES["CATALOG_UNAVAILABLE"],
                "message": f"Failed to load catalog: {str(e)}",
            }
        }
        if legacy_format:
            return {"error": f"Failed to load catalog: {str(e)}", "results": []}
        logger.debug("Wrapped catalog_search error response in v1 envelope")
        return error_response
    
    if not query:
        return {
            "ok": False,
            "contract_version": "v1",
            "error": {
                "code": "QUERY_TOO_SHORT",
                "message": "Query parameter is required",
                "details": {}
            }
        }
    
    if len(query) < 2:
        return {
            "ok": False,
            "contract_version": "v1",
            "error": {
                "code": "QUERY_TOO_SHORT",
                "message": "Query must be at least 2 characters long",
                "details": {"query": query}
            }
        }
    
    if category not in ["techo", "pared", "camara", "accesorio", "all"]:
        return {
            "ok": False,
            "contract_version": "v1",
            "error": {
                "code": "INVALID_CATEGORY",
                "message": f"Invalid category: {category}",
                "details": {"category": category, "valid_categories": ["techo", "pared", "camara", "accesorio", "all"]}
            }
        }

    catalog = _load_catalog()
    norm_query = _normalize(query)

    # Determine category keywords
    category_keywords: list[str] = []
    if category != "all":
        if category in CATEGORY_MAP:
            category_keywords = CATEGORY_MAP[category]
        else:
            error_response = {
                "ok": False,
                "contract_version": CONTRACT_VERSION,
                "error": {
                    "code": CATALOG_SEARCH_ERROR_CODES["INVALID_CATEGORY"],
                    "message": f"Invalid category: {category}",
                    "details": {"valid_categories": list(CATEGORY_MAP.keys()) + ["all"]}
                }
            }
            if legacy_format:
                return {"error": f"Invalid category: {category}", "results": []}
            logger.debug("Wrapped catalog_search error response in v1 envelope")
            return error_response

    try:
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

            results.append(product)
            if len(results) >= limit:
                break

        # Map to v1 contract format
        v1_results = [_map_to_v1_result(product, query, norm_query) for product in results]
        
        success_response = {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "results": v1_results,
        }
        
        if legacy_format:
            return {
                "message": f"Found {len(results)} product(s) for '{query}'",
                "results": [_to_lightweight(p) for p in results],
                "source": "shopify_catalog_v1.json (Level 1.6)",
                "total_catalog_size": len(catalog),
            }
        
        logger.debug(f"Wrapped catalog_search response in v1 envelope with {len(v1_results)} results")
        return success_response
        
    except Exception as e:
        error_response = {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": CATALOG_SEARCH_ERROR_CODES["INTERNAL_ERROR"],
                "message": f"Internal error during catalog search: {str(e)}",
            }
        }
        if legacy_format:
            return {"error": f"Internal error: {str(e)}", "results": []}
        logger.exception("Internal error during catalog search")
        return error_response


def _infer_category(searchable_text: str) -> str:
    """Infer product category from searchable text."""
    text = searchable_text.lower()
    if any(kw in text for kw in CATEGORY_MAP["techo"]):
        return "techo"
    elif any(kw in text for kw in CATEGORY_MAP["pared"]):
        return "pared"
    elif any(kw in text for kw in CATEGORY_MAP["camara"]):
        return "camara"
    elif any(kw in text for kw in CATEGORY_MAP["accesorio"]):
        return "accesorio"
    return "other"
