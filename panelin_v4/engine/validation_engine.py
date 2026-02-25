"""
Panelin v4.0 - Validation Engine
==================================

Multi-layer validation that classifies issues as OK / WARNING / CRITICAL.

NEVER blocks quotations in pre_cotizacion mode.
Only blocks in formal mode when CRITICAL issues are found.

Layers:
    A. Data Integrity: SKU exists, price exists, unit_base coherent
    B. Technical: Autoportancia, thickness compatible, accessories compatible
    C. Commercial: Shipping, fixings, sealants completeness
    D. Mathematical: Subtotal/total/IVA consistency
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from panelin_v4.engine.classifier import OperatingMode
from panelin_v4.engine.parser import QuoteRequest
from panelin_v4.engine.sre_engine import SREResult
from panelin_v4.engine.bom_engine import BOMResult
from panelin_v4.engine.pricing_engine import PricingResult


class Severity(str, Enum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    layer: str  # A=integrity, B=technical, C=commercial, D=math
    severity: Severity
    code: str
    message: str
    field: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "layer": self.layer,
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "field": self.field,
        }


@dataclass
class ValidationResult:
    is_valid: bool
    can_emit_formal: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    autoportancia_status: str = "unknown"  # validated | not_verified | not_applicable | exceeded

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "can_emit_formal": self.can_emit_formal,
            "autoportancia_status": self.autoportancia_status,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "issues": [i.to_dict() for i in self.issues],
        }


def validate_quotation(
    request: QuoteRequest,
    sre: SREResult,
    bom: BOMResult,
    pricing: PricingResult,
    mode: OperatingMode,
) -> ValidationResult:
    """Run all validation layers and produce a combined result.

    In pre_cotizacion mode: CRITICAL issues become WARNINGs (non-blocking).
    In formal mode: CRITICAL issues prevent formal emission.
    """
    issues: list[ValidationIssue] = []
    autoportancia_status = "unknown"

    # ── Layer A: Data Integrity ──
    if not request.familia:
        issues.append(ValidationIssue(
            layer="A", severity=Severity.CRITICAL, code="A001",
            message="Product family not identified",
            field="familia",
        ))

    if not request.thickness_mm:
        issues.append(ValidationIssue(
            layer="A", severity=Severity.CRITICAL, code="A002",
            message="Panel thickness not specified",
            field="thickness_mm",
        ))

    if pricing.missing_prices:
        for mp in pricing.missing_prices:
            issues.append(ValidationIssue(
                layer="A", severity=Severity.WARNING, code="A003",
                message=f"Price not found: {mp}",
            ))

    # ── Layer B: Technical ──
    if request.uso in ("techo",) and request.span_m is None:
        if mode == OperatingMode.FORMAL:
            issues.append(ValidationIssue(
                layer="B", severity=Severity.CRITICAL, code="B001",
                message="Span (luz entre apoyos) required for formal roof quotation",
                field="span_m",
            ))
        else:
            issues.append(ValidationIssue(
                layer="B", severity=Severity.WARNING, code="B001",
                message="Span not provided. Pre-quotation uses default assumptions.",
                field="span_m",
            ))
            autoportancia_status = "not_verified"

    if sre.r_autoportancia >= 50:
        issues.append(ValidationIssue(
            layer="B", severity=Severity.CRITICAL, code="B002",
            message=f"Span exceeds autoportancia capacity. Alternatives: {sre.alternative_thicknesses}",
            field="autoportancia",
        ))
        autoportancia_status = "exceeded"
    elif sre.r_autoportancia >= 30:
        issues.append(ValidationIssue(
            layer="B", severity=Severity.WARNING, code="B003",
            message="Span near autoportancia limit. Verify with engineering.",
            field="autoportancia",
        ))
        autoportancia_status = "near_limit"
    elif request.span_m is not None and request.thickness_mm:
        autoportancia_status = "validated"

    if request.uso == "pared":
        autoportancia_status = "not_applicable"

    if bom.warnings:
        for w in bom.warnings:
            issues.append(ValidationIssue(
                layer="B", severity=Severity.WARNING, code="B004",
                message=w,
            ))

    # ── Layer C: Commercial ──
    if request.include_shipping and not request.client.location:
        issues.append(ValidationIssue(
            layer="C", severity=Severity.WARNING, code="C001",
            message="Shipping requested but location not specified",
            field="location",
        ))

    if request.uso == "techo" and not request.include_accessories:
        issues.append(ValidationIssue(
            layer="C", severity=Severity.WARNING, code="C002",
            message="Roof quotation without accessories may be incomplete",
        ))

    # ── Layer D: Mathematical ──
    if pricing.subtotal_total_usd <= 0 and not pricing.missing_prices:
        issues.append(ValidationIssue(
            layer="D", severity=Severity.CRITICAL, code="D001",
            message="Total is zero or negative despite having prices",
        ))

    expected_total = round(
        pricing.subtotal_panels_usd + pricing.subtotal_accessories_usd, 2
    )
    if abs(pricing.subtotal_total_usd - expected_total) > 0.02:
        issues.append(ValidationIssue(
            layer="D", severity=Severity.CRITICAL, code="D002",
            message=f"Total mismatch: {pricing.subtotal_total_usd} vs expected {expected_total}",
        ))

    # ── Determine validity ──
    if mode == OperatingMode.PRE_COTIZACION:
        # Downgrade CRITICALs to WARNINGs in pre mode (except math errors)
        for issue in issues:
            if issue.severity == Severity.CRITICAL and issue.layer != "D":
                issue.severity = Severity.WARNING
                issue.message += " [downgraded in pre_cotizacion mode]"

    critical_count = sum(1 for i in issues if i.severity == Severity.CRITICAL)
    is_valid = critical_count == 0
    can_emit_formal = is_valid and mode == OperatingMode.FORMAL

    return ValidationResult(
        is_valid=is_valid,
        can_emit_formal=can_emit_formal,
        issues=issues,
        autoportancia_status=autoportancia_status,
    )
