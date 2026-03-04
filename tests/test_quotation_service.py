"""
Tests for src/quotation/service.py — QuotationService facade.
"""

import json
import pytest

from src.quotation.service import QuotationService


class TestQuotationServiceClassify:
    def test_classify_roof(self):
        result = QuotationService.classify("Isodec 100mm techo 6 paneles")
        assert result["request_type"] == "roof_system"
        assert result["has_roof"] is True

    def test_classify_wall(self):
        result = QuotationService.classify("Isopanel 50mm pared 13 paneles")
        assert result["request_type"] == "wall_system"
        assert result["has_wall"] is True

    def test_classify_with_mode(self):
        result = QuotationService.classify("Isodec 100mm techo", force_mode="formal")
        assert result["operating_mode"] == "formal"


class TestQuotationServiceParse:
    def test_parse_basic(self):
        result = QuotationService.parse("Isodec EPS 100mm / 6 paneles de 6.5mts / techo")
        assert result["familia"] == "ISODEC"
        assert result["sub_familia"] == "EPS"
        assert result["thickness_mm"] == 100
        assert result["uso"] == "techo"

    def test_parse_returns_dict(self):
        result = QuotationService.parse("cualquier texto")
        assert isinstance(result, dict)
        assert "familia" in result


class TestQuotationServiceFullPipeline:
    def test_full_quotation(self):
        result = QuotationService.full_quotation(
            text="Isodec EPS 100mm / 6 paneles de 6.5mts / techo completo a metal",
            mode="pre_cotizacion",
            client_name="Test Client",
        )
        assert "quote_id" in result
        assert result["quote_id"].startswith("PV4-")
        assert result["mode"] in ("pre_cotizacion", "formal", "informativo")
        assert "bom" in result
        assert "pricing" in result
        assert "validation" in result

    def test_full_quotation_wall(self):
        result = QuotationService.full_quotation(
            text="Isopanel EPS 50mm / 13 paneles de 2.60mts / pared",
        )
        assert result["bom"]["panel_count"] > 0

    def test_sai_score(self):
        output = QuotationService.full_quotation(
            text="Isodec EPS 100mm / 10 paneles de 5mts / techo a metal",
            client_name="Test",
        )
        sai = QuotationService.calculate_sai_score(output)
        assert "score" in sai
        assert "grade" in sai
        assert sai["score"] >= 0
        assert sai["score"] <= 100


class TestQuotationServiceBOM:
    def test_calculate_bom(self):
        result = QuotationService.calculate_bom(
            familia="ISODEC",
            sub_familia="EPS",
            thickness_mm=100,
            uso="techo",
            length_m=5.0,
            width_m=11.0,
            structure_type="metal",
        )
        assert result["panel_count"] >= 10
        assert result["area_m2"] == 55.0
        items = [i["tipo"] for i in result["items"]]
        assert "panel" in items


class TestQuotationServiceBatch:
    def test_batch_quotation(self):
        results = QuotationService.batch_quotation([
            {"text": "Isodec 100mm / 6 paneles de 5mts"},
            {"text": "Isopanel 50mm / 13 paneles de 2.60mts"},
        ])
        assert len(results) == 2
        for r in results:
            assert "quote_id" in r
