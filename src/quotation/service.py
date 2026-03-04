"""
Panelin v5.0 — Quotation Service

Thin service layer wrapping the deterministic engine (panelin_v4).
The engine is NOT modified — this layer adds structured I/O for the
Agno workflow steps.
"""

from __future__ import annotations

import json
from typing import Any, Optional

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
)
from panelin_v4.evaluator.sai_engine import SAIResult, calculate_sai


class QuotationService:
    """Stateless service exposing each pipeline stage individually."""

    @staticmethod
    def classify(text: str, force_mode: Optional[str] = None) -> dict[str, Any]:
        fm = OperatingMode(force_mode) if force_mode else None
        result = classify_request(text, force_mode=fm)
        return result.to_dict()

    @staticmethod
    def parse(text: str) -> dict[str, Any]:
        result = parse_request(text)
        return result.to_dict()

    @staticmethod
    def compute_sre(parsed: dict[str, Any]) -> dict[str, Any]:
        req = _dict_to_quote_request(parsed)
        result = calculate_sre(req)
        return result.to_dict()

    @staticmethod
    def compute_bom(parsed: dict[str, Any]) -> dict[str, Any]:
        req = _dict_to_quote_request(parsed)
        if not _can_calculate_bom(req):
            return BOMResult(
                system_key="unknown",
                area_m2=0,
                panel_count=0,
                supports_per_panel=0,
                fixation_points=0,
                warnings=["Insufficient data for BOM calculation"],
            ).to_dict()

        length_m = req.geometry.length_m or 0
        width_m = req.geometry.width_m or 0
        if not width_m and req.geometry.panel_count:
            width_m = req.geometry.panel_count * 1.12

        if length_m <= 0 or width_m <= 0:
            return BOMResult(
                system_key="unknown",
                area_m2=0,
                panel_count=0,
                supports_per_panel=0,
                fixation_points=0,
                warnings=["Zero dimensions"],
            ).to_dict()

        result = calculate_bom(
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
    def compute_pricing(
        bom_dict: dict[str, Any],
        parsed: dict[str, Any],
    ) -> dict[str, Any]:
        familia = parsed.get("familia")
        sub_familia = parsed.get("sub_familia", "EPS")
        thickness = parsed.get("thickness_mm")

        if not familia or not thickness or bom_dict.get("panel_count", 0) == 0:
            return PricingResult().to_dict()

        bom = _dict_to_bom_result(bom_dict)
        result = calculate_pricing(
            bom=bom,
            familia=familia,
            sub_familia=sub_familia or "EPS",
            thickness_mm=thickness,
            panel_area_m2=bom.area_m2,
            iva_mode=parsed.get("iva_mode", "incluido"),
        )
        return result.to_dict()

    @staticmethod
    def validate(
        parsed: dict[str, Any],
        sre_dict: dict[str, Any],
        bom_dict: dict[str, Any],
        pricing_dict: dict[str, Any],
        mode: str,
    ) -> dict[str, Any]:
        req = _dict_to_quote_request(parsed)
        sre = _dict_to_sre(sre_dict)
        bom = _dict_to_bom_result(bom_dict)
        pricing = _dict_to_pricing(pricing_dict)
        op_mode = OperatingMode(mode)
        result = validate_quotation(req, sre, bom, pricing, op_mode)
        return result.to_dict()

    @staticmethod
    def full_pipeline(
        text: str,
        force_mode: Optional[str] = None,
        client_name: Optional[str] = None,
        client_phone: Optional[str] = None,
        client_location: Optional[str] = None,
    ) -> dict[str, Any]:
        fm = OperatingMode(force_mode) if force_mode else None
        output = process_quotation(
            text=text,
            force_mode=fm,
            client_name=client_name,
            client_phone=client_phone,
            client_location=client_location,
        )
        return output.to_dict()

    @staticmethod
    def compute_sai(output_dict: dict[str, Any]) -> dict[str, Any]:
        output = _dict_to_quotation_output(output_dict)
        result = calculate_sai(output)
        return result.to_dict()


def _can_calculate_bom(req: QuoteRequest) -> bool:
    return (
        req.familia is not None
        and req.thickness_mm is not None
        and req.uso is not None
        and (req.geometry.length_m is not None or bool(req.geometry.panel_lengths))
    )


def _dict_to_quote_request(d: dict) -> QuoteRequest:
    """Reconstruct a QuoteRequest from its dict representation."""
    from panelin_v4.engine.parser import ClientInfo, ProjectGeometry

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
    from panelin_v4.engine.bom_engine import BOMItem

    items = []
    for item in d.get("items", []):
        items.append(BOMItem(
            tipo=item.get("tipo", ""),
            referencia=item.get("referencia", ""),
            sku=item.get("sku"),
            name=item.get("name"),
            quantity=item.get("quantity", 0),
            unit=item.get("unit", "unid"),
            formula_used=item.get("formula_used", ""),
            notes=item.get("notes", ""),
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


def _dict_to_sre(d: dict) -> SREResult:
    from panelin_v4.engine.sre_engine import QuotationLevel

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


def _dict_to_pricing(d: dict) -> PricingResult:
    from panelin_v4.engine.pricing_engine import PricedItem

    items = []
    for item in d.get("items", []):
        items.append(PricedItem(
            tipo=item.get("tipo", ""),
            sku=item.get("sku"),
            name=item.get("name"),
            quantity=item.get("quantity", 0),
            unit=item.get("unit", "unid"),
            unit_price_usd=item.get("unit_price_usd", 0),
            subtotal_usd=item.get("subtotal_usd", 0),
            price_source=item.get("price_source", ""),
            price_includes_iva=item.get("price_includes_iva", True),
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


def _dict_to_quotation_output(d: dict) -> QuotationOutput:
    return QuotationOutput(
        quote_id=d.get("quote_id", ""),
        timestamp=d.get("timestamp", ""),
        mode=d.get("mode", "pre_cotizacion"),
        level=d.get("level", "commercial_quick"),
        status=d.get("status", "draft"),
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
