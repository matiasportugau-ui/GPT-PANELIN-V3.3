"""Handler for the bom_calculate MCP tool.

Uses bom_rules.json to calculate a complete Bill of Materials for a given
panel installation. Applies parametric rules per construction system.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

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


async def handle_bom_calculate(arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute bom_calculate tool and return BOM breakdown in v1 contract format."""
    family = arguments.get("product_family", "")
    thickness = arguments.get("thickness_mm", 0)
    core = arguments.get("core_type", "EPS")
    usage = arguments.get("usage", "")
    length = arguments.get("length_m", 0)
    width = arguments.get("width_m", 0)
    qty_panels = arguments.get("quantity_panels")

    # Validate required parameters
    if not family or not usage or not length or not width:
        return {
            "ok": False,
            "contract_version": "v1",
            "error": {
                "code": "INVALID_DIMENSIONS",
                "message": "product_family, usage, length_m, and width_m are required",
                "details": {"family": family, "usage": usage, "length": length, "width": width}
            }
        }
    
    # Validate thickness_mm
    if not thickness or thickness <= 0:
        return {
            "ok": False,
            "contract_version": "v1",
            "error": {
                "code": "INVALID_THICKNESS",
                "message": "thickness_mm is required and must be a positive number",
                "details": {"thickness_mm": thickness}
            }
        }

    try:
        rules = _load_bom_rules()
        system_key = _resolve_system_key(family, core, usage)

        if not system_key:
            return {
                "ok": False,
                "contract_version": "v1",
                "error": {
                    "code": "RULE_NOT_FOUND",
                    "message": f"No BOM rules found for {family} {core} {usage}",
                    "details": {
                        "family": family,
                        "core": core,
                        "usage": usage,
                        "hint": "Valid systems: techo_isoroof_3g, techo_isodec_eps, techo_isodec_pir, pared_isopanel_eps, pared_isowall_pir, pared_isofrig_pir"
                    }
                }
            }

        # Look up system rules
        systems = rules.get("sistemas", rules.get("systems", {}))
        system = systems.get(system_key)

        if not system:
            return {
                "ok": False,
                "contract_version": "v1",
                "error": {
                    "code": "RULE_NOT_FOUND",
                    "message": f"System '{system_key}' not found in bom_rules.json",
                    "details": {"system_key": system_key, "available_systems": list(systems.keys())}
                }
            }

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

        # Build items list - basic structure without pricing
        # Note: Pricing lookup would require integration with handle_price_check
        # For now, we return the BOM structure with placeholder prices
        items = [
            {
                "item_type": "panel",
                "sku": f"{family}-{int(thickness)}-{int(length*1000)}",  # Synthetic SKU format
                "quantity": qty_panels,
                "unit": "unit",
                "unit_price_usd_iva_inc": 0.0,  # Pricing not integrated yet
                "subtotal_usd_iva_inc": 0.0
            },
            {
                "item_type": "fixation",
                "sku": "SUPPORT-STD",  # Generic support SKU
                "quantity": n_supports,
                "unit": "unit",
                "unit_price_usd_iva_inc": 0.0,  # Pricing not integrated yet
                "subtotal_usd_iva_inc": 0.0
            }
        ]

        return {
            "ok": True,
            "contract_version": "v1",
            "summary": {
                "area_m2": area_m2,
                "panel_count": qty_panels,
                "total_usd_iva_inc": 0.0  # Sum of item subtotals (currently 0 without pricing)
            },
            "items": items
        }

    except Exception as e:
        return {
            "ok": False,
            "contract_version": "v1",
            "error": {
                "code": "INTERNAL_ERROR",
                "message": f"Internal error during BOM calculation: {str(e)}",
                "details": {"exception_type": type(e).__name__}
            }
        }
