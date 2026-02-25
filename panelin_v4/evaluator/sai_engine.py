"""
Panelin v4.0 - System Accuracy Index (SAI) Engine
=====================================================

Calculates a quality score (0-100) for each quotation output.
Used to measure system performance and detect regressions.

Scoring:
    Base: 100 points

    Penalties:
        -30: Structural error (autoportancia exceeded without alternative)
        -25: IVA calculation error
        -20: Accessory incompatible with family
        -15: Missing BOM items for complete system
        -10: Unnecessary blocking in pre_cotizacion mode
        -10: Missing prices that exist in KB
        -5:  Inconsistent units
        -5:  Assumptions used without declaration

    Bonuses:
        +5: Alternative thickness suggested when needed
        +3: Optimization suggestion provided
        +2: Complete client data

Targets:
    formal:         SAI >= 95
    pre_cotizacion:  SAI >= 80
    informativo:     SAI >= 60
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from panelin_v4.engine.quotation_engine import QuotationOutput


@dataclass
class SAIPenalty:
    code: str
    points: int
    description: str

    def to_dict(self) -> dict:
        return {"code": self.code, "points": self.points, "description": self.description}


@dataclass
class SAIResult:
    score: float
    grade: str  # A (95+), B (85-94), C (70-84), D (60-69), F (<60)
    passed: bool
    target: float
    penalties: list[SAIPenalty] = field(default_factory=list)
    bonuses: list[SAIPenalty] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "grade": self.grade,
            "passed": self.passed,
            "target": self.target,
            "penalties": [p.to_dict() for p in self.penalties],
            "bonuses": [b.to_dict() for b in self.bonuses],
        }


def _get_target(mode: str) -> float:
    targets = {
        "formal": 95.0,
        "pre_cotizacion": 80.0,
        "informativo": 60.0,
    }
    return targets.get(mode, 80.0)


def _grade(score: float) -> str:
    if score >= 95:
        return "A"
    elif score >= 85:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    return "F"


def calculate_sai(output: QuotationOutput) -> SAIResult:
    """Calculate the System Accuracy Index for a quotation output.

    Always returns a result. Never raises.
    """
    score = 100.0
    penalties: list[SAIPenalty] = []
    bonuses: list[SAIPenalty] = []

    validation = output.validation
    sre = output.sre
    pricing = output.pricing
    bom = output.bom
    mode = output.mode

    # ── Penalties ──

    # P1: Autoportancia exceeded without alternative
    if sre.get("r_autoportancia", 0) >= 50:
        if not sre.get("alternative_thicknesses"):
            penalties.append(SAIPenalty("P1", -30, "Autoportancia exceeded without alternative"))
            score -= 30
        else:
            penalties.append(SAIPenalty("P1a", -10, "Autoportancia exceeded (alternative provided)"))
            score -= 10

    # P2: Mathematical inconsistency
    expected = round(
        pricing.get("subtotal_panels_usd", 0) + pricing.get("subtotal_accessories_usd", 0), 2
    )
    actual = pricing.get("subtotal_total_usd", 0)
    if abs(actual - expected) > 0.02:
        penalties.append(SAIPenalty("P2", -25, f"Math error: total {actual} != expected {expected}"))
        score -= 25

    # P3: Missing prices that should exist
    missing = pricing.get("missing_prices", [])
    if missing:
        penalty = min(len(missing) * 10, 20)
        penalties.append(SAIPenalty("P3", -penalty, f"{len(missing)} missing price(s)"))
        score -= penalty

    # P4: BOM warnings
    bom_warnings = bom.get("warnings", [])
    if bom_warnings:
        penalty = min(len(bom_warnings) * 5, 15)
        penalties.append(SAIPenalty("P4", -penalty, f"{len(bom_warnings)} BOM warning(s)"))
        score -= penalty

    # P5: Validation issues
    val_issues = validation.get("issues", [])
    critical_issues = [i for i in val_issues if i.get("severity") == "critical"]
    if critical_issues:
        penalty = min(len(critical_issues) * 15, 30)
        penalties.append(SAIPenalty("P5", -penalty, f"{len(critical_issues)} critical validation issue(s)"))
        score -= penalty

    # P6: Unnecessary blocking in pre mode
    if mode == "pre_cotizacion" and output.status == "blocked":
        penalties.append(SAIPenalty("P6", -10, "Unnecessary blocking in pre_cotizacion mode"))
        score -= 10

    # P7: Assumptions used without declaration
    assumptions = output.assumptions_used
    if assumptions and not any("assumed" in a.lower() for a in assumptions):
        penalties.append(SAIPenalty("P7", -5, "Assumptions used but not properly declared"))
        score -= 5

    # P8: Zero panel count with valid request
    request = output.request
    if request.get("familia") and bom.get("panel_count", 0) == 0:
        penalties.append(SAIPenalty("P8", -15, "Valid request but zero panel count"))
        score -= 15

    # ── Bonuses ──

    # B1: Alternative thickness provided when autoportancia exceeded
    if sre.get("r_autoportancia", 0) >= 30 and sre.get("alternative_thicknesses"):
        bonuses.append(SAIPenalty("B1", 5, "Alternative thickness suggested"))
        score += 5

    # B2: Complete client data
    client = request.get("client", {})
    if client.get("name") and client.get("phone") and client.get("location"):
        bonuses.append(SAIPenalty("B2", 2, "Complete client data"))
        score += 2

    # B3: Low SRE risk
    if sre.get("score", 100) <= 15:
        bonuses.append(SAIPenalty("B3", 3, "Very low structural risk"))
        score += 3

    score = max(0.0, min(100.0, score))
    target = _get_target(mode)

    return SAIResult(
        score=round(score, 1),
        grade=_grade(score),
        passed=score >= target,
        target=target,
        penalties=penalties,
        bonuses=bonuses,
    )


def calculate_batch_sai(outputs: list[QuotationOutput]) -> dict:
    """Calculate SAI statistics for a batch of quotations.

    Returns:
        Summary with average, min, max, pass rate, and individual results.
    """
    if not outputs:
        return {"average": 0, "min": 0, "max": 0, "pass_rate": 0, "count": 0, "results": []}

    results = [calculate_sai(o) for o in outputs]
    scores = [r.score for r in results]

    passed = sum(1 for r in results if r.passed)

    return {
        "average": round(sum(scores) / len(scores), 1),
        "min": round(min(scores), 1),
        "max": round(max(scores), 1),
        "pass_rate": round(passed / len(results) * 100, 1),
        "count": len(results),
        "grade_distribution": {
            "A": sum(1 for r in results if r.grade == "A"),
            "B": sum(1 for r in results if r.grade == "B"),
            "C": sum(1 for r in results if r.grade == "C"),
            "D": sum(1 for r in results if r.grade == "D"),
            "F": sum(1 for r in results if r.grade == "F"),
        },
        "results": [r.to_dict() for r in results],
    }
