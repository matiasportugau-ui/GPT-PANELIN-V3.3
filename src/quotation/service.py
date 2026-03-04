"""
Panelin v5.0 — Quotation Service
==================================

Thin wrapper around the deterministic panelin_v4 engine pipeline.
Provides a clean interface for the Agno workflow steps.
"""

from __future__ import annotations

from typing import Optional

from panelin_v4.engine.classifier import (
    ClassificationResult,
    OperatingMode,
    classify_request,
)
from panelin_v4.engine.parser import QuoteRequest, parse_request
from panelin_v4.engine.sre_engine import SREResult, calculate_sre
from panelin_v4.engine.bom_engine import BOMResult, calculate_bom
from panelin_v4.engine.pricing_engine import PricingResult, calculate_pricing
from panelin_v4.engine.validation_engine import ValidationResult, validate_quotation
from panelin_v4.engine.quotation_engine import (
    QuotationOutput,
    _apply_defaults,
    process_quotation,
    process_batch,
)
from panelin_v4.evaluator.sai_engine import SAIResult, calculate_sai


class QuotationService:
    """Stateless service wrapping the panelin_v4 engine pipeline.

    Each method maps to a pipeline stage and returns typed results.
    All methods are synchronous and deterministic (no LLM calls).
    """

    @staticmethod
    def classify(text: str, force_mode: Optional[OperatingMode] = None) -> ClassificationResult:
        return classify_request(text, force_mode=force_mode)

    @staticmethod
    def parse(text: str) -> QuoteRequest:
        return parse_request(text)

    @staticmethod
    def apply_defaults(request: QuoteRequest, mode: OperatingMode) -> list[str]:
        return _apply_defaults(request, mode)

    @staticmethod
    def calculate_sre(request: QuoteRequest) -> SREResult:
        return calculate_sre(request)

    @staticmethod
    def calculate_bom(
        request: QuoteRequest,
    ) -> BOMResult:
        if not _can_calculate_bom(request):
            return BOMResult(
                system_key="unknown",
                area_m2=0,
                panel_count=0,
                supports_per_panel=0,
                fixation_points=0,
                warnings=["Insufficient data for BOM calculation"],
            )

        length_m = request.geometry.length_m or 0
        width_m = request.geometry.width_m or 0
        if not width_m and request.geometry.panel_count:
            width_m = request.geometry.panel_count * 1.12
        if length_m <= 0 or width_m <= 0:
            return BOMResult(
                system_key="unknown",
                area_m2=0,
                panel_count=0,
                supports_per_panel=0,
                fixation_points=0,
                warnings=["Invalid dimensions for BOM"],
            )

        return calculate_bom(
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

    @staticmethod
    def calculate_pricing(
        bom: BOMResult,
        request: QuoteRequest,
    ) -> PricingResult:
        if bom.panel_count <= 0 or not request.familia or not request.thickness_mm:
            return PricingResult()
        return calculate_pricing(
            bom=bom,
            familia=request.familia,
            sub_familia=request.sub_familia or "EPS",
            thickness_mm=request.thickness_mm,
            panel_area_m2=bom.area_m2,
            iva_mode=request.iva_mode,
        )

    @staticmethod
    def validate(
        request: QuoteRequest,
        sre: SREResult,
        bom: BOMResult,
        pricing: PricingResult,
        mode: OperatingMode,
    ) -> ValidationResult:
        return validate_quotation(
            request=request,
            sre=sre,
            bom=bom,
            pricing=pricing,
            mode=mode,
        )

    @staticmethod
    def calculate_sai(output: QuotationOutput) -> SAIResult:
        return calculate_sai(output)

    @staticmethod
    def process_full(
        text: str,
        force_mode: Optional[OperatingMode] = None,
        client_name: Optional[str] = None,
        client_phone: Optional[str] = None,
        client_location: Optional[str] = None,
    ) -> QuotationOutput:
        """Run the complete pipeline in one call."""
        return process_quotation(
            text=text,
            force_mode=force_mode,
            client_name=client_name,
            client_phone=client_phone,
            client_location=client_location,
        )

    @staticmethod
    def process_batch(
        requests: list[dict],
        force_mode: Optional[OperatingMode] = None,
    ) -> list[QuotationOutput]:
        return process_batch(requests, force_mode=force_mode)


def _can_calculate_bom(request: QuoteRequest) -> bool:
    return (
        request.familia is not None
        and request.thickness_mm is not None
        and request.uso is not None
        and (request.geometry.length_m is not None or bool(request.geometry.panel_lengths))
    )
