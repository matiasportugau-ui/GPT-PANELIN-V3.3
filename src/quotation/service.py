"""Domain service layer wrapping the deterministic Panelin v4 engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
import uuid

from panelin_v4.engine.classifier import (
    ClassificationResult,
    OperatingMode,
    RequestType,
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
    _calculate_confidence,
    _determine_status,
)
from panelin_v4.evaluator.sai_engine import SAIResult, calculate_sai


@dataclass
class PipelineArtifacts:
    classification: ClassificationResult
    request: QuoteRequest
    sre: SREResult
    bom: BOMResult
    pricing: PricingResult
    validation: ValidationResult
    output: QuotationOutput
    sai: SAIResult


class QuotationService:
    """Application service for quotation orchestration without LLM in the pipeline."""

    MODE_MAP: dict[str, OperatingMode] = {
        "informativo": OperatingMode.INFORMATIVO,
        "pre_cotizacion": OperatingMode.PRE_COTIZACION,
        "formal": OperatingMode.FORMAL,
    }

    def resolve_mode(self, raw_mode: str | OperatingMode | None) -> OperatingMode:
        if isinstance(raw_mode, OperatingMode):
            return raw_mode
        mode_key = (raw_mode or "pre_cotizacion").strip().lower()
        return self.MODE_MAP.get(mode_key, OperatingMode.PRE_COTIZACION)

    def classify(self, text: str, mode: str | OperatingMode | None = None) -> ClassificationResult:
        force_mode = self.resolve_mode(mode) if mode else None
        return classify_request(text, force_mode=force_mode)

    def parse(self, text: str) -> QuoteRequest:
        return parse_request(text)

    def apply_defaults(self, request: QuoteRequest, mode: OperatingMode) -> list[str]:
        assumptions = _apply_defaults(request, mode)
        request.assumptions_used.extend(assumptions)
        return assumptions

    def inject_client_data(
        self,
        request: QuoteRequest,
        client_name: str | None = None,
        client_phone: str | None = None,
        client_location: str | None = None,
    ) -> None:
        if client_name:
            request.client.name = client_name
        if client_phone:
            request.client.phone = client_phone
        if client_location:
            request.client.location = client_location

    def calculate_sre(self, request: QuoteRequest) -> SREResult:
        return calculate_sre(request)

    @staticmethod
    def empty_bom(reason: str) -> BOMResult:
        return BOMResult(
            system_key="skipped",
            area_m2=0,
            panel_count=0,
            supports_per_panel=0,
            fixation_points=0,
            warnings=[reason],
        )

    def calculate_bom(self, request: QuoteRequest) -> BOMResult:
        can_calculate_bom = (
            request.familia is not None
            and request.thickness_mm is not None
            and request.uso is not None
            and (request.geometry.length_m is not None or request.geometry.panel_lengths)
        )
        if not can_calculate_bom:
            return self.empty_bom("Insufficient data to calculate BOM")

        length_m = request.geometry.length_m or 0.0
        width_m = request.geometry.width_m or 0.0

        if not width_m and request.geometry.panel_count:
            width_m = request.geometry.panel_count * 1.12

        if length_m <= 0 or width_m <= 0:
            return self.empty_bom("Missing or invalid geometry dimensions for BOM")

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

    def calculate_pricing(self, request: QuoteRequest, bom: BOMResult) -> PricingResult:
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

    def validate(
        self,
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

    def build_output(
        self,
        classification: ClassificationResult,
        request: QuoteRequest,
        sre: SREResult,
        bom: BOMResult,
        pricing: PricingResult,
        validation: ValidationResult,
        mode: OperatingMode,
    ) -> QuotationOutput:
        quote_id = f"PV4-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        confidence = _calculate_confidence(request, sre, validation, pricing)
        status = _determine_status(mode, sre, validation)

        notes: list[str] = []
        if mode == OperatingMode.PRE_COTIZACION and request.assumptions_used:
            notes.append("Pre-quotation with assumptions. Requires confirmation for formal emission.")
        if classification.request_type == RequestType.UPDATE:
            notes.append("Update request detected. Recalculate differential values.")
        if classification.request_type == RequestType.ACCESSORIES_ONLY:
            notes.append("Accessories-only request. Structural validation skipped.")

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

    def process(
        self,
        text: str,
        mode: str | OperatingMode | None = None,
        client_name: str | None = None,
        client_phone: str | None = None,
        client_location: str | None = None,
        skip_bom: bool = False,
    ) -> PipelineArtifacts:
        classification = self.classify(text, mode)
        resolved_mode = classification.operating_mode if mode is None else self.resolve_mode(mode)
        request = self.parse(text)
        self.inject_client_data(request, client_name, client_phone, client_location)
        self.apply_defaults(request, resolved_mode)

        sre = self.calculate_sre(request)
        bom = self.empty_bom("BOM skipped by route policy") if skip_bom else self.calculate_bom(request)
        pricing = self.calculate_pricing(request, bom)
        validation = self.validate(request, sre, bom, pricing, resolved_mode)
        output = self.build_output(classification, request, sre, bom, pricing, validation, resolved_mode)
        sai = calculate_sai(output)

        return PipelineArtifacts(
            classification=classification,
            request=request,
            sre=sre,
            bom=bom,
            pricing=pricing,
            validation=validation,
            output=output,
            sai=sai,
        )

    @staticmethod
    def response_payload(output: QuotationOutput, sai: SAIResult) -> dict[str, Any]:
        return {
            "quote_id": output.quote_id,
            "status": output.status,
            "mode": output.mode,
            "level": output.level,
            "confidence_score": output.confidence_score,
            "sai": sai.to_dict(),
            "quotation": output.to_dict(),
        }
