"""
Panelin v5.0 - Quotation Service
==================================

Thin service layer wrapping the v4 deterministic engine.
Adds session tracking, persistence hooks, and structured result types
without modifying any engine logic.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Optional

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
    process_quotation,
    process_batch,
)
from panelin_v4.evaluator.sai_engine import SAIResult, calculate_sai


MODE_MAP: dict[str, OperatingMode] = {
    "informativo": OperatingMode.INFORMATIVO,
    "pre_cotizacion": OperatingMode.PRE_COTIZACION,
    "formal": OperatingMode.FORMAL,
}


class QuotationService:
    """Facade over the panelin_v4 engine pipeline.

    Provides convenience methods for the Agno workflow steps and tools.
    """

    @staticmethod
    def classify(text: str, force_mode: Optional[str] = None) -> dict:
        mode = MODE_MAP.get(force_mode) if force_mode else None
        result = classify_request(text, force_mode=mode)
        return result.to_dict()

    @staticmethod
    def parse(text: str) -> dict:
        result = parse_request(text)
        return result.to_dict()

    @staticmethod
    def calculate_sre(request_dict: dict) -> dict:
        req = _rebuild_quote_request(request_dict)
        result = calculate_sre(req)
        return result.to_dict()

    @staticmethod
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
    ) -> dict:
        result = calculate_bom(
            familia=familia,
            sub_familia=sub_familia,
            thickness_mm=thickness_mm,
            uso=uso,
            length_m=length_m,
            width_m=width_m,
            structure_type=structure_type,
            panel_count=panel_count,
            panel_lengths=panel_lengths,
            roof_type=roof_type,
            span_m=span_m,
        )
        return result.to_dict()

    @staticmethod
    def calculate_pricing(
        bom_dict: dict,
        familia: str,
        sub_familia: str,
        thickness_mm: int,
        panel_area_m2: Optional[float] = None,
        iva_mode: str = "incluido",
    ) -> dict:
        bom = _rebuild_bom_result(bom_dict)
        result = calculate_pricing(
            bom=bom,
            familia=familia,
            sub_familia=sub_familia,
            thickness_mm=thickness_mm,
            panel_area_m2=panel_area_m2,
            iva_mode=iva_mode,
        )
        return result.to_dict()

    @staticmethod
    def validate(
        request_dict: dict,
        sre_dict: dict,
        bom_dict: dict,
        pricing_dict: dict,
        mode: str,
    ) -> dict:
        req = _rebuild_quote_request(request_dict)
        sre = _rebuild_sre_result(sre_dict)
        bom = _rebuild_bom_result(bom_dict)
        pricing_result = _rebuild_pricing_result(pricing_dict)
        op_mode = MODE_MAP.get(mode, OperatingMode.PRE_COTIZACION)
        result = validate_quotation(
            request=req, sre=sre, bom=bom, pricing=pricing_result, mode=op_mode
        )
        return result.to_dict()

    @staticmethod
    def full_quotation(
        text: str,
        mode: Optional[str] = None,
        client_name: Optional[str] = None,
        client_phone: Optional[str] = None,
        client_location: Optional[str] = None,
    ) -> dict:
        force_mode = MODE_MAP.get(mode) if mode else None
        output = process_quotation(
            text=text,
            force_mode=force_mode,
            client_name=client_name,
            client_phone=client_phone,
            client_location=client_location,
        )
        return output.to_dict()

    @staticmethod
    def calculate_sai_score(output_dict: dict) -> dict:
        output = _rebuild_quotation_output(output_dict)
        sai = calculate_sai(output)
        return sai.to_dict()

    @staticmethod
    def batch_quotation(requests: list[dict], mode: Optional[str] = None) -> list[dict]:
        force_mode = MODE_MAP.get(mode) if mode else None
        results = process_batch(requests, force_mode=force_mode)
        return [r.to_dict() for r in results]


def _rebuild_quote_request(d: dict) -> QuoteRequest:
    """Reconstruct QuoteRequest from dict for engine functions that need it."""
    from panelin_v4.engine.parser import ClientInfo, ProjectGeometry

    geo_d = d.get("geometry", {})
    geo = ProjectGeometry(
        length_m=geo_d.get("length_m"),
        width_m=geo_d.get("width_m"),
        height_m=geo_d.get("height_m"),
        panel_count=geo_d.get("panel_count"),
        panel_lengths=geo_d.get("panel_lengths", []),
    )
    client_d = d.get("client", {})
    client = ClientInfo(
        name=client_d.get("name"),
        phone=client_d.get("phone"),
        location=client_d.get("location"),
    )
    return QuoteRequest(
        familia=d.get("familia"),
        sub_familia=d.get("sub_familia"),
        thickness_mm=d.get("thickness_mm"),
        uso=d.get("uso"),
        structure_type=d.get("structure_type"),
        span_m=d.get("span_m"),
        geometry=geo,
        client=client,
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


def _rebuild_bom_result(d: dict) -> BOMResult:
    from panelin_v4.engine.bom_engine import BOMItem

    items = []
    for item_d in d.get("items", []):
        items.append(BOMItem(
            tipo=item_d.get("tipo", ""),
            referencia=item_d.get("referencia", ""),
            sku=item_d.get("sku"),
            name=item_d.get("name"),
            quantity=item_d.get("quantity", 0),
            unit=item_d.get("unit", "unid"),
            formula_used=item_d.get("formula_used", ""),
            notes=item_d.get("notes", ""),
        ))
    return BOMResult(
        system_key=d.get("system_key", "unknown"),
        area_m2=d.get("area_m2", 0),
        panel_count=d.get("panel_count", 0),
        supports_per_panel=d.get("supports_per_panel", 0),
        fixation_points=d.get("fixation_points", 0),
        items=items,
        warnings=d.get("warnings", []),
    )


def _rebuild_sre_result(d: dict) -> SREResult:
    from panelin_v4.engine.sre_engine import QuotationLevel

    level_map = {v.value: v for v in QuotationLevel}
    return SREResult(
        score=d.get("score", 0),
        level=level_map.get(d.get("level", ""), QuotationLevel.LEVEL_1_COMMERCIAL),
        r_datos=d.get("r_datos", 0),
        r_autoportancia=d.get("r_autoportancia", 0),
        r_geometria=d.get("r_geometria", 0),
        r_sistema=d.get("r_sistema", 0),
        breakdown=d.get("breakdown", []),
        recommendations=d.get("recommendations", []),
        alternative_thicknesses=d.get("alternative_thicknesses", []),
    )


def _rebuild_pricing_result(d: dict) -> PricingResult:
    from panelin_v4.engine.pricing_engine import PricedItem

    items = []
    for item_d in d.get("items", []):
        items.append(PricedItem(
            tipo=item_d.get("tipo", ""),
            sku=item_d.get("sku"),
            name=item_d.get("name"),
            quantity=item_d.get("quantity", 0),
            unit=item_d.get("unit", "unid"),
            unit_price_usd=item_d.get("unit_price_usd", 0),
            subtotal_usd=item_d.get("subtotal_usd", 0),
            price_source=item_d.get("price_source", ""),
            price_includes_iva=item_d.get("price_includes_iva", True),
        ))
    return PricingResult(
        items=items,
        subtotal_panels_usd=d.get("subtotal_panels_usd", 0),
        subtotal_accessories_usd=d.get("subtotal_accessories_usd", 0),
        subtotal_total_usd=d.get("subtotal_total_usd", 0),
        iva_mode=d.get("iva_mode", "incluido"),
        warnings=d.get("warnings", []),
        missing_prices=d.get("missing_prices", []),
    )


def _rebuild_quotation_output(d: dict) -> QuotationOutput:
    return QuotationOutput(
        quote_id=d.get("quote_id", ""),
        timestamp=d.get("timestamp", ""),
        mode=d.get("mode", ""),
        level=d.get("level", ""),
        status=d.get("status", ""),
        classification=d.get("classification", {}),
        request=d.get("request", {}),
        sre=d.get("sre", {}),
        bom=d.get("bom", {}),
        pricing=d.get("pricing", {}),
        validation=d.get("validation", {}),
        assumptions_used=d.get("assumptions_used", []),
        confidence_score=d.get("confidence_score", 0),
        processing_notes=d.get("processing_notes", []),
    )
