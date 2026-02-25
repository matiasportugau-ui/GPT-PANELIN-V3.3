"""
Panelin v4.0 - BOM Engine
===========================

Generates Bill of Materials from structured QuoteRequest using
parametric rules from bom_rules.json.

Accessory selection follows strict priority:
    1. Exact family match
    2. Exact thickness match
    3. Sub-family compatible
    4. UNIVERSAL fallback

Produces quantities only -- pricing is handled by pricing_engine.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class BOMItem:
    tipo: str
    referencia: str
    sku: Optional[str] = None
    name: Optional[str] = None
    quantity: int = 0
    unit: str = "unid"
    formula_used: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "tipo": self.tipo,
            "referencia": self.referencia,
            "sku": self.sku,
            "name": self.name,
            "quantity": self.quantity,
            "unit": self.unit,
            "formula_used": self.formula_used,
            "notes": self.notes,
        }


@dataclass
class BOMResult:
    system_key: str
    area_m2: float
    panel_count: int
    supports_per_panel: int
    fixation_points: int
    items: list[BOMItem] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "system_key": self.system_key,
            "area_m2": self.area_m2,
            "panel_count": self.panel_count,
            "supports_per_panel": self.supports_per_panel,
            "fixation_points": self.fixation_points,
            "items": [i.to_dict() for i in self.items],
            "warnings": self.warnings,
        }


_BOM_RULES_CACHE: Optional[dict] = None
_ACCESSORIES_CACHE: Optional[dict] = None

KB_ROOT = Path(__file__).resolve().parent.parent.parent


def _load_bom_rules() -> dict:
    global _BOM_RULES_CACHE
    if _BOM_RULES_CACHE is None:
        with open(KB_ROOT / "bom_rules.json", encoding="utf-8") as f:
            _BOM_RULES_CACHE = json.load(f)
    return _BOM_RULES_CACHE


def _load_accessories() -> dict:
    global _ACCESSORIES_CACHE
    if _ACCESSORIES_CACHE is None:
        with open(KB_ROOT / "accessories_catalog.json", encoding="utf-8") as f:
            _ACCESSORIES_CACHE = json.load(f)
    return _ACCESSORIES_CACHE


def _resolve_system_key(familia: str, core: str, uso: str) -> Optional[str]:
    """Map product parameters to BOM system key."""
    mapping = {
        ("ISOROOF", "techo"): "techo_isoroof_3g",
        ("ISODEC", "techo"): f"techo_isodec_{core.lower()}",
        ("ISOPANEL", "pared"): "pared_isopanel_eps",
        ("ISOWALL", "pared"): "pared_isowall_pir",
        ("ISOFRIG", "camara"): "pared_isofrig_pir",
        ("ISOFRIG", "pared"): "pared_isofrig_pir",
    }
    return mapping.get((familia.upper(), uso.lower()))


def _get_autoportancia_m(familia: str, core: str, thickness_mm: int) -> Optional[float]:
    rules = _load_bom_rules()
    tables = rules.get("autoportancia", {}).get("tablas", {})
    key = f"{familia}_{core}".upper()
    if familia.upper() == "ISOROOF":
        key = "ISOROOF_3G"
    entry = tables.get(key, {}).get(str(thickness_mm), {})
    return entry.get("luz_max_m")


def _find_accessory(
    tipo: str,
    familia: str,
    thickness_mm: Optional[int] = None,
) -> Optional[dict]:
    """Find best matching accessory using priority: family > thickness > UNIVERSAL."""
    catalog = _load_accessories()
    accesorios = catalog.get("accesorios", [])

    # Filter by type
    candidates = [a for a in accesorios if a.get("tipo") == tipo]
    if not candidates:
        return None

    # Priority 1: exact family match
    family_matches = [
        a for a in candidates
        if familia.upper() in [c.upper() for c in a.get("compatibilidad", [])]
    ]

    # Priority 2: thickness match within family
    if thickness_mm and family_matches:
        thick_matches = [
            a for a in family_matches
            if a.get("espesor_mm") == thickness_mm
        ]
        if thick_matches:
            return thick_matches[0]

    if family_matches:
        return family_matches[0]

    # Priority 3: UNIVERSAL fallback
    universal = [
        a for a in candidates
        if "UNIVERSAL" in [c.upper() for c in a.get("compatibilidad", [])]
    ]
    if universal:
        return universal[0]

    return candidates[0] if candidates else None


def calculate_bom(
    familia: str,
    sub_familia: str,
    thickness_mm: int,
    uso: str,
    length_m: float,
    width_m: float,
    structure_type: str = "metal",
    panel_count: Optional[int] = None,
    panel_lengths: Optional[list[float]] = None,
    roof_type: Optional[str] = None,
    span_m: Optional[float] = None,
) -> BOMResult:
    """Calculate complete BOM for a panel installation.

    This is a pure deterministic function. No LLM inference involved.
    """
    rules = _load_bom_rules()

    system_key = _resolve_system_key(familia, sub_familia, uso)
    if not system_key:
        return BOMResult(
            system_key="unknown",
            area_m2=0, panel_count=0,
            supports_per_panel=0, fixation_points=0,
            warnings=[f"No BOM rules for {familia} {sub_familia} {uso}"],
        )

    systems = rules.get("sistemas", {})
    system = systems.get(system_key)
    if not system:
        parent_key = system.get("hereda_de") if system else None
        if parent_key:
            system = systems.get(parent_key, {})
        if not system:
            return BOMResult(
                system_key=system_key,
                area_m2=0, panel_count=0,
                supports_per_panel=0, fixation_points=0,
                warnings=[f"System {system_key} not found in bom_rules"],
            )

    # Handle inheritance
    if system.get("hereda_de"):
        parent = systems.get(system["hereda_de"], {})
        merged = {**parent, **{k: v for k, v in system.items() if k != "hereda_de"}}
        system = merged

    ancho_util_m = system.get("ancho_util_m", 1.12)

    # Calculate area
    area_m2 = length_m * width_m

    # Calculate panel count
    if panel_count is None:
        panel_count = math.ceil(width_m / ancho_util_m)

    # Autoportancia for support calculation
    autoportancia_m = _get_autoportancia_m(familia, sub_familia, thickness_mm)
    if autoportancia_m and autoportancia_m > 0:
        supports = max(2, math.ceil(length_m / autoportancia_m) + 1)
    else:
        supports = max(2, math.ceil(length_m / 3.0) + 1)

    # Fixation points
    is_roof = uso.lower() in ("techo", "cubierta")
    if is_roof:
        base_fix = panel_count * supports * 2
        edge_fix = math.ceil(length_m * 2 / 2.5)
        fix_points = base_fix + edge_fix
    else:
        fix_points = panel_count * supports * 2

    warnings: list[str] = []
    items: list[BOMItem] = []

    # Panel item
    items.append(BOMItem(
        tipo="panel",
        referencia=f"{familia}_{sub_familia}_{thickness_mm}mm",
        quantity=panel_count,
        unit="unid",
        formula_used=f"ceil({width_m} / {ancho_util_m}) = {panel_count}",
    ))

    # Build accessory items based on system
    perimeter_ml = 2 * (panel_count * ancho_util_m) + 2 * length_m

    if is_roof:
        _add_roof_accessories(
            items, warnings, familia, thickness_mm,
            panel_count, ancho_util_m, length_m, width_m,
            supports, fix_points, structure_type,
            perimeter_ml, system, roof_type,
        )
    else:
        _add_wall_accessories(
            items, warnings, familia, thickness_mm,
            panel_count, ancho_util_m, length_m, width_m,
            fix_points, structure_type, perimeter_ml, system,
        )

    return BOMResult(
        system_key=system_key,
        area_m2=round(area_m2, 2),
        panel_count=panel_count,
        supports_per_panel=supports,
        fixation_points=fix_points,
        items=items,
        warnings=warnings,
    )


def _add_roof_accessories(
    items: list[BOMItem],
    warnings: list[str],
    familia: str,
    thickness_mm: int,
    panel_count: int,
    ancho_util_m: float,
    length_m: float,
    width_m: float,
    supports: int,
    fix_points: int,
    structure_type: str,
    perimeter_ml: float,
    system: dict,
    roof_type: Optional[str],
) -> None:
    """Add roof-specific accessories to BOM items list."""
    stds = system.get("largos_estandar_m", {})
    largo_gotero_f = stds.get("gotero_frontal", 3.03)
    largo_gotero_l = stds.get("gotero_lateral", 3.0)
    largo_babeta = stds.get("babeta_adosar", 3.03)
    largo_cumbrera = stds.get("cumbrera", 3.0)
    largo_canalon = stds.get("canalon", 3.03)

    front_coverage = panel_count * ancho_util_m
    gotero_f_qty = math.ceil(front_coverage / largo_gotero_f)
    gotero_l_qty = math.ceil((length_m * 2) / largo_gotero_l)

    acc = _find_accessory("gotero_frontal", familia, thickness_mm)
    items.append(BOMItem(
        tipo="gotero_frontal", referencia="gotero_frontal",
        sku=acc["sku"] if acc else None,
        name=acc["name"] if acc else None,
        quantity=gotero_f_qty, unit="unid",
        formula_used=f"ceil(({panel_count} × {ancho_util_m}) / {largo_gotero_f})",
    ))

    acc = _find_accessory("gotero_lateral", familia, thickness_mm)
    items.append(BOMItem(
        tipo="gotero_lateral", referencia="gotero_lateral",
        sku=acc["sku"] if acc else None,
        name=acc["name"] if acc else None,
        quantity=gotero_l_qty, unit="unid",
        formula_used=f"ceil(({length_m} × 2) / {largo_gotero_l})",
    ))

    # Cumbrera (if 2+ aguas)
    if roof_type in ("2_aguas", "4_aguas", "mariposa"):
        cumbrera_qty = math.ceil(width_m / largo_cumbrera)
        acc = _find_accessory("cumbrera", familia, thickness_mm)
        items.append(BOMItem(
            tipo="cumbrera", referencia="cumbrera",
            sku=acc["sku"] if acc else None,
            name=acc["name"] if acc else None,
            quantity=cumbrera_qty, unit="unid",
            formula_used=f"ceil({width_m} / {largo_cumbrera})",
        ))

    # Fixation components
    is_isoroof = familia.upper() == "ISOROOF"

    if is_isoroof:
        caballetes = panel_count * supports
        acc = _find_accessory("arandela_trapezoidal", familia, thickness_mm)
        items.append(BOMItem(
            tipo="caballete", referencia="caballete_isoroof",
            sku=acc["sku"] if acc else None,
            name=acc["name"] if acc else None,
            quantity=caballetes, unit="unid",
            formula_used=f"{panel_count} × {supports}",
        ))
    else:
        varilla_qty = math.ceil(fix_points / 4)
        acc = _find_accessory("varilla", familia, thickness_mm)
        items.append(BOMItem(
            tipo="varilla", referencia="varilla_3_8",
            sku=acc["sku"] if acc else None,
            name=acc["name"] if acc else None,
            quantity=varilla_qty, unit="unid",
            formula_used=f"ceil({fix_points} / 4)",
        ))

        if structure_type == "metal":
            tuerca_qty = fix_points * 2
        else:
            tuerca_qty = fix_points

        acc = _find_accessory("tuerca", familia, thickness_mm)
        items.append(BOMItem(
            tipo="tuerca", referencia="tuerca_3_8",
            sku=acc["sku"] if acc else None,
            name=acc["name"] if acc else None,
            quantity=tuerca_qty, unit="unid",
            formula_used=f"fix_points × {'2 (metal)' if structure_type == 'metal' else '1 (hormigon)'}",
        ))

        acc = _find_accessory("arandela_carrocero", familia, thickness_mm)
        items.append(BOMItem(
            tipo="arandela_carrocero", referencia="arandela_carrocero_3_8",
            sku=acc["sku"] if acc else None,
            name=acc["name"] if acc else None,
            quantity=fix_points, unit="unid",
            formula_used=f"fix_points = {fix_points}",
        ))

        acc = _find_accessory("tortuga_pvc", familia, thickness_mm)
        items.append(BOMItem(
            tipo="tortuga_pvc", referencia="tortuga_pvc",
            sku=acc["sku"] if acc else None,
            name=acc["name"] if acc else None,
            quantity=fix_points, unit="unid",
            formula_used=f"fix_points = {fix_points}",
        ))

        if structure_type == "hormigon":
            acc = _find_accessory("taco", familia, thickness_mm)
            items.append(BOMItem(
                tipo="taco", referencia="taco_3_8",
                sku=acc["sku"] if acc else None,
                name=acc["name"] if acc else None,
                quantity=fix_points, unit="unid",
                formula_used=f"fix_points = {fix_points} (hormigon only)",
            ))

    # Silicone
    silicona_qty = math.ceil(perimeter_ml / 8)
    acc = _find_accessory("silicona", familia, thickness_mm)
    items.append(BOMItem(
        tipo="silicona", referencia="silicona_neutra",
        sku=acc["sku"] if acc else None,
        name=acc["name"] if acc else None,
        quantity=silicona_qty, unit="tubo",
        formula_used=f"ceil({perimeter_ml:.1f} / 8)",
    ))

    # Cinta butilo
    butilo_qty = math.ceil(perimeter_ml / 22.5)
    acc = _find_accessory("cinta_butilo", familia, thickness_mm)
    items.append(BOMItem(
        tipo="cinta_butilo", referencia="cinta_butilo",
        sku=acc["sku"] if acc else None,
        name=acc["name"] if acc else None,
        quantity=butilo_qty, unit="rollo",
        formula_used=f"ceil({perimeter_ml:.1f} / 22.5)",
    ))

    # Profile fixation (rivets/T1)
    perfileria_fix = math.ceil(perimeter_ml / 0.30)
    acc = _find_accessory("fijacion_perfileria", familia, thickness_mm)
    if acc is None:
        acc = _find_accessory("remache", familia, thickness_mm)
    items.append(BOMItem(
        tipo="fijacion_perfileria", referencia="remache_o_t1",
        sku=acc["sku"] if acc else None,
        name=acc["name"] if acc else None,
        quantity=perfileria_fix, unit="unid",
        formula_used=f"ceil({perimeter_ml:.1f} / 0.30)",
    ))


def _add_wall_accessories(
    items: list[BOMItem],
    warnings: list[str],
    familia: str,
    thickness_mm: int,
    panel_count: int,
    ancho_util_m: float,
    length_m: float,
    height_m: float,
    fix_points: int,
    structure_type: str,
    perimeter_ml: float,
    system: dict,
) -> None:
    """Add wall-specific accessories to BOM items list."""
    largo_perfil_u = 3.0

    # Profile U (top + bottom)
    u_inferior = math.ceil(length_m / largo_perfil_u)
    u_superior = math.ceil(length_m / largo_perfil_u)

    acc = _find_accessory("perfil_u", familia, thickness_mm)
    items.append(BOMItem(
        tipo="perfil_u", referencia="perfil_u",
        sku=acc["sku"] if acc else None,
        name=acc["name"] if acc else None,
        quantity=u_inferior + u_superior, unit="unid",
        formula_used=f"ceil({length_m} / {largo_perfil_u}) × 2",
    ))

    # Fixation: varilla + tuercas + arandelas + tortugas
    varilla_qty = math.ceil(fix_points / 4)
    acc = _find_accessory("varilla", familia, thickness_mm)
    items.append(BOMItem(
        tipo="varilla", referencia="varilla_3_8",
        sku=acc["sku"] if acc else None,
        name=acc["name"] if acc else None,
        quantity=varilla_qty, unit="unid",
        formula_used=f"ceil({fix_points} / 4)",
    ))

    tuerca_qty = fix_points * (2 if structure_type == "metal" else 1)
    acc = _find_accessory("tuerca", familia, thickness_mm)
    items.append(BOMItem(
        tipo="tuerca", referencia="tuerca_3_8",
        sku=acc["sku"] if acc else None,
        name=acc["name"] if acc else None,
        quantity=tuerca_qty, unit="unid",
    ))

    acc = _find_accessory("arandela_carrocero", familia, thickness_mm)
    items.append(BOMItem(
        tipo="arandela_carrocero", referencia="arandela_carrocero_3_8",
        sku=acc["sku"] if acc else None,
        name=acc["name"] if acc else None,
        quantity=fix_points, unit="unid",
    ))

    acc = _find_accessory("tortuga_pvc", familia, thickness_mm)
    items.append(BOMItem(
        tipo="tortuga_pvc", referencia="tortuga_pvc",
        sku=acc["sku"] if acc else None,
        name=acc["name"] if acc else None,
        quantity=fix_points, unit="unid",
    ))

    if structure_type == "hormigon":
        acc = _find_accessory("taco", familia, thickness_mm)
        items.append(BOMItem(
            tipo="taco", referencia="taco_3_8",
            sku=acc["sku"] if acc else None,
            name=acc["name"] if acc else None,
            quantity=fix_points, unit="unid",
        ))

    # Sealants
    juntas_ml = (panel_count - 1) * height_m * 2
    silicona_qty = max(1, math.ceil(juntas_ml / 8))
    acc = _find_accessory("silicona", familia, thickness_mm)
    items.append(BOMItem(
        tipo="silicona", referencia="silicona_neutra",
        sku=acc["sku"] if acc else None,
        name=acc["name"] if acc else None,
        quantity=silicona_qty, unit="tubo",
        formula_used=f"ceil({juntas_ml:.1f} / 8)",
    ))

    butilo_qty = max(1, math.ceil(juntas_ml / 22.5))
    acc = _find_accessory("cinta_butilo", familia, thickness_mm)
    items.append(BOMItem(
        tipo="cinta_butilo", referencia="cinta_butilo",
        sku=acc["sku"] if acc else None,
        name=acc["name"] if acc else None,
        quantity=butilo_qty, unit="rollo",
        formula_used=f"ceil({juntas_ml:.1f} / 22.5)",
    ))
