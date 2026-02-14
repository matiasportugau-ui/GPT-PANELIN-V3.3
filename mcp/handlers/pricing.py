"""Handler for the price_check MCP tool.

Loads bromyros_pricing_master.json and provides lookup by SKU, family, type,
or free-text search. All prices are in USD with IVA 22% included.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

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


def _extract_thickness(product: dict[str, Any]) -> float | None:
    """Extract thickness value from product, checking multiple possible locations."""
    thickness = product.get("espesor_mm", product.get("thickness", product.get("espesor")))
    if thickness is None and "specifications" in product:
        specs = product["specifications"]
        if isinstance(specs, dict):
            thickness = specs.get("thickness_mm", specs.get("espesor_mm"))
    return thickness


def _search_products(data: dict[str, Any] | list[Any], query: str, filter_type: str = "search",
                     thickness_mm: float | None = None) -> list[dict[str, Any]]:
    """Search pricing data for matching products."""
    results: list[dict[str, Any]] = []
    norm_query = _normalize(query)

    # Navigate the pricing structure — adapt to actual JSON shape
    if isinstance(data, list):
        products = data
    elif isinstance(data, dict):
        # First try the expected nested structure
        if "data" in data and isinstance(data["data"], dict) and "products" in data["data"]:
            products = data["data"]["products"]
        # Fall back to flat structure for backwards compatibility
        elif "products" in data:
            products = data["products"]
        elif "items" in data:
            products = data["items"]
        else:
            products = []
    else:
        products = []
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
        thickness = _extract_thickness(product)

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
    """Execute price_check tool and return v1 contract envelope."""
    query = arguments.get("query", "")
    filter_type = arguments.get("filter_type", "search")
    thickness_mm = arguments.get("thickness_mm")

    # Validate query parameter (contract requires minLength=2, strip whitespace)
    query_stripped = query.strip() if isinstance(query, str) else ""
    if len(query_stripped) < 2:
        return {
            "ok": False,
            "contract_version": "v1",
            "error": {
                "code": "INVALID_FILTER",
                "message": "Query parameter must be at least 2 characters long",
                "details": {"query": query}
            }
        }
    
    # Use the stripped query for processing
    query = query_stripped

    # Validate filter_type if provided
    valid_filters = ["sku", "family", "type", "search"]
    if filter_type not in valid_filters:
        return {
            "ok": False,
            "contract_version": "v1",
            "error": {
                "code": "INVALID_FILTER",
                "message": f"Invalid filter_type '{filter_type}'. Must be one of: {', '.join(valid_filters)}",
                "details": {"filter_type": filter_type}
            }
        }

    # Validate thickness_mm if provided
    if thickness_mm is not None:
        if not isinstance(thickness_mm, (int, float)) or thickness_mm < 20 or thickness_mm > 250:
            return {
                "ok": False,
                "contract_version": "v1",
                "error": {
                    "code": "INVALID_THICKNESS",
                    "message": f"thickness_mm must be between 20 and 250, got {thickness_mm}",
                    "details": {"thickness_mm": thickness_mm}
                }
            }

    try:
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
        for product in results[:20]:  # Cap at 20 results
            sku = str(product.get("sku", product.get("SKU", product.get("codigo", ""))))
            name = str(product.get("nombre", product.get("name", product.get("title", ""))))
            thickness = _extract_thickness(product)
            
            # Extract price - try multiple paths in pricing data
            price = None
            pricing_data = product.get("pricing", {})
            if isinstance(pricing_data, dict):
                price = pricing_data.get("web_iva_inc") or pricing_data.get("sale_iva_inc")
            if price is None:
                price = product.get("precio", product.get("price", 0))
            
            # Convert to float, default to 0 if invalid
            try:
                price = float(price) if price is not None else 0
            except (ValueError, TypeError):
                price = 0

            match = {
                "sku": sku,
                "description": name,
                "price_usd_iva_inc": price
            }
            
            # Add thickness if available
            if thickness is not None:
                try:
                    match["thickness_mm"] = float(thickness)
                except (ValueError, TypeError):
                    pass
            
            matches.append(match)

        return {
            "ok": True,
            "contract_version": "v1",
            "matches": matches
        }

    except Exception:
        # Log the full exception for debugging
        logger.exception("Error processing price_check request")
        
        return {
            "ok": False,
            "contract_version": "v1",
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Internal error processing price_check request",
                "details": {}
            }
        }
