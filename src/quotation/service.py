"""
Panelin Agno — QuotationService

Thin service layer over the panelin_v4 engine. Provides a clean API
for the Agno workflow steps to invoke without importing engine internals.
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
from panelin_v4.engine.quotation_engine import QuotationOutput, process_quotation, process_batch
from panelin_v4.evaluator.sai_engine import SAIResult, calculate_sai


class QuotationService:
    """Stateless service wrapping the panelin_v4 engine pipeline.

    Each method corresponds to one pipeline step. The Agno workflow
    calls them in sequence, passing results between steps via session state.
    """

    @staticmethod
    def classify(text: str, force_mode: Optional[str] = None) -> dict:
        mode = OperatingMode(force_mode) if force_mode else None
        result: ClassificationResult = classify_request(text, force_mode=mode)
        return result.to_dict()

    @staticmethod
    def parse(text: str) -> dict:
        result: QuoteRequest = parse_request(text)
        return result.to_dict()

    @staticmethod
    def calculate_sre(parsed: dict) -> dict:
        req = _dict_to_quote_request(parsed)
        result: SREResult = calculate_sre(req)
        return result.to_dict()

    @staticmethod
    def calculate_bom(parsed: dict) -> dict:
        req = _dict_to_quote_request(parsed)
        if not req.familia or not req.thickness_mm or not req.uso:
            return BOMResult(
                system_key="unknown", area_m2=0, panel_count=0,
                supports_per_panel=0, fixation_points=0,
                warnings=["Insufficient data for BOM calculation"],
            ).to_dict()

        length_m = req.geometry.length_m or 0
        width_m = req.geometry.width_m or 0
        if not width_m and req.geometry.panel_count:
            width_m = req.geometry.panel_count * 1.12
        if length_m <= 0 or width_m <= 0:
            return BOMResult(
                system_key="unknown", area_m2=0, panel_count=0,
                supports_per_panel=0, fixation_points=0,
                warnings=["Missing dimensions for BOM"],
            ).to_dict()

        result: BOMResult = calculate_bom(
            familia=req.familia,
            sub_familia=req.sub_familia or "EPS",
            thickness_mm=req.thickness_mm,
            uso=req.uso,
            length_m=length_m,
            width_m=width_m,
            structure_type=req.structure_type or "metal",
            panel_count=req.geometry.panel_count,
            panel_lengths=req.geometry.panel_lengths or None,
            roof_type=req.roof_type,
            span_m=req.span_m,
        )
        return result.to_dict()

    @staticmethod
    def calculate_pricing(bom_dict: dict, parsed: dict) -> dict:
        req = _dict_to_quote_request(parsed)
        if not bom_dict.get("panel_count"):
            return PricingResult().to_dict()

        bom = _dict_to_bom_result(bom_dict)
        result: PricingResult = calculate_pricing(
            bom=bom,
            familia=req.familia or "",
            sub_familia=req.sub_familia or "EPS",
            thickness_mm=req.thickness_mm or 0,
            panel_area_m2=bom.area_m2,
            iva_mode=req.iva_mode,
        )
        return result.to_dict()

    @staticmethod
    def validate(parsed: dict, sre_dict: dict, bom_dict: dict, pricing_dict: dict, mode: str) -> dict:
        from panelin_v4.engine.bom_engine import BOMItem

        req = _dict_to_quote_request(parsed)
        sre = _dict_to_sre_result(sre_dict)
        bom = _dict_to_bom_result(bom_dict)
        pricing = _dict_to_pricing_result(pricing_dict)
        op_mode = OperatingMode(mode)
        result: ValidationResult = validate_quotation(req, sre, bom, pricing, op_mode)
        return result.to_dict()

    @staticmethod
    def calculate_sai(output: QuotationOutput) -> dict:
        result: SAIResult = calculate_sai(output)
        return result.to_dict()

    @staticmethod
    def full_pipeline(text: str, force_mode: Optional[str] = None, **kwargs) -> dict:
        mode = OperatingMode(force_mode) if force_mode else None
        output: QuotationOutput = process_quotation(
            text=text,
            force_mode=mode,
            client_name=kwargs.get("client_name"),
            client_phone=kwargs.get("client_phone"),
            client_location=kwargs.get("client_location"),
        )
        return output.to_dict()

    @staticmethod
    def batch_pipeline(requests: list[dict], force_mode: Optional[str] = None) -> list[dict]:
        mode = OperatingMode(force_mode) if force_mode else None
        outputs = process_batch(requests, force_mode=mode)
        return [o.to_dict() for o in outputs]


def _dict_to_quote_request(d: dict) -> QuoteRequest:
    """Reconstruct QuoteRequest from dict for engine functions."""
    from panelin_v4.engine.parser import QuoteRequest, ProjectGeometry, ClientInfo

    geo = d.get("geometry", {})
    client = d.get("client", {})
    req = QuoteRequest(
        familia=d.get("familia"),
        sub_familia=d.get("sub_familia"),
        thickness_mm=d.get("thickness_mm"),
        uso=d.get("uso"),
        structure_type=d.get("structure_type"),
        span_m=d.get("span_m"),
        geometry=ProjectGeometry(
            length_m=geo.get("length_m"),
            width_m=geo.get("width_m"),
            height_m=geo.get("height_m"),
            panel_count=geo.get("panel_count"),
            panel_lengths=geo.get("panel_lengths", []),
        ),
        client=ClientInfo(
            name=client.get("name"),
            phone=client.get("phone"),
            location=client.get("location"),
        ),
        include_accessories=d.get("include_accessories", True),
        include_fixings=d.get("include_fixings", True),
        include_shipping=d.get("include_shipping", False),
        iva_mode=d.get("iva_mode", "incluido"),
        roof_type=d.get("roof_type"),
        raw_accessories_requested=d.get("raw_accessories_requested", []),
        raw_text=d.get("raw_text", ""),
        incomplete_fields=d.get("incomplete_fields", []),
        assumptions_used=d.get("assumptions_used", []),
    )
    return req


def _dict_to_bom_result(d: dict) -> BOMResult:
    from panelin_v4.engine.bom_engine import BOMResult, BOMItem

    items = [
        BOMItem(
            tipo=i.get("tipo", ""),
            referencia=i.get("referencia", ""),
            sku=i.get("sku"),
            name=i.get("name"),
            quantity=i.get("quantity", 0),
            unit=i.get("unit", "unid"),
            formula_used=i.get("formula_used", ""),
            notes=i.get("notes", ""),
        )
        for i in d.get("items", [])
    ]
    return BOMResult(
        system_key=d.get("system_key", "unknown"),
        area_m2=d.get("area_m2", 0),
        panel_count=d.get("panel_count", 0),
        supports_per_panel=d.get("supports_per_panel", 0),
        fixation_points=d.get("fixation_points", 0),
        items=items,
        warnings=d.get("warnings", []),
    )


def _dict_to_sre_result(d: dict) -> SREResult:
    from panelin_v4.engine.sre_engine import SREResult, QuotationLevel

    return SREResult(
        score=d.get("score", 0),
        level=QuotationLevel(d.get("level", "commercial_quick")),
        r_datos=d.get("r_datos", 0),
        r_autoportancia=d.get("r_autoportancia", 0),
        r_geometria=d.get("r_geometria", 0),
        r_sistema=d.get("r_sistema", 0),
        breakdown=d.get("breakdown", []),
        recommendations=d.get("recommendations", []),
        alternative_thicknesses=d.get("alternative_thicknesses", []),
    )


def _dict_to_pricing_result(d: dict) -> PricingResult:
    from panelin_v4.engine.pricing_engine import PricingResult, PricedItem

    items = [
        PricedItem(
            tipo=i.get("tipo", ""),
            sku=i.get("sku"),
            name=i.get("name"),
            quantity=i.get("quantity", 0),
            unit=i.get("unit", "unid"),
            unit_price_usd=i.get("unit_price_usd", 0),
            subtotal_usd=i.get("subtotal_usd", 0),
            price_source=i.get("price_source", ""),
            price_includes_iva=i.get("price_includes_iva", True),
        )
        for i in d.get("items", [])
    ]
    return PricingResult(
        items=items,
        subtotal_panels_usd=d.get("subtotal_panels_usd", 0),
        subtotal_accessories_usd=d.get("subtotal_accessories_usd", 0),
        subtotal_total_usd=d.get("subtotal_total_usd", 0),
        iva_mode=d.get("iva_mode", "incluido"),
        warnings=d.get("warnings", []),
        missing_prices=d.get("missing_prices", []),
    )
