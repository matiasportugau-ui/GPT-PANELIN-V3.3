"""Tests for the price validation guardrail."""

import pytest

from src.guardrails.price_validation import validate_prices_in_response


class TestPriceValidation:
    def test_valid_response(self):
        result = validate_prices_in_response(
            "Total: $1,250.50 USD (IVA incluido). "
            "Panel ISODEC 100mm: $45.20/m2."
        )
        assert result["valid"] is True
        assert len(result["warnings"]) == 0

    def test_suspiciously_low_price(self):
        result = validate_prices_in_response(
            "El precio del panel es $0.10 por m2."
        )
        assert result["valid"] is False
        assert any("bajo" in w for w in result["warnings"])

    def test_suspiciously_high_price(self):
        result = validate_prices_in_response(
            "Total de la cotización: $100,000.00 USD."
        )
        assert result["valid"] is False
        assert any("alto" in w for w in result["warnings"])

    def test_estimated_price_language(self):
        result = validate_prices_in_response(
            "El precio estimado es de $500.00 por m2."
        )
        assert result["valid"] is False
        assert any("estimación" in w for w in result["warnings"])

    def test_no_prices_is_valid(self):
        result = validate_prices_in_response(
            "Necesitamos más datos para generar la cotización."
        )
        assert result["valid"] is True
