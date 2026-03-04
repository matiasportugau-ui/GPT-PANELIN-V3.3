"""Domain service layer for deterministic Panelin quotations."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from panelin_v4.engine.bom_engine import BOMItem, BOMResult, calculate_bom
from panelin_v4.engine.classifier import (
    ClassificationResult,
    OperatingMode,
    RequestType,
    classify_request,
)
from panelin_v4.engine.parser import ClientInfo, ProjectGeometry, QuoteRequest, parse_request
from panelin_v4.engine.pricing_engine import PricedItem, PricingResult, calculate_pricing
from panelin_v4.engine.quotation_engine import (
    QuotationOutput,
    _apply_defaults,
    _calculate_confidence,
    _determine_status,
    process_quotation,
)
from panelin_v4.engine.sre_engine import QuotationLevel, SREResult, calculate_sre
from panelin_v4.engine.validation_engine import (
    Severity,
    ValidationIssue,
    ValidationResult,
    validate_quotation,
)
from panelin_v4.evaluator.sai_engine import SAIResult, SAIPenalty, calculate_sai


MODE_MAP: dict[str, OperatingMode] = {
    "informativo": OperatingMode.INFORMATIVO,
    "pre_cotizacion": OperatingMode.PRE_COTIZACION,
    "formal": OperatingMode.FORMAL,
}


class QuotationService:
    """Encapsulates deterministic v4 domain logic for Agno components."""

    def resolve_mode(self, raw_mode: str | None) -> OperatingMode:
        mode_key = (raw_mode or "pre_cotizacion").strip().lower()
        if mode_key not in MODE_MAP:
            valid_modes = ", ".join(sorted(MODE_MAP.keys()))
            raise ValueError(f"Invalid mode '{raw_mode}'. Valid options: {valid_modes}")
        return MODE_MAP[mode_key]

    def classify(self, text: str, mode: OperatingMode | None = None) -> ClassificationResult:
        return classify_request(text=text, force_mode=mode)

    def parse(self, text: str) -> QuoteRequest:
        return parse_request(text)

    def enrich_request(
        self,
        request: QuoteRequest,
        mode: OperatingMode,
        client_name: str | None = None,
        client_phone: str | None = None,
        client_location: str | None = None,
    ) -> QuoteRequest:
        if client_name:
            request.client.name = client_name
        if client_phone:
            request.client.phone = client_phone
        if client_location:
            request.client.location = client_location
        assumptions = _apply_defaults(request, mode)
        request.assumptions_used.extend(assumptions)
        return request

    def calculate_sre(self, request: QuoteRequest) -> SREResult:
        return calculate_sre(request)

    def calculate_bom(self, request: QuoteRequest) -> BOMResult:
        can_calculate_bom = (
            request.familia is not None
            and request.thickness_mm is not None
            and request.uso is not None
            and (request.geometry.length_m is not None or request.geometry.panel_lengths)
        )
        if not can_calculate_bom:
            return BOMResult(
                system_key="unknown",
                area_m2=0,
                panel_count=0,
                supports_per_panel=0,
                fixation_points=0,
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
    ) -> QuotationOutput:
        mode = classification.operating_mode
        confidence = _calculate_confidence(request, sre, validation, pricing)
        status = _determine_status(mode, sre, validation)
        quote_id = f"PV5-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        notes: list[str] = []
        if mode == OperatingMode.PRE_COTIZACION and request.assumptions_used:
            notes.append(
                "Pre-cotización con supuestos automáticos. Requiere confirmación antes de emitir formal."
            )
        if classification.request_type == RequestType.ACCESSORIES_ONLY:
            notes.append("Solicitud de accesorios: se omite validación estructural de paneles.")

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
        mode: str | None = None,
        client_name: str | None = None,
        client_phone: str | None = None,
        client_location: str | None = None,
    ) -> QuotationOutput:
        force_mode = self.resolve_mode(mode) if mode else None
        return process_quotation(
            text=text,
            force_mode=force_mode,
            client_name=client_name,
            client_phone=client_phone,
            client_location=client_location,
        )

    def process_to_dict(
        self,
        text: str,
        mode: str | None = None,
        client_name: str | None = None,
        client_phone: str | None = None,
        client_location: str | None = None,
    ) -> dict:
        return self.process(
            text=text,
            mode=mode,
            client_name=client_name,
            client_phone=client_phone,
            client_location=client_location,
        ).to_dict()

    def calculate_sai(self, output: QuotationOutput) -> SAIResult:
        return calculate_sai(output)

    # ---- Serialization helpers for workflow state ----

    def classification_from_dict(self, data: dict) -> ClassificationResult:
        return ClassificationResult(
            request_type=RequestType(data["request_type"]),
            operating_mode=OperatingMode(data["operating_mode"]),
            has_roof=bool(data.get("has_roof", False)),
            has_wall=bool(data.get("has_wall", False)),
            has_accessories=bool(data.get("has_accessories", False)),
            is_update=bool(data.get("is_update", False)),
            confidence=float(data.get("confidence", 0)),
            signals=list(data.get("signals", [])),
        )

    def request_from_dict(self, data: dict) -> QuoteRequest:
        geometry_data = data.get("geometry", {})
        client_data = data.get("client", {})
        geometry = ProjectGeometry(
            length_m=geometry_data.get("length_m"),
            width_m=geometry_data.get("width_m"),
            height_m=geometry_data.get("height_m"),
            panel_count=geometry_data.get("panel_count"),
            panel_lengths=list(geometry_data.get("panel_lengths", [])),
        )
        client = ClientInfo(
            name=client_data.get("name"),
            phone=client_data.get("phone"),
            location=client_data.get("location"),
        )
        return QuoteRequest(
            familia=data.get("familia"),
            sub_familia=data.get("sub_familia"),
            thickness_mm=data.get("thickness_mm"),
            uso=data.get("uso"),
            structure_type=data.get("structure_type"),
            span_m=data.get("span_m"),
            geometry=geometry,
            client=client,
            include_accessories=bool(data.get("include_accessories", True)),
            include_fixings=bool(data.get("include_fixings", True)),
            include_shipping=bool(data.get("include_shipping", False)),
            iva_mode=data.get("iva_mode", "incluido"),
            roof_type=data.get("roof_type"),
            raw_accessories_requested=list(data.get("raw_accessories_requested", [])),
            raw_text=data.get("raw_text", ""),
            incomplete_fields=list(data.get("incomplete_fields", [])),
            assumptions_used=list(data.get("assumptions_used", [])),
        )

    def sre_from_dict(self, data: dict) -> SREResult:
        return SREResult(
            score=int(data.get("score", 0)),
            level=QuotationLevel(data.get("level", QuotationLevel.LEVEL_1_COMMERCIAL.value)),
            r_datos=int(data.get("r_datos", 0)),
            r_autoportancia=int(data.get("r_autoportancia", 0)),
            r_geometria=int(data.get("r_geometria", 0)),
            r_sistema=int(data.get("r_sistema", 0)),
            breakdown=list(data.get("breakdown", [])),
            recommendations=list(data.get("recommendations", [])),
            alternative_thicknesses=list(data.get("alternative_thicknesses", [])),
        )

    def bom_from_dict(self, data: dict) -> BOMResult:
        items = [
            BOMItem(
                tipo=item.get("tipo", ""),
                referencia=item.get("referencia", ""),
                sku=item.get("sku"),
                name=item.get("name"),
                quantity=int(item.get("quantity", 0)),
                unit=item.get("unit", "unid"),
                formula_used=item.get("formula_used", ""),
                notes=item.get("notes", ""),
            )
            for item in data.get("items", [])
        ]
        return BOMResult(
            system_key=data.get("system_key", "unknown"),
            area_m2=float(data.get("area_m2", 0)),
            panel_count=int(data.get("panel_count", 0)),
            supports_per_panel=int(data.get("supports_per_panel", 0)),
            fixation_points=int(data.get("fixation_points", 0)),
            items=items,
            warnings=list(data.get("warnings", [])),
        )

    def pricing_from_dict(self, data: dict) -> PricingResult:
        items = [
            PricedItem(
                tipo=item.get("tipo", ""),
                sku=item.get("sku"),
                name=item.get("name"),
                quantity=int(item.get("quantity", 0)),
                unit=item.get("unit", "unid"),
                unit_price_usd=float(item.get("unit_price_usd", 0)),
                subtotal_usd=float(item.get("subtotal_usd", 0)),
                price_source=item.get("price_source", "accessories_catalog"),
                price_includes_iva=bool(item.get("price_includes_iva", True)),
            )
            for item in data.get("items", [])
        ]
        return PricingResult(
            items=items,
            subtotal_panels_usd=float(data.get("subtotal_panels_usd", 0)),
            subtotal_accessories_usd=float(data.get("subtotal_accessories_usd", 0)),
            subtotal_total_usd=float(data.get("subtotal_total_usd", 0)),
            iva_mode=data.get("iva_mode", "incluido"),
            warnings=list(data.get("warnings", [])),
            missing_prices=list(data.get("missing_prices", [])),
        )

    def validation_from_dict(self, data: dict) -> ValidationResult:
        issues = [
            ValidationIssue(
                layer=issue.get("layer", "A"),
                severity=Severity(issue.get("severity", Severity.WARNING.value)),
                code=issue.get("code", "UNKNOWN"),
                message=issue.get("message", ""),
                field=issue.get("field"),
            )
            for issue in data.get("issues", [])
        ]
        return ValidationResult(
            is_valid=bool(data.get("is_valid", False)),
            can_emit_formal=bool(data.get("can_emit_formal", False)),
            issues=issues,
            autoportancia_status=data.get("autoportancia_status", "unknown"),
        )

    def output_from_dict(self, data: dict) -> QuotationOutput:
        return QuotationOutput(
            quote_id=data.get("quote_id", ""),
            timestamp=data.get("timestamp", ""),
            mode=data.get("mode", OperatingMode.PRE_COTIZACION.value),
            level=data.get("level", QuotationLevel.LEVEL_1_COMMERCIAL.value),
            status=data.get("status", "draft"),
            classification=dict(data.get("classification", {})),
            request=dict(data.get("request", {})),
            sre=dict(data.get("sre", {})),
            bom=dict(data.get("bom", {})),
            pricing=dict(data.get("pricing", {})),
            validation=dict(data.get("validation", {})),
            assumptions_used=list(data.get("assumptions_used", [])),
            confidence_score=float(data.get("confidence_score", 0)),
            processing_notes=list(data.get("processing_notes", [])),
        )

    def sai_from_dict(self, data: dict) -> SAIResult:
        penalties = [
            SAIPenalty(
                code=item.get("code", ""),
                points=int(item.get("points", 0)),
                description=item.get("description", ""),
            )
            for item in data.get("penalties", [])
        ]
        bonuses = [
            SAIPenalty(
                code=item.get("code", ""),
                points=int(item.get("points", 0)),
                description=item.get("description", ""),
            )
            for item in data.get("bonuses", [])
        ]
        return SAIResult(
            score=float(data.get("score", 0)),
            grade=data.get("grade", "F"),
            passed=bool(data.get("passed", False)),
            target=float(data.get("target", 0)),
            penalties=penalties,
            bonuses=bonuses,
        )
