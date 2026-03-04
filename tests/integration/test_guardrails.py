"""
Tests for the price guardrail.
"""

from __future__ import annotations

import pytest

from src.guardrails.price_guardrail import (
    validate_prices_in_response,
    _load_known_prices,
)


class TestPriceGuardrail:
    def test_load_known_prices(self):
        prices = _load_known_prices()
        assert isinstance(prices, set)

    def test_valid_response_no_prices(self):
        result = validate_prices_in_response(
            "Los paneles ISODEC están disponibles en espesores de 50 a 200mm."
        )
        assert result["valid"] is True
        assert result["checked_count"] == 0

    def test_response_with_known_price(self):
        prices = _load_known_prices()
        if prices:
            known_price = next(iter(prices))
            response = f"El precio del panel es USD ${known_price:.2f}/m²"
            result = validate_prices_in_response(response)
            assert result["checked_count"] >= 1

    def test_response_with_suspicious_price(self):
        result = validate_prices_in_response(
            "El precio especial es $99999.99 por m²"
        )
        if result["known_prices_loaded"] > 0:
            assert len(result["suspicious_prices"]) > 0
            assert result["valid"] is False
