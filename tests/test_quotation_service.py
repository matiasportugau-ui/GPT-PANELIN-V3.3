"""
Tests for the QuotationService wrapper layer.

Ensures the service layer correctly wraps the v4 engine
without modifying engine behavior.
"""

import json
import pytest

from src.quotation.service import QuotationService


class TestClassifyService:
    def test_roof_classification(self):
        result = QuotationService.classify("Isodec 100 mm techo completo")
        assert result["request_type"] == "roof_system"
        assert result["has_roof"] is True

    def test_wall_classification(self):
        result = QuotationService.classify("Isopanel 50 mm pared")
        assert result["request_type"] == "wall_system"
        assert result["has_wall"] is True

    def test_accessories_only(self):
        result = QuotationService.classify("12 goteros frontales + 8 goteros laterales")
        assert result["has_accessories"] is True

    def test_formal_mode(self):
        result = QuotationService.classify("Isodec 100 mm PDF formal", force_mode="formal")
        assert result["operating_mode"] == "formal"


class TestParseService:
    def test_basic_parse(self):
        result = QuotationService.parse("Isodec EPS 100 mm 6 paneles de 6,5 mts techo a metal")
        assert result["familia"] == "ISODEC"
        assert result["sub_familia"] == "EPS"
        assert result["thickness_mm"] == 100

    def test_wall_parse(self):
        result = QuotationService.parse("Isopanel 50 mm 13 paneles de 2.60 mts pared")
        assert result["familia"] == "ISOPANEL"
        assert result["uso"] == "pared"
        assert result["thickness_mm"] == 50


class TestSREService:
    def test_low_risk_complete(self):
        parsed = QuotationService.parse("Isodec EPS 100 mm 6 paneles de 4.5 mts techo a metal")
        parsed["span_m"] = 4.5
        sre = QuotationService.compute_sre(parsed)
        assert sre["score"] <= 30

    def test_wall_zero_system_risk(self):
        parsed = QuotationService.parse("Isopanel 50 mm 13 paneles de 2.60 mts pared")
        sre = QuotationService.compute_sre(parsed)
        assert sre["r_sistema"] == 0


class TestBOMService:
    def test_roof_bom(self):
        parsed = QuotationService.parse("Isodec EPS 100 mm techo 11 x 5 a metal")
        parsed["structure_type"] = "metal"
        bom = QuotationService.compute_bom(parsed)
        assert bom["panel_count"] >= 5
        assert bom["area_m2"] == 55.0
        item_types = [i["tipo"] for i in bom["items"]]
        assert "panel" in item_types

    def test_wall_bom(self):
        parsed = QuotationService.parse("Isopanel 100 mm pared 10 x 2.5 a metal")
        parsed["structure_type"] = "metal"
        bom = QuotationService.compute_bom(parsed)
        assert bom["panel_count"] > 0
        item_types = [i["tipo"] for i in bom["items"]]
        assert "perfil_u" in item_types

    def test_insufficient_data(self):
        parsed = QuotationService.parse("hola")
        bom = QuotationService.compute_bom(parsed)
        assert bom["panel_count"] == 0


class TestPricingService:
    def test_pricing_from_kb(self):
        parsed = QuotationService.parse("Isodec EPS 100 mm techo 5 x 11 a metal")
        parsed["structure_type"] = "metal"
        bom = QuotationService.compute_bom(parsed)

        if bom["panel_count"] > 0:
            pricing = QuotationService.compute_pricing(bom, parsed)
            assert pricing["iva_mode"] == "incluido"

    def test_no_pricing_without_bom(self):
        parsed = QuotationService.parse("hola")
        empty_bom = {"panel_count": 0, "items": []}
        pricing = QuotationService.compute_pricing(empty_bom, parsed)
        assert pricing["subtotal_total_usd"] == 0


class TestFullPipeline:
    def test_full_pipeline(self):
        result = QuotationService.full_pipeline(
            text="Isodec EPS 100 mm 6 paneles de 6.5 mts techo completo a metal",
            client_name="Test",
            client_location="Montevideo",
        )
        assert result["quote_id"].startswith("PV4-")
        assert result["mode"] in ("pre_cotizacion", "formal", "informativo")
        assert "classification" in result
        assert "request" in result
        assert "sre" in result
        assert "bom" in result
        assert "pricing" in result
        assert "validation" in result

    def test_pre_mode_never_blocks(self):
        result = QuotationService.full_pipeline(
            text="Isodec 100 mm techo 7 x 10",
            force_mode="pre_cotizacion",
        )
        assert result["status"] != "blocked"

    def test_accessories_only_pipeline(self):
        result = QuotationService.full_pipeline(
            text="12 Goteros Frontales 100 mm + 8 Goteros Laterales 100 mm",
        )
        assert result["status"] != "blocked"


class TestSAIService:
    def test_sai_score(self):
        output = QuotationService.full_pipeline(
            text="Isodec EPS 100 mm 10 paneles de 5 mts techo completo a metal",
            client_name="Test",
            client_location="Montevideo",
        )
        sai = QuotationService.compute_sai(output)
        assert "score" in sai
        assert "grade" in sai
        assert sai["grade"] in ("A", "B", "C", "D", "F")
