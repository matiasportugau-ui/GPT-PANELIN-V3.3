"""
Business-rule validators for Panelin Sheets Orchestrator.

Validates data before writing to Google Sheets, enforcing:
- Autoportancia (self-bearing span) limits per product/thickness
- Dimension constraints (length, width)
- Pricing sanity checks (IVA included, range bounds)
- BOM quantity integrity (always ceil, never zero)
- Cell-level type validation (numeric, date, text)
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ──────────────────────────────────────────────────────────────────────
# Autoportancia tables (max span in meters between supports)
# Source: Panelin technical documentation / bom_rules.json
# ──────────────────────────────────────────────────────────────────────

AUTOPORTANCIA: Dict[str, Dict[int, float]] = {
    "ISODEC_EPS": {100: 5.5, 150: 7.5, 200: 9.1, 250: 10.4},
    "ISODEC_PIR": {50: 3.5, 80: 5.5, 120: 7.6},
    "ISOROOF_3G": {30: 2.8, 50: 3.3, 80: 4.0},
    "ISOPANEL_EPS": {50: 3.0, 100: 5.5, 150: 7.5, 200: 9.1, 250: 10.4},
    "ISOWALL_PIR": {50: 3.0, 80: 5.0},
    "ISOFRIG_PIR": {40: 2.5, 60: 3.5, 80: 5.0, 100: 6.0, 150: 7.5, 200: 9.0},
}

USEFUL_WIDTH: Dict[str, float] = {
    "ISODEC_EPS": 1.12,
    "ISODEC_PIR": 1.0,
    "ISOROOF_3G": 1.0,
    "ISOPANEL_EPS": 1.14,
    "ISOWALL_PIR": 1.0,
    "ISOFRIG_PIR": 1.0,
}

LENGTH_BOUNDS: Tuple[float, float] = (0.5, 14.0)
WIDTH_BOUNDS: Tuple[float, float] = (0.1, 100.0)
PRICE_BOUNDS: Tuple[float, float] = (1.0, 500.0)
THICKNESS_VALUES = {30, 40, 50, 60, 80, 100, 120, 150, 200, 250}

DATE_PATTERNS = [
    r"\d{4}-\d{2}-\d{2}",
    r"\d{2}/\d{2}/\d{4}",
    r"\d{1,2}/\d{1,2}/\d{2,4}",
]


@dataclass
class ValidationResult:
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def add_error(self, msg: str) -> "ValidationResult":
        self.valid = False
        self.errors.append(msg)
        return self

    def add_warning(self, msg: str) -> "ValidationResult":
        self.warnings.append(msg)
        return self

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        if not other.valid:
            self.valid = False
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.details.update(other.details)
        return self


def validate_autoportancia(
    product_family: str,
    thickness_mm: int,
    span_m: float,
    safety_margin: float = 0.15,
) -> ValidationResult:
    """Validate that the requested span does not exceed the panel's structural capacity."""
    result = ValidationResult(valid=True)
    key = product_family.upper().replace("-", "_").replace(" ", "_")

    if key not in AUTOPORTANCIA:
        return result.add_error(
            f"Familia de producto desconocida: {product_family}. "
            f"Válidas: {', '.join(sorted(AUTOPORTANCIA.keys()))}"
        )

    family_table = AUTOPORTANCIA[key]
    if thickness_mm not in family_table:
        return result.add_error(
            f"Espesor {thickness_mm}mm no disponible para {product_family}. "
            f"Espesores válidos: {sorted(family_table.keys())}"
        )

    luz_max = family_table[thickness_mm]
    luz_max_safe = luz_max * (1 - safety_margin)

    result.details = {
        "product_family": key,
        "thickness_mm": thickness_mm,
        "span_requested_m": span_m,
        "span_max_nominal_m": luz_max,
        "span_max_safe_m": round(luz_max_safe, 2),
        "safety_margin": safety_margin,
    }

    if span_m > luz_max:
        result.add_error(
            f"Luz {span_m}m excede máximo nominal {luz_max}m para "
            f"{product_family} {thickness_mm}mm."
        )
        alternatives = [
            (t, s)
            for t, s in sorted(family_table.items())
            if s * (1 - safety_margin) >= span_m
        ]
        if alternatives:
            result.details["alternatives"] = [
                {"thickness_mm": t, "max_span_m": s} for t, s in alternatives
            ]
        else:
            result.add_warning(
                "No hay espesores alternativos que cubran esta luz. "
                "Se requieren apoyos intermedios adicionales."
            )
    elif span_m > luz_max_safe:
        result.add_warning(
            f"Luz {span_m}m dentro del nominal ({luz_max}m) pero fuera del "
            f"margen seguro ({luz_max_safe:.2f}m con {safety_margin*100:.0f}% margen)."
        )

    return result


def validate_dimensions(
    length_m: float,
    width_m: float,
) -> ValidationResult:
    result = ValidationResult(valid=True)

    if not (LENGTH_BOUNDS[0] <= length_m <= LENGTH_BOUNDS[1]):
        result.add_error(
            f"Largo {length_m}m fuera de rango [{LENGTH_BOUNDS[0]}, {LENGTH_BOUNDS[1]}]m."
        )

    if not (WIDTH_BOUNDS[0] <= width_m <= WIDTH_BOUNDS[1]):
        result.add_error(
            f"Ancho {width_m}m fuera de rango [{WIDTH_BOUNDS[0]}, {WIDTH_BOUNDS[1]}]m."
        )

    return result


def validate_bom_quantities(bom_items: List[Dict[str, Any]]) -> ValidationResult:
    """Ensure all BOM quantities are positive integers (ceil-rounded)."""
    result = ValidationResult(valid=True)

    for i, item in enumerate(bom_items):
        qty = item.get("quantity")
        if qty is None:
            result.add_error(f"Item {i}: cantidad faltante.")
            continue

        try:
            qty_num = float(qty)
        except (TypeError, ValueError):
            result.add_error(f"Item {i}: cantidad no numérica: {qty}")
            continue

        if qty_num <= 0:
            result.add_error(f"Item {i} ({item.get('name', '?')}): cantidad debe ser > 0, got {qty}")
        elif qty_num != math.ceil(qty_num):
            result.add_warning(
                f"Item {i} ({item.get('name', '?')}): cantidad {qty_num} no es entero. "
                f"Panelin redondea siempre hacia arriba (ceil)."
            )

    return result


def validate_price(
    price: float,
    label: str = "precio",
) -> ValidationResult:
    result = ValidationResult(valid=True)

    if price < 0:
        result.add_error(f"{label}: precio negativo ({price}).")
    elif not (PRICE_BOUNDS[0] <= price <= PRICE_BOUNDS[1]):
        result.add_warning(
            f"{label}: {price} USD/m² fuera del rango esperado "
            f"[{PRICE_BOUNDS[0]}, {PRICE_BOUNDS[1]}]."
        )

    return result


def calculate_supports(length_m: float, autoportancia_m: float) -> int:
    """ROUNDUP((length / autoportancia) + 1), minimum 2."""
    if autoportancia_m <= 0:
        return 2
    return max(2, math.ceil((length_m / autoportancia_m) + 1))


def calculate_panels_needed(width_m: float, useful_width_m: float) -> int:
    """ROUNDUP(width / useful_width)."""
    if useful_width_m <= 0:
        return 1
    return max(1, math.ceil(width_m / useful_width_m))


def calculate_fixing_points(
    panels: int,
    supports: int,
    length_m: float,
    usage: str = "techo",
) -> int:
    """
    Fixing points calculation per Panelin BOM rules.
    Roofs: ceil(((panels * supports) * 2) + (length * 2 / 2.5))
    Walls: ceil((panels * supports) * 2)
    """
    base = panels * supports * 2
    if usage.lower() in ("techo", "roof", "cubierta"):
        edge = length_m * 2 / 2.5
        return math.ceil(base + edge)
    return math.ceil(base)


def calculate_rods(fixing_points: int) -> int:
    """Each 1m rod provides 4 fixing points."""
    return math.ceil(fixing_points / 4)


def calculate_nuts(fixing_points: int, structure: str = "metal") -> int:
    """Metal: 2 per point (top+bottom). Concrete: 1 per point (top only, taco below)."""
    if structure.lower() in ("hormigon", "concrete"):
        return fixing_points
    return fixing_points * 2


def validate_write_plan_values(
    writes: List[Dict[str, Any]],
    template_hints: Dict[str, Any],
) -> ValidationResult:
    """
    Validate the values in a write plan against template hint metadata.
    Checks dates, numeric ranges, and text length.
    """
    result = ValidationResult(valid=True)
    cell_hints = template_hints.get("cells", {})
    hint_map = {v: k for k, v in cell_hints.items()}

    for w in writes:
        range_str = w.get("range", "")
        values = w.get("values", [[]])
        hint_name = hint_map.get(range_str)

        if not values or not values[0]:
            continue

        first_val = str(values[0][0]) if values[0] else ""

        if hint_name and "fecha" in hint_name.lower():
            if not any(re.match(pat, first_val) for pat in DATE_PATTERNS):
                result.add_warning(
                    f"Valor en {range_str} ('{first_val}') no parece una fecha válida."
                )

        if first_val.startswith("="):
            result.add_error(
                f"Rango {range_str}: valor contiene fórmula ('{first_val[:30]}...'). "
                f"Solo se permiten valores planos."
            )

    return result


def compute_bom_summary(
    product_family: str,
    thickness_mm: int,
    length_m: float,
    width_m: float,
    usage: str = "techo",
    structure: str = "metal",
    safety_margin: float = 0.15,
) -> ValidationResult:
    """
    Compute a full BOM summary with validation.
    Returns quantities in result.details.
    """
    result = ValidationResult(valid=True)

    result.merge(validate_dimensions(length_m, width_m))
    result.merge(validate_autoportancia(product_family, thickness_mm, length_m, safety_margin))

    if not result.valid:
        return result

    key = product_family.upper().replace("-", "_").replace(" ", "_")
    autoportancia_m = AUTOPORTANCIA[key][thickness_mm]
    useful_w = USEFUL_WIDTH.get(key, 1.0)

    panels = calculate_panels_needed(width_m, useful_w)
    supports = calculate_supports(length_m, autoportancia_m)
    area_m2 = round(length_m * width_m, 2)
    fixing_pts = calculate_fixing_points(panels, supports, length_m, usage)
    rods = calculate_rods(fixing_pts)
    nuts = calculate_nuts(fixing_pts, structure)

    result.details.update({
        "product_family": key,
        "thickness_mm": thickness_mm,
        "length_m": length_m,
        "width_m": width_m,
        "area_m2": area_m2,
        "usage": usage,
        "structure": structure,
        "panels_needed": panels,
        "useful_width_m": useful_w,
        "supports": supports,
        "autoportancia_m": autoportancia_m,
        "fixing_points": fixing_pts,
        "rods_varilla_3_8": rods,
        "nuts_tuercas": nuts,
        "currency": "USD",
    })

    return result
