"""Handler for the bom_calculate MCP tool.

Uses bom_rules.json to calculate a complete Bill of Materials for a given
panel installation. Applies parametric rules per construction system.
"""

from __future__ import annotations

import json
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


async def handle_bom_calculate(arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute bom_calculate tool and return BOM breakdown."""
    family = arguments.get("product_family", "")
    thickness = arguments.get("thickness_mm", 0)
    core = arguments.get("core_type", "EPS")
    usage = arguments.get("usage", "")
    length = arguments.get("length_m", 0)
    width = arguments.get("width_m", 0)
    qty_panels = arguments.get("quantity_panels")

    if not family or not usage or not length or not width:
        return {"error": "product_family, usage, length_m, and width_m are required"}

    rules = _load_bom_rules()
    system_key = _resolve_system_key(family, core, usage)

    if not system_key:
        return {
            "error": f"No BOM rules found for {family} {core} {usage}",
            "hint": "Valid systems: techo_isoroof_3g, techo_isodec_eps, techo_isodec_pir, pared_isopanel_eps, pared_isowall_pir, pared_isofrig_pir",
        }

    # Look up system rules
    systems = rules.get("sistemas", rules.get("systems", {}))
    system = systems.get(system_key)

    if not system:
        return {
            "error": f"System '{system_key}' not found in bom_rules.json",
            "available_systems": list(systems.keys()),
        }

    # Basic panel calculation
    panel_width_m = 1.0  # Default useful width in meters (most panels are ~1m useful)
    if qty_panels is None:
        qty_panels = max(1, int(length / panel_width_m + 0.5))

    area_m2 = length * width
    n_supports = max(2, int(width) + 1)  # Minimum 2 supports

    return {
        "system": system_key,
        "product": f"{family} {core} {thickness}mm",
        "dimensions": {"length_m": length, "width_m": width, "area_m2": area_m2},
        "panels": {"quantity": qty_panels, "note": "Verify against useful panel width from KB"},
        "supports": n_supports,
        "bom_rules_applied": system,
        "source": "bom_rules.json (Level 1.3) + accessories_catalog.json (Level 1.2)",
        "note": "This is a parametric estimate. Final BOM should be validated against KB formulas in BMC_Base_Conocimiento_GPT-2.json.",
    }
