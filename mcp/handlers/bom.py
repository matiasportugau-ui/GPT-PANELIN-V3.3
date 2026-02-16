"""Handler for the bom_calculate MCP tool.

Uses bom_rules.json to calculate a complete Bill of Materials for a given
panel installation. Applies parametric rules per construction system.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
from pathlib import Path
from typing import Any

from mcp_tools.contracts import CONTRACT_VERSION, BOM_CALCULATE_ERROR_CODES
from mcp.handlers.pricing import handle_price_check

logger = logging.getLogger(__name__)

KB_ROOT = Path(__file__).resolve().parent.parent.parent
BOM_FILE = KB_ROOT / "bom_rules.json"
ACCESSORIES_FILE = KB_ROOT / "accessories_catalog.json"

_bom_rules: dict[str, Any] | None = None
_accessories: dict[str, Any] | None = None


def _load_bom_rules() -> dict[str, Any]:
    global _bom_rules
    if _bom_rules is None:
        with open(BOM_FILE, encoding="utf-8") as f:
            _bom_rules = json.load(f)
    return _bom_rules


def _load_accessories() -> dict[str, Any]:
    global _accessories
    if _accessories is None:
        with open(ACCESSORIES_FILE, encoding="utf-8") as f:
            _accessories = json.load(f)
    return _accessories


def _resolve_system_key(family: str, core: str, usage: str) -> str | None:
    """Map product parameters to BOM system key."""
    family_upper = family.upper()
    usage_lower = usage.lower()

    mapping = {
        ("ISOROOF", "techo"): "techo_isoroof_3g",
        ("ISODEC", "techo"): f"techo_isodec_{core.lower()}",
        ("ISOPANEL", "pared"): "pared_isopanel_eps",
        ("ISOWALL", "pared"): "pared_isowall_pir",
        ("ISOFRIG", "camara"): "pared_isofrig_pir",
    }

    return mapping.get((family_upper, usage_lower))


def _get_autoportancia(
    family: str,
    core: str,
    thickness: int,
    producto_ref: str | None = None,
) -> float | None:
    """Retrieve autoportancia (self-supporting span) from bom_rules.json.
    
    Returns the luz_max_m value for the given product family, core, and thickness.
    This is used to calculate the number of supports needed.
    
    If ``producto_ref`` is provided, it is used directly as the lookup key into
    ``autoportancia.tablas`` (after upper-casing). This allows callers that
    already resolved the system (and its producto_ref) to avoid duplicating
    mapping logic here. If ``producto_ref`` is not provided, a best-effort
    mapping is derived from ``family`` and ``core`` for backwards compatibility.
    """
    rules = _load_bom_rules()
    autoportancia_tables = rules.get("autoportancia", {}).get("tablas", {})

    # Prefer explicit producto_ref when available to avoid duplicating mapping logic.
    if producto_ref:
        key = producto_ref.upper()
    else:
        # Build the key for the autoportancia table from family/core as fallback.
        family_upper = family.upper()
        if family_upper == "ISOROOF":
            key = "ISOROOF_3G"
        elif family_upper == "ISODEC":
            key = f"ISODEC_{core.upper()}"
        elif family_upper == "ISOPANEL":
            key = f"ISOPANEL_{core.upper()}"
        elif family_upper == "ISOWALL":
            # ISOWALL typically uses PIR
            key = "ISOWALL_PIR"
        elif family_upper == "ISOFRIG":
            # ISOFRIG typically uses PIR
            key = "ISOFRIG_PIR"
        else:
            return None

    # Normalize thickness to integer string (e.g., 80.0 -> "80")
    # The tool schema accepts JSON numbers which may be floats
    thickness_int = int(thickness) if thickness else 0
    thickness_str = str(thickness_int)
    
    table = autoportancia_tables.get(key, {})
    entry = table.get(thickness_str, {})
    return entry.get("luz_max_m")


async def handle_bom_calculate(arguments: dict[str, Any], legacy_format: bool = False) -> dict[str, Any]:
    """Execute bom_calculate tool and return BOM breakdown in v1 contract format.
    
    Args:
        arguments: Tool arguments containing product_family, thickness_mm, core_type, usage, length_m, width_m
        legacy_format: If True, return legacy format for backwards compatibility
    
    Returns:
        v1 contract envelope: {ok, contract_version, items, summary} or {ok, contract_version, error}
        arguments: Tool arguments containing product_family, thickness_mm, core_type, usage, dimensions
        legacy_format: If True, return legacy format for backwards compatibility
    
    Returns:
        v1 contract envelope: {ok, contract_version, summary, items} or {ok, contract_version, error}
    """
    family = arguments.get("product_family", "")
    thickness = arguments.get("thickness_mm", 0)
    core = arguments.get("core_type", "EPS")
    usage = arguments.get("usage", "")
    length = arguments.get("length_m", 0)
    width = arguments.get("width_m", 0)
    qty_panels = arguments.get("quantity_panels")

    # Validate required parameters
    if not family or not usage or not length or not width:
        error_response = {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": BOM_CALCULATE_ERROR_CODES["INVALID_DIMENSIONS"],
                "message": "product_family, usage, length_m, and width_m are required",
            }
        }
        if legacy_format:
            return {"error": "product_family, usage, length_m, and width_m are required"}
        logger.debug("Wrapped bom_calculate error response in v1 envelope")
        return error_response
    
    # Validate usage parameter (must be one of allowed values per contract)
    allowed_usage_values = ["techo", "pared", "camara"]
    if usage not in allowed_usage_values:
        error_response = {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": BOM_CALCULATE_ERROR_CODES["INVALID_DIMENSIONS"],
                "message": f"usage must be one of {allowed_usage_values}",
                "details": {"received": usage}
            }
        }
        if legacy_format:
            return {"error": f"usage must be one of {allowed_usage_values}"}
        logger.debug("Wrapped bom_calculate error response in v1 envelope")
        return error_response
    
    # Validate thickness_mm (must be in range [30, 250] per contract)
    if not thickness or thickness <= 0:
        error_response = {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": BOM_CALCULATE_ERROR_CODES["INVALID_THICKNESS"],
                "message": "thickness_mm is required and must be a positive number",
                "details": {"received": thickness}
            }
        }
        if legacy_format:
            return {
                "error": "thickness_mm is required and must be a positive number",
                "received": thickness
            }
        logger.debug("Wrapped bom_calculate error response in v1 envelope")
        return error_response
    
    try:
        thickness_val = float(thickness)
        if thickness_val < 30 or thickness_val > 250:
            error_response = {
                "ok": False,
                "contract_version": CONTRACT_VERSION,
                "error": {
                    "code": BOM_CALCULATE_ERROR_CODES["INVALID_THICKNESS"],
                    "message": "thickness_mm must be between 30 and 250",
                    "details": {"received": thickness}
                }
            }
            if legacy_format:
                return {"error": "thickness_mm must be between 30 and 250", "received": thickness}
            logger.debug("Wrapped bom_calculate error response in v1 envelope")
            return error_response
    except (ValueError, TypeError):
        error_response = {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": BOM_CALCULATE_ERROR_CODES["INVALID_THICKNESS"],
                "message": "thickness_mm must be a valid number",
                "details": {"received": thickness}
            }
        }
        if legacy_format:
            return {"error": "thickness_mm must be a valid number", "received": thickness}
        logger.debug("Wrapped bom_calculate error response in v1 envelope")
        return error_response
    
    # Validate length_m (must be in range (0, 30] per contract with exclusiveMinimum)
    try:
        length_val = float(length)
        if length_val <= 0 or length_val > 30:
            error_response = {
                "ok": False,
                "contract_version": CONTRACT_VERSION,
                "error": {
                    "code": BOM_CALCULATE_ERROR_CODES["INVALID_DIMENSIONS"],
                    "message": "length_m must be greater than 0 and at most 30",
                    "details": {"received": length}
                }
            }
            if legacy_format:
                return {"error": "length_m must be greater than 0 and at most 30"}
            logger.debug("Wrapped bom_calculate error response in v1 envelope")
            return error_response
    except (ValueError, TypeError):
        error_response = {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": BOM_CALCULATE_ERROR_CODES["INVALID_DIMENSIONS"],
                "message": "length_m must be a valid number",
                "details": {"received": length}
            }
        }
        if legacy_format:
            return {"error": "length_m must be a valid number"}
        logger.debug("Wrapped bom_calculate error response in v1 envelope")
        return error_response
    
    # Validate width_m (must be in range (0, 20] per contract with exclusiveMinimum)
    try:
        width_val = float(width)
        if width_val <= 0 or width_val > 20:
            error_response = {
                "ok": False,
                "contract_version": CONTRACT_VERSION,
                "error": {
                    "code": BOM_CALCULATE_ERROR_CODES["INVALID_DIMENSIONS"],
                    "message": "width_m must be greater than 0 and at most 20",
                    "details": {"received": width}
                }
            }
            if legacy_format:
                return {"error": "width_m must be greater than 0 and at most 20"}
            logger.debug("Wrapped bom_calculate error response in v1 envelope")
            return error_response
    except (ValueError, TypeError):
        error_response = {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": BOM_CALCULATE_ERROR_CODES["INVALID_DIMENSIONS"],
                "message": "width_m must be a valid number",
                "details": {"received": width}
            }
        }
        if legacy_format:
            return {"error": "width_m must be a valid number"}
        logger.debug("Wrapped bom_calculate error response in v1 envelope")
        return error_response
    
    # Validate quantity_panels if provided (must be in range [1, 2000] per contract)
    if qty_panels is not None:
        try:
            qty_panels_val = int(qty_panels)
            if qty_panels_val < 1 or qty_panels_val > 2000:
                error_response = {
                    "ok": False,
                    "contract_version": CONTRACT_VERSION,
                    "error": {
                        "code": BOM_CALCULATE_ERROR_CODES["INVALID_DIMENSIONS"],
                        "message": "quantity_panels must be between 1 and 2000",
                        "details": {"received": qty_panels}
                    }
                }
                if legacy_format:
                    return {"error": "quantity_panels must be between 1 and 2000"}
                logger.debug("Wrapped bom_calculate error response in v1 envelope")
                return error_response
            qty_panels = qty_panels_val
        except (ValueError, TypeError):
            error_response = {
                "ok": False,
                "contract_version": CONTRACT_VERSION,
                "error": {
                    "code": BOM_CALCULATE_ERROR_CODES["INVALID_DIMENSIONS"],
                    "message": "quantity_panels must be a valid integer",
                    "details": {"received": qty_panels}
                }
            }
            if legacy_format:
                return {"error": "quantity_panels must be a valid integer"}
            logger.debug("Wrapped bom_calculate error response in v1 envelope")
            return error_response

    try:
        rules = _load_bom_rules()
        system_key = _resolve_system_key(family, core, usage)

        if not system_key:
            error_response = {
                "ok": False,
                "contract_version": CONTRACT_VERSION,
                "error": {
                    "code": BOM_CALCULATE_ERROR_CODES["RULE_NOT_FOUND"],
                    "message": f"No BOM rules found for {family} {core} {usage}",
                    "details": {
                        "hint": "Valid systems: techo_isoroof_3g, techo_isodec_eps, techo_isodec_pir, pared_isopanel_eps, pared_isowall_pir, pared_isofrig_pir"
                    }
                }
            }
            if legacy_format:
                return {
                    "error": f"No BOM rules found for {family} {core} {usage}",
                    "hint": "Valid systems: techo_isoroof_3g, techo_isodec_eps, techo_isodec_pir, pared_isopanel_eps, pared_isowall_pir, pared_isofrig_pir",
                }
            logger.debug("Wrapped bom_calculate error response in v1 envelope")
            return error_response

        # Look up system rules
        systems = rules.get("sistemas", rules.get("systems", {}))
        system = systems.get(system_key)

        if not system:
            error_response = {
                "ok": False,
                "contract_version": CONTRACT_VERSION,
                "error": {
                    "code": BOM_CALCULATE_ERROR_CODES["RULE_NOT_FOUND"],
                    "message": f"System '{system_key}' not found in bom_rules.json",
                    "details": {"available_systems": list(systems.keys())}
                }
            }
            if legacy_format:
                return {
                    "error": f"System '{system_key}' not found in bom_rules.json",
                    "available_systems": list(systems.keys()),
                }
            logger.debug("Wrapped bom_calculate error response in v1 envelope")
            return error_response

        # Basic panel calculation
        panel_width_m = 1.0  # Default useful width in meters (most panels are ~1m useful)
        if qty_panels is None:
            qty_panels = max(1, int(length / panel_width_m + 0.5))

        area_m2 = length * width
        
        # Calculate supports using correct formula: ROUNDUP((length_m / autoportancia) + 1)
        # Use producto_ref from system to avoid duplicating mapping logic
        producto_ref = system.get("producto_ref")
        autoportancia = _get_autoportancia(family, core, thickness, producto_ref=producto_ref)
        
        if autoportancia and autoportancia > 0:
            # Formula from quotation_calculator_v3.py:414-427 and bom_rules.json
            n_supports = max(2, math.ceil((length / autoportancia) + 1))
        else:
            # Fallback if autoportancia not found
            n_supports = max(2, math.ceil(length / 3.0) + 1)  # Conservative fallback: 3m span

        # Build items array for v1 contract
        items: list[dict[str, Any]] = []
        
        # Construct SKU for panel lookup - try to match pricing data format
        # Pricing data has SKUs like "IROOF30", "IROOF50", etc.
        # Try different SKU formats
        thickness_int = int(thickness)
        sku_candidates = [
            f"{family.upper()}{thickness_int}",  # e.g., "ISODEC100"
            f"{family.upper()}-{thickness_int}",  # e.g., "ISODEC-100"
            f"{family.upper()}_{core.upper()}_{thickness_int}",  # e.g., "ISODEC_EPS_100"
        ]
        
        # Try to fetch price for panels using pricing handler
        panel_unit_price = 0.0
        panel_sku = sku_candidates[0]  # Default to first format
        
        # Note: Internal calls to handle_price_check always use v1 format (legacy_format not passed)
        # regardless of the format requested by external callers. This ensures consistent internal
        # communication while maintaining backwards compatibility at the API boundary.
        
        # Parallelize SKU candidate price checks using asyncio.gather()
        # NOTE: sku_candidates is a small, fixed list of format variants (currently 3).
        # If this list is ever expanded to many dynamically generated candidates, add
        # explicit concurrency limiting (e.g., using an asyncio.Semaphore around
        # handle_price_check) to avoid creating too many parallel requests.
        async def fetch_price(sku: str) -> tuple[str, dict | None]:
            """Fetch price for a single SKU candidate."""
            try:
                result = await handle_price_check({"query": sku, "filter_type": "sku"})
                if result.get("ok") and result.get("matches"):
                    return (sku, result["matches"][0])
            except Exception as e:
                logger.debug(f"Failed to fetch price for SKU candidate '{sku}': {e}")
            return (sku, None)
        
        # NOTE: sku_candidates is a small, fixed list of format variants (currently 3).
        # If this list is ever expanded to many dynamically generated candidates, add
        # explicit concurrency limiting (e.g., using an asyncio.Semaphore around
        # handle_price_check) to avoid creating too many parallel requests.
        # Fetch all SKU candidates in parallel
        price_results = await asyncio.gather(*[fetch_price(sku) for sku in sku_candidates])
        
        # Use the first successful result
        for sku_candidate, match in price_results:
            if match:
                panel_unit_price = match.get("price_usd_iva_inc", 0.0)
                panel_sku = match.get("sku", sku_candidate)
                break
        
        # Add panel item
        panel_subtotal = panel_unit_price * qty_panels
        items.append({
            "item_type": "panel",
            "sku": panel_sku,
            "quantity": qty_panels,
            "unit": "unit",
            "unit_price_usd_iva_inc": panel_unit_price,
            "subtotal_usd_iva_inc": panel_subtotal,
        })
        
        # Calculate total
        total_usd_iva_inc = sum(item["subtotal_usd_iva_inc"] for item in items)
        
        # Build v1 contract response
        success_response = {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "summary": {
                "area_m2": area_m2,
                "panel_count": qty_panels,
                "total_usd_iva_inc": total_usd_iva_inc,
            },
            "items": items,
        }
        
        if legacy_format:
            support_note = f"Calculated from length ({length}m) / autoportancia ({autoportancia}m)" if autoportancia else f"Fallback estimate (autoportancia not found for {family} {core} {thickness_int}mm)"
            return {
                "system": system_key,
                "product": f"{family} {core} {thickness_int}mm",
                "dimensions": {"length_m": length, "width_m": width, "area_m2": area_m2},
                "panels": {"quantity": qty_panels, "note": "Verify against useful panel width from KB"},
                "supports": n_supports,
                "supports_note": support_note,
                "bom_rules_applied": system,
                "source": "bom_rules.json (Level 1.3) + accessories_catalog.json (Level 1.2)",
                "note": "This is a parametric estimate. Final BOM should be validated against KB formulas in BMC_Base_Conocimiento_GPT-2.json.",
            }
        
        logger.debug(f"Wrapped bom_calculate response in v1 envelope with {len(items)} items")
        return success_response
        
    except Exception as e:
        error_response = {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": BOM_CALCULATE_ERROR_CODES["INTERNAL_ERROR"],
                "message": f"Internal error during BOM calculation: {str(e)}",
            }
        }
        if legacy_format:
            return {"error": f"Internal error: {str(e)}"}
        logger.exception("Internal error during BOM calculation")
        return error_response
