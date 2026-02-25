"""
Panelin v4.0 - Structural Risk Engine (SRE)
=============================================

Calculates a risk score (0-100) for each quotation request.
The score determines the quotation level:

    0-30:  Level 3 - Formal Certified (full validation, PDF/JSON ready)
    31-60: Level 2 - Technical Conditioned (valid with warnings)
    61-85: Level 1 - Commercial Quick (pre-quote with assumptions)
    86+:   Technical Block (requires human review)

The SRE NEVER blocks quotations by itself. It classifies risk so
the orchestrator can decide the appropriate response level.

SRE = R_datos + R_autoportancia + R_geometria + R_sistema

Each component is capped to prevent runaway scores.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from panelin_v4.engine.parser import QuoteRequest


class QuotationLevel(str, Enum):
    LEVEL_3_FORMAL = "formal_certified"
    LEVEL_2_CONDITIONED = "technical_conditioned"
    LEVEL_1_COMMERCIAL = "commercial_quick"
    TECHNICAL_BLOCK = "technical_block"


@dataclass
class SREResult:
    """Structural Risk Engine calculation result."""
    score: int
    level: QuotationLevel
    r_datos: int
    r_autoportancia: int
    r_geometria: int
    r_sistema: int
    breakdown: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    alternative_thicknesses: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "level": self.level.value,
            "r_datos": self.r_datos,
            "r_autoportancia": self.r_autoportancia,
            "r_geometria": self.r_geometria,
            "r_sistema": self.r_sistema,
            "breakdown": self.breakdown,
            "recommendations": self.recommendations,
            "alternative_thicknesses": self.alternative_thicknesses,
        }


_BOM_RULES_CACHE: Optional[dict] = None


def _load_bom_rules() -> dict:
    global _BOM_RULES_CACHE
    if _BOM_RULES_CACHE is None:
        path = Path(__file__).resolve().parent.parent.parent / "bom_rules.json"
        with open(path, encoding="utf-8") as f:
            _BOM_RULES_CACHE = json.load(f)
    return _BOM_RULES_CACHE


def _get_autoportancia(family: str, core: str, thickness_mm: int) -> Optional[float]:
    """Look up max span from autoportancia tables."""
    rules = _load_bom_rules()
    tables = rules.get("autoportancia", {}).get("tablas", {})

    key = f"{family}_{core}".upper()
    if family.upper() == "ISOROOF":
        key = "ISOROOF_3G"

    table = tables.get(key, {})
    entry = table.get(str(thickness_mm), {})
    return entry.get("luz_max_m")


def _find_valid_thicknesses(family: str, core: str, span_m: float) -> list[int]:
    """Find thicknesses that satisfy the given span."""
    rules = _load_bom_rules()
    tables = rules.get("autoportancia", {}).get("tablas", {})

    key = f"{family}_{core}".upper()
    if family.upper() == "ISOROOF":
        key = "ISOROOF_3G"

    table = tables.get(key, {})
    valid = []
    for thick_str, data in table.items():
        luz_max = data.get("luz_max_m", 0)
        if span_m <= luz_max:
            valid.append(int(thick_str))
    valid.sort()
    return valid


def _calc_r_datos(req: QuoteRequest) -> tuple[int, list[str]]:
    """Calculate data completeness risk (0-40, capped)."""
    score = 0
    breakdown = []

    if req.uso in ("techo", None) and req.span_m is None:
        score += 40
        breakdown.append("span_m missing for roof (+40)")

    if not req.thickness_mm:
        penalty = 25
        score += penalty
        breakdown.append(f"thickness_mm missing (+{penalty})")

    if not req.structure_type:
        penalty = 15
        score += penalty
        breakdown.append(f"structure_type missing (+{penalty})")

    has_dims = (
        req.geometry.length_m is not None
        or len(req.geometry.panel_lengths) > 0
    )
    if not has_dims:
        penalty = 20
        score += penalty
        breakdown.append(f"dimensions incomplete (+{penalty})")

    text_lower = req.raw_text.lower()
    if any(kw in text_lower for kw in ["ver plano", "aguardo planta", "ver presupuesto"]):
        penalty = 25
        score += penalty
        breakdown.append(f"plan reference without measurements (+{penalty})")

    return min(score, 40), breakdown


def _calc_r_autoportancia(req: QuoteRequest) -> tuple[int, list[str], list[int]]:
    """Calculate autoportancia risk (0-50)."""
    if req.span_m is None or req.familia is None or req.thickness_mm is None:
        return 0, ["autoportancia not calculable (missing data)"], []

    core = req.sub_familia or "EPS"
    luz_max = _get_autoportancia(req.familia, core, req.thickness_mm)

    if luz_max is None:
        return 10, [f"no autoportancia table for {req.familia}_{core} {req.thickness_mm}mm (+10)"], []

    ratio = req.span_m / luz_max
    breakdown = [f"span={req.span_m}m, luz_max={luz_max}m, ratio={ratio:.2f}"]
    alternatives: list[int] = []

    if ratio <= 0.60:
        return 0, breakdown + ["ratio <= 0.60: safe (0)"], alternatives
    elif ratio <= 0.75:
        return 10, breakdown + ["ratio 0.61-0.75: low risk (+10)"], alternatives
    elif ratio <= 0.85:
        return 20, breakdown + ["ratio 0.76-0.85: moderate risk (+20)"], alternatives
    elif ratio <= 1.0:
        return 30, breakdown + ["ratio 0.86-1.00: near limit (+30)"], alternatives
    else:
        alternatives = _find_valid_thicknesses(req.familia, core, req.span_m)
        return 50, breakdown + [f"ratio > 1.0: EXCEEDS capacity (+50)"], alternatives


def _calc_r_geometria(req: QuoteRequest) -> tuple[int, list[str]]:
    """Calculate geometric complexity risk (0-15)."""
    score = 0
    breakdown = []

    if req.roof_type == "4_aguas":
        score += 8
        breakdown.append("4 aguas roof (+8)")
    elif req.roof_type == "mariposa":
        score += 10
        breakdown.append("mariposa roof (+10)")
    elif req.roof_type == "2_aguas":
        score += 5
        breakdown.append("2 aguas roof (+5)")

    if req.geometry.panel_lengths:
        max_len = max(req.geometry.panel_lengths)
        if max_len > 12.0:
            score += 10
            breakdown.append(f"panel > 12m ({max_len}m) (+10)")

    text_lower = req.raw_text.lower()
    if "unid" in text_lower and "centro" in text_lower:
        score += 5
        breakdown.append("central union detected (+5)")

    return min(score, 15), breakdown


def _calc_r_sistema(req: QuoteRequest) -> tuple[int, list[str]]:
    """Calculate system sensitivity risk (0-15)."""
    score = 0
    breakdown = []

    if req.uso == "pared":
        breakdown.append("wall system: no structural risk (0)")
        return 0, breakdown

    familia = (req.familia or "").upper()

    if "ISOROOF" in familia:
        score += 10
        breakdown.append("ISOROOF system (+10)")
    elif "ISODEC" in familia:
        core = (req.sub_familia or "EPS").upper()
        if core == "PIR":
            score += 8
            breakdown.append("ISODEC PIR system (+8)")
        else:
            score += 5
            breakdown.append("ISODEC EPS system (+5)")

    if req.thickness_mm and req.thickness_mm <= 50:
        score += 5
        breakdown.append(f"thin panel ({req.thickness_mm}mm) (+5)")

    return min(score, 15), breakdown


def _determine_level(score: int) -> QuotationLevel:
    if score <= 30:
        return QuotationLevel.LEVEL_3_FORMAL
    elif score <= 60:
        return QuotationLevel.LEVEL_2_CONDITIONED
    elif score <= 85:
        return QuotationLevel.LEVEL_1_COMMERCIAL
    else:
        return QuotationLevel.TECHNICAL_BLOCK


def calculate_sre(req: QuoteRequest) -> SREResult:
    """Calculate the Structural Risk Engine score for a quote request.

    This function NEVER raises. It always returns a result with
    the appropriate risk classification.
    """
    r_datos, bd_datos = _calc_r_datos(req)
    r_autoportancia, bd_auto, alternatives = _calc_r_autoportancia(req)
    r_geometria, bd_geo = _calc_r_geometria(req)
    r_sistema, bd_sys = _calc_r_sistema(req)

    total_score = r_datos + r_autoportancia + r_geometria + r_sistema
    level = _determine_level(total_score)

    all_breakdown = bd_datos + bd_auto + bd_geo + bd_sys

    recommendations: list[str] = []
    if r_autoportancia >= 50 and alternatives:
        recommendations.append(
            f"Span exceeds capacity. Consider thickness: {alternatives[0]}mm"
        )
    elif r_autoportancia >= 50:
        span = req.span_m or 0
        recommendations.append(
            f"Add intermediate support to reduce span from {span}m to {span / 2:.1f}m"
        )

    if "span_m" in (req.incomplete_fields or []):
        recommendations.append(
            "Provide span (distance between supports) for structural validation."
        )

    if level == QuotationLevel.LEVEL_1_COMMERCIAL:
        recommendations.append(
            "Pre-quotation with assumptions. Requires structural confirmation before formal emission."
        )

    return SREResult(
        score=total_score,
        level=level,
        r_datos=r_datos,
        r_autoportancia=r_autoportancia,
        r_geometria=r_geometria,
        r_sistema=r_sistema,
        breakdown=all_breakdown,
        recommendations=recommendations,
        alternative_thicknesses=alternatives,
    )
