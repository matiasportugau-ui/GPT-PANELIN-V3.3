"""Handler for the price_check MCP tool.

Loads bromyros_pricing_master.json and provides lookup by SKU, family, type,
or free-text search. All prices are in USD with IVA 22% included.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from mcp_tools.contracts import CONTRACT_VERSION, PRICE_CHECK_ERROR_CODES

logger = logging.getLogger(__name__)

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
    # Handle nested data structure: {"data": {"products": [...]}}
    if isinstance(data, dict) and "data" in data:
        data = data["data"]
    
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
        
        # Extract thickness - check both root level and nested specifications
        thickness = product.get("espesor_mm", product.get("thickness", product.get("espesor")))
        if thickness is None:
            specs = product.get("specifications", {})
            if isinstance(specs, dict):
                thickness = specs.get("thickness_mm", specs.get("espesor_mm"))

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


def _map_product_to_match(product: dict[str, Any]) -> dict[str, Any]:
    """Map product data to v1 contract match format."""
    # Extract SKU
    sku = str(product.get("sku", product.get("SKU", product.get("codigo", ""))))
    
    # Build description from available fields
    name = str(product.get("nombre", product.get("name", product.get("title", ""))))
    family = str(product.get("familia", product.get("family", "")))
    description = name if name else f"{family} {sku}".strip()
    
    # Extract thickness - check both root level and nested specifications
    thickness = product.get("espesor_mm", product.get("thickness", product.get("espesor")))
    if thickness is None:
        specs = product.get("specifications", {})
        if isinstance(specs, dict):
            thickness = specs.get("thickness_mm", specs.get("espesor_mm"))
    
    thickness_mm = None
    if thickness is not None:
        try:
            thickness_mm = float(thickness)
        except (ValueError, TypeError):
            pass
    
    # Extract price (IVA included)
    price = 0.0
    pricing_data = product.get("pricing", {})
    if isinstance(pricing_data, dict):
        # Try web_iva_inc first, then sale_iva_inc
        price = pricing_data.get("web_iva_inc", pricing_data.get("sale_iva_inc", 0.0))
    
    match_obj: dict[str, Any] = {
        "sku": sku,
        "description": description,
        "price_usd_iva_inc": float(price),
    }
    
    # Only include thickness_mm if it's available
    if thickness_mm is not None:
        match_obj["thickness_mm"] = thickness_mm
    
    return match_obj


async def handle_price_check(arguments: dict[str, Any], legacy_format: bool = False) -> dict[str, Any]:
    """Execute price_check tool and return results in v1 contract format.
    
    Args:
        arguments: Tool arguments containing query, filter_type, thickness_mm
        legacy_format: If True, return legacy format for backwards compatibility
    
    Returns:
        v1 contract envelope: {ok, contract_version, matches} or {ok, contract_version, error}
    """
    query = arguments.get("query", "")
    filter_type = arguments.get("filter_type", "search")
    thickness_mm = arguments.get("thickness_mm")

    # Strip whitespace from query before validation
    query = query.strip()

    # Validate query parameter (minLength: 2 per contract)
    if not query or len(query) < 2:
        error_response = {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": PRICE_CHECK_ERROR_CODES["INVALID_FILTER"],
                "message": "Query parameter is required and must be at least 2 characters long",
            }
        }
        if legacy_format:
            return {"error": "Query parameter is required and must be at least 2 characters long", "results": []}
        logger.debug("Wrapped price_check error response in v1 envelope")
        return error_response
    
    # Validate filter_type (must be one of allowed values per contract)
    allowed_filter_types = ["sku", "family", "type", "search"]
    if filter_type not in allowed_filter_types:

        error_response = {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": PRICE_CHECK_ERROR_CODES["INVALID_FILTER"],
                "message": f"filter_type must be one of {allowed_filter_types}",
                "details": {"received": filter_type}
            }
        }
        if legacy_format:
            return {"error": f"filter_type must be one of {allowed_filter_types}", "results": []}
        logger.debug("Wrapped price_check error response in v1 envelope")
        return error_response
    
    # Validate thickness_mm (must be in range [20, 250] per contract)
    if thickness_mm is not None:
        try:
            thickness_val = float(thickness_mm)
            if thickness_val < 20 or thickness_val > 250:
                error_response = {
                    "ok": False,
                    "contract_version": CONTRACT_VERSION,
                    "error": {
                        "code": PRICE_CHECK_ERROR_CODES["INVALID_THICKNESS"],
                        "message": "thickness_mm must be between 20 and 250",
                        "details": {"received": thickness_mm}
                    }
                }
                if legacy_format:
                    return {"error": "thickness_mm must be between 20 and 250", "results": []}
                logger.debug("Wrapped price_check error response in v1 envelope")
                return error_response
        except (ValueError, TypeError):
            error_response = {
                "ok": False,
                "contract_version": CONTRACT_VERSION,
                "error": {
                    "code": PRICE_CHECK_ERROR_CODES["INVALID_THICKNESS"],
                    "message": "thickness_mm must be a valid number",
                    "details": {"received": thickness_mm}
                }
            }
            if legacy_format:
                return {"error": "thickness_mm must be a valid number", "results": []}
            logger.debug("Wrapped price_check error response in v1 envelope")
            return error_response

    try:
        data = _load_pricing()
        results = _search_products(data, query, filter_type, thickness_mm)

        if not results:
            error_response = {
                "ok": False,
                "contract_version": CONTRACT_VERSION,
                "error": {
                    "code": PRICE_CHECK_ERROR_CODES["SKU_NOT_FOUND"],
                    "message": f"No products found for query '{query}' (filter: {filter_type})",
                }
            }
            if legacy_format:
                return {
                    "message": f"No products found for query '{query}' (filter: {filter_type})",
                    "results": [],
                    "source": "bromyros_pricing_master.json (Level 1)",
                }
            logger.debug("Wrapped price_check error response in v1 envelope")
            return error_response

        # Map results to v1 contract format
        matches = [_map_product_to_match(product) for product in results[:20]]
        
        success_response = {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "matches": matches,
        }
        
        if legacy_format:
            return {
                "message": f"Found {len(results)} product(s)",
                "results": results[:20],
                "source": "bromyros_pricing_master.json (Level 1)",
                "note": "Prices in USD, IVA 22% included",
            }
        
        logger.debug(f"Wrapped price_check response in v1 envelope with {len(matches)} matches")
        return success_response
        
    except Exception as e:
        error_response = {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": PRICE_CHECK_ERROR_CODES["INTERNAL_ERROR"],
                "message": f"Internal error during price lookup: {str(e)}",
            }
        }
        if legacy_format:
            return {"error": f"Internal error: {str(e)}", "results": []}
        logger.exception("Internal error during price lookup")
        return error_response
