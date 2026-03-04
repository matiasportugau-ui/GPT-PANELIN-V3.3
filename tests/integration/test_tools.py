"""
Integration tests for Agno tool wrappers.

Verifies that each tool function produces valid JSON output
and correctly delegates to the underlying engine.
"""

from __future__ import annotations

import json
import pytest

from src.quotation.tools import (
    quote_from_text,
    validate_quotation_request,
    check_product_price,
    search_accessories,
    calculate_sai_score,
)


class TestQuoteFromText:
    def test_basic_roof_quote(self):
        result = json.loads(quote_from_text(
            "ISODEC EPS 100mm para techo de 10x7m sobre metal"
        ))
        assert "quote_id" in result
        assert result["mode"] == "pre_cotizacion"

    def test_wall_quote(self):
        result = json.loads(quote_from_text(
            "ISOPANEL 80mm para pared de 15x3m",
            mode="pre_cotizacion",
        ))
        assert "quote_id" in result

    def test_formal_mode(self):
        result = json.loads(quote_from_text(
            "ISODEC 100mm techo 10x7m luz 3m metal",
            mode="formal",
        ))
        assert result["mode"] == "formal"

    def test_with_client_info(self):
        result = json.loads(quote_from_text(
            "ISODEC 100mm techo 10x7",
            client_name="Juan Pérez",
            client_phone="099123456",
        ))
        assert result["request"]["client"]["name"] == "Juan Pérez"


class TestValidateQuotationRequest:
    def test_validate_complete_request(self):
        result = json.loads(validate_quotation_request(
            "ISODEC EPS 100mm techo 10x7m metal"
        ))
        assert "classification" in result
        assert "request" in result
        assert "sre" in result
        assert "validation" in result

    def test_validate_incomplete_request(self):
        result = json.loads(validate_quotation_request(
            "Paneles para techo"
        ))
        assert len(result["request"]["incomplete_fields"]) > 0


class TestCheckProductPrice:
    def test_price_lookup(self):
        result = json.loads(check_product_price("ISODEC", "EPS", 100))
        assert "found" in result
        if result["found"]:
            assert result["iva_included"] is True
            assert result["source"] == "bromyros_pricing_master"

    def test_price_not_found(self):
        result = json.loads(check_product_price("UNKNOWN", "XXX", 999))
        assert result["found"] is False


class TestSearchAccessories:
    def test_search_gotero(self):
        result = json.loads(search_accessories("gotero_frontal", "ISODEC", 100))
        assert "found" in result

    def test_search_unknown_tipo(self):
        result = json.loads(search_accessories("unknown_tipo_xyz"))
        assert result["found"] is False


class TestCalculateSaiScore:
    def test_sai_calculation(self):
        result = json.loads(calculate_sai_score(
            "ISODEC EPS 100mm techo 10x7m metal"
        ))
        assert "sai" in result
        assert 0 <= result["sai"]["score"] <= 100
        assert result["sai"]["grade"] in ("A", "B", "C", "D", "F")
