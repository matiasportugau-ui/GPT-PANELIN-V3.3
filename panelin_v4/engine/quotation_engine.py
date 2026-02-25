"""
Panelin v4.0 - Quotation Orchestrator
========================================

Central orchestrator that coordinates all engines in the pipeline:

    INPUT TEXT
        ↓
    classifier  →  Determines type & mode
        ↓
    parser      →  Structures data
        ↓
    sre_engine  →  Calculates risk score
        ↓
    bom_engine  →  Generates BOM
        ↓
    pricing     →  Values BOM items
        ↓
    validation  →  Multi-layer checks
        ↓
    OUTPUT      →  Structured quotation result

The orchestrator applies default assumptions when data is missing
in pre_cotizacion mode, and records every assumption used.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from panelin_v4.engine.classifier import (
    ClassificationResult, OperatingMode, RequestType,
    classify_request,
)
from panelin_v4.engine.parser import QuoteRequest, parse_request
from panelin_v4.engine.sre_engine import SREResult, QuotationLevel, calculate_sre
from panelin_v4.engine.bom_engine import BOMResult, calculate_bom
from panelin_v4.engine.pricing_engine import PricingResult, calculate_pricing
from panelin_v4.engine.validation_engine import ValidationResult, validate_quotation


@dataclass
class QuotationOutput:
    """Complete output of the quotation pipeline."""
    quote_id: str
    timestamp: str
    mode: str
    level: str
    status: str  # draft | validated | requires_review | blocked

    classification: dict = field(default_factory=dict)
    request: dict = field(default_factory=dict)
    sre: dict = field(default_factory=dict)
    bom: dict = field(default_factory=dict)
    pricing: dict = field(default_factory=dict)
    validation: dict = field(default_factory=dict)

    assumptions_used: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    processing_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "quote_id": self.quote_id,
            "timestamp": self.timestamp,
            "mode": self.mode,
            "level": self.level,
            "status": self.status,
            "classification": self.classification,
            "request": self.request,
            "sre": self.sre,
            "bom": self.bom,
            "pricing": self.pricing,
            "validation": self.validation,
            "assumptions_used": self.assumptions_used,
            "confidence_score": self.confidence_score,
            "processing_notes": self.processing_notes,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


_DEFAULTS_CACHE: Optional[dict] = None


def _load_defaults() -> dict:
    global _DEFAULTS_CACHE
    if _DEFAULTS_CACHE is None:
        path = Path(__file__).resolve().parent.parent / "data" / "default_assumptions.json"
        with open(path, encoding="utf-8") as f:
            _DEFAULTS_CACHE = json.load(f)
    return _DEFAULTS_CACHE


def _apply_defaults(req: QuoteRequest, mode: OperatingMode) -> list[str]:
    """Apply default assumptions for missing data in non-formal modes.

    Returns list of assumption descriptions for audit trail.
    """
    if mode == OperatingMode.FORMAL:
        return []

    defaults = _load_defaults()
    assumptions: list[str] = []

    if req.uso in ("techo",) and req.span_m is None:
        default_span = defaults.get("span_defaults", {}).get("default", 1.5)
        req.span_m = default_span
        assumptions.append(f"span_m assumed {default_span}m (residential default)")

    if not req.structure_type:
        uso_key = req.uso or "techo"
        default_struct = defaults.get("structure_defaults", {}).get(uso_key, "metal")
        req.structure_type = default_struct
        assumptions.append(f"structure_type assumed '{default_struct}' for {uso_key}")

    if not req.geometry.width_m and req.geometry.panel_count:
        ancho_util = 1.12
        req.geometry.width_m = req.geometry.panel_count * ancho_util
        assumptions.append(
            f"width_m derived from panel_count ({req.geometry.panel_count}) × ancho_util ({ancho_util}m)"
        )

    return assumptions


def _calculate_confidence(
    req: QuoteRequest,
    sre: SREResult,
    validation: ValidationResult,
    pricing: PricingResult,
) -> float:
    """Calculate a confidence score (0-100) for the quotation."""
    score = 100.0

    # Penalize for incomplete data
    score -= len(req.incomplete_fields) * 8

    # Penalize for assumptions
    score -= len(req.assumptions_used) * 5

    # Penalize for SRE risk
    if sre.score > 60:
        score -= 20
    elif sre.score > 30:
        score -= 10

    # Penalize for validation issues
    score -= validation.critical_count * 15
    score -= validation.warning_count * 3

    # Penalize for missing prices
    score -= len(pricing.missing_prices) * 10

    return max(0.0, min(100.0, score))


def _determine_status(
    mode: OperatingMode,
    sre: SREResult,
    validation: ValidationResult,
) -> str:
    """Determine quotation status based on mode and validation results."""
    if validation.critical_count > 0 and mode == OperatingMode.FORMAL:
        return "blocked"
    if sre.level == QuotationLevel.TECHNICAL_BLOCK:
        return "requires_review"
    if validation.warning_count > 3:
        return "requires_review"
    if mode == OperatingMode.FORMAL and validation.can_emit_formal:
        return "validated"
    return "draft"


def process_quotation(
    text: str,
    force_mode: Optional[OperatingMode] = None,
    client_name: Optional[str] = None,
    client_phone: Optional[str] = None,
    client_location: Optional[str] = None,
) -> QuotationOutput:
    """Process a quotation request through the full pipeline.

    This is the main entry point for the Panelin v4.0 engine.

    Args:
        text: Raw quotation request in Spanish.
        force_mode: Override auto-detected operating mode.
        client_name: Client name (optional).
        client_phone: Client phone (optional).
        client_location: Client location (optional).

    Returns:
        QuotationOutput with complete pipeline results.
    """
    # Step 1: Classify
    classification = classify_request(text, force_mode=force_mode)
    mode = classification.operating_mode

    # Step 2: Parse
    request = parse_request(text)

    # Inject client info if provided externally
    if client_name:
        request.client.name = client_name
    if client_phone:
        request.client.phone = client_phone
    if client_location:
        request.client.location = client_location

    # Step 3: Apply defaults (only in non-formal mode)
    assumptions = _apply_defaults(request, mode)
    request.assumptions_used.extend(assumptions)

    # Step 4: Calculate SRE
    sre = calculate_sre(request)

    # Step 5: Calculate BOM (only if we have enough data)
    bom = BOMResult(
        system_key="unknown", area_m2=0, panel_count=0,
        supports_per_panel=0, fixation_points=0,
    )

    can_calculate_bom = (
        request.familia is not None
        and request.thickness_mm is not None
        and request.uso is not None
        and (request.geometry.length_m is not None or request.geometry.panel_lengths)
    )

    if can_calculate_bom:
        length_m = request.geometry.length_m or 0
        width_m = request.geometry.width_m or 0

        if not width_m and request.geometry.panel_count:
            width_m = request.geometry.panel_count * 1.12

        if length_m > 0 and width_m > 0:
            bom = calculate_bom(
                familia=request.familia,
                sub_familia=request.sub_familia or "EPS",
                thickness_mm=request.thickness_mm,
                uso=request.uso,
                length_m=length_m,
                width_m=width_m,
                structure_type=request.structure_type or "metal",
                panel_count=request.geometry.panel_count,
                panel_lengths=request.geometry.panel_lengths or None,
                roof_type=request.roof_type,
                span_m=request.span_m,
            )

    # Step 6: Calculate pricing
    pricing = PricingResult()
    if bom.panel_count > 0 and request.familia and request.thickness_mm:
        pricing = calculate_pricing(
            bom=bom,
            familia=request.familia,
            sub_familia=request.sub_familia or "EPS",
            thickness_mm=request.thickness_mm,
            panel_area_m2=bom.area_m2,
            iva_mode=request.iva_mode,
        )

    # Step 7: Validate
    validation = validate_quotation(
        request=request,
        sre=sre,
        bom=bom,
        pricing=pricing,
        mode=mode,
    )

    # Step 8: Calculate confidence & status
    confidence = _calculate_confidence(request, sre, validation, pricing)
    status = _determine_status(mode, sre, validation)

    # Step 9: Build output
    quote_id = f"PV4-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    notes: list[str] = []
    if mode == OperatingMode.PRE_COTIZACION and assumptions:
        notes.append("Pre-quotation with assumptions. Requires confirmation for formal emission.")
    if classification.request_type == RequestType.UPDATE:
        notes.append("Update request detected. Only recalculate differential.")
    if classification.request_type == RequestType.ACCESSORIES_ONLY:
        notes.append("Accessories-only request. No structural validation required.")

    return QuotationOutput(
        quote_id=quote_id,
        timestamp=datetime.now().isoformat(),
        mode=mode.value,
        level=sre.level.value,
        status=status,
        classification=classification.to_dict(),
        request=request.to_dict(),
        sre=sre.to_dict(),
        bom=bom.to_dict(),
        pricing=pricing.to_dict(),
        validation=validation.to_dict(),
        assumptions_used=request.assumptions_used,
        confidence_score=round(confidence, 1),
        processing_notes=notes,
    )


def process_batch(
    requests: list[dict],
    force_mode: Optional[OperatingMode] = None,
) -> list[QuotationOutput]:
    """Process multiple quotation requests in batch.

    Args:
        requests: List of dicts with at least 'text' key.
            Optional keys: 'client_name', 'client_phone', 'client_location'.
        force_mode: Override mode for all requests.

    Returns:
        List of QuotationOutput results.
    """
    results = []
    for req_dict in requests:
        text = req_dict.get("text", "")
        output = process_quotation(
            text=text,
            force_mode=force_mode,
            client_name=req_dict.get("client_name"),
            client_phone=req_dict.get("client_phone"),
            client_location=req_dict.get("client_location"),
        )
        results.append(output)
    return results
