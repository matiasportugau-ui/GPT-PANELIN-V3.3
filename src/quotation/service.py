from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from panelin_v4.engine.bom_engine import BOMResult, calculate_bom
from panelin_v4.engine.classifier import (
    ClassificationResult,
    OperatingMode,
    RequestType,
    classify_request,
)
from panelin_v4.engine.parser import QuoteRequest, parse_request
from panelin_v4.engine.pricing_engine import PricingResult, calculate_pricing
from panelin_v4.engine.quotation_engine import (
    QuotationOutput,
    _apply_defaults,
    _calculate_confidence,
    _determine_status,
    process_batch,
    process_quotation,
)
from panelin_v4.engine.sre_engine import SREResult, calculate_sre
from panelin_v4.engine.validation_engine import ValidationResult, validate_quotation
from panelin_v4.evaluator.sai_engine import SAIResult, calculate_sai


class QuotationService:
    """Servicio de dominio que encapsula el engine v4 deterministico."""

    def classify(self, text: str, force_mode: Optional[OperatingMode] = None) -> ClassificationResult:
        return classify_request(text, force_mode=force_mode)

    def parse(self, text: str) -> QuoteRequest:
        return parse_request(text)

    def inject_client_data(
        self,
        request: QuoteRequest,
        *,
        client_name: Optional[str] = None,
        client_phone: Optional[str] = None,
        client_location: Optional[str] = None,
    ) -> None:
        if client_name:
            request.client.name = client_name
        if client_phone:
            request.client.phone = client_phone
        if client_location:
            request.client.location = client_location

    def apply_defaults(self, request: QuoteRequest, mode: OperatingMode) -> list[str]:
        assumptions = _apply_defaults(request, mode)
        request.assumptions_used.extend(assumptions)
        return assumptions

    def sre(self, request: QuoteRequest) -> SREResult:
        return calculate_sre(request)

    @staticmethod
    def empty_bom() -> BOMResult:
        return BOMResult(
            system_key="unknown",
            area_m2=0,
            panel_count=0,
            supports_per_panel=0,
            fixation_points=0,
        )

    @staticmethod
    def empty_pricing() -> PricingResult:
        return PricingResult()

    def can_calculate_bom(self, request: QuoteRequest) -> bool:
        return (
            request.familia is not None
            and request.thickness_mm is not None
            and request.uso is not None
            and (request.geometry.length_m is not None or request.geometry.panel_lengths)
        )

    def bom(self, request: QuoteRequest) -> BOMResult:
        if not self.can_calculate_bom(request):
            return self.empty_bom()

        length_m = request.geometry.length_m or 0
        width_m = request.geometry.width_m or 0
        if not width_m and request.geometry.panel_count:
            width_m = request.geometry.panel_count * 1.12

        if length_m <= 0 or width_m <= 0:
            return self.empty_bom()

        return calculate_bom(
            familia=request.familia or "ISODEC",
            sub_familia=request.sub_familia or "EPS",
            thickness_mm=request.thickness_mm or 100,
            uso=request.uso or "techo",
            length_m=length_m,
            width_m=width_m,
            structure_type=request.structure_type or "metal",
            panel_count=request.geometry.panel_count,
            panel_lengths=request.geometry.panel_lengths or None,
            roof_type=request.roof_type,
            span_m=request.span_m,
        )

    def pricing(self, request: QuoteRequest, bom: BOMResult) -> PricingResult:
        if bom.panel_count <= 0 or not request.familia or not request.thickness_mm:
            return self.empty_pricing()

        return calculate_pricing(
            bom=bom,
            familia=request.familia,
            sub_familia=request.sub_familia or "EPS",
            thickness_mm=request.thickness_mm,
            panel_area_m2=bom.area_m2,
            iva_mode=request.iva_mode,
        )

    def validation(
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
        *,
        classification: ClassificationResult,
        request: QuoteRequest,
        sre: SREResult,
        bom: BOMResult,
        pricing: PricingResult,
        validation: ValidationResult,
        assumptions: list[str] | None = None,
    ) -> QuotationOutput:
        mode = classification.operating_mode
        confidence = _calculate_confidence(request, sre, validation, pricing)
        status = _determine_status(mode, sre, validation)
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

    def sai(self, output: QuotationOutput) -> SAIResult:
        return calculate_sai(output)

    def process(
        self,
        text: str,
        force_mode: Optional[OperatingMode] = None,
        client_name: Optional[str] = None,
        client_phone: Optional[str] = None,
        client_location: Optional[str] = None,
    ) -> QuotationOutput:
        return process_quotation(
            text=text,
            force_mode=force_mode,
            client_name=client_name,
            client_phone=client_phone,
            client_location=client_location,
        )

    def process_batch(self, requests: list[dict], force_mode: Optional[OperatingMode] = None) -> list[QuotationOutput]:
        return process_batch(requests=requests, force_mode=force_mode)
