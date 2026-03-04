"""
Tests for src/guardrails/price_guardrail.py
"""

import pytest

from src.guardrails.price_guardrail import check_no_invented_prices


class TestPriceGuardrail:
    def test_safe_output(self):
        output = (
            "📋 Cotización PV5-20260304-ABCD1234\n"
            "📦 ISODEC EPS 100mm\n"
            "💰 Total: USD 1,234.56 (IVA incluido)\n"
        )
        is_safe, flagged = check_no_invented_prices(output)
        assert is_safe is True
        assert len(flagged) == 0

    def test_detects_iva_addition(self):
        output = "Subtotal: USD 1,000.00 + 22% IVA = USD 1,220.00"
        is_safe, flagged = check_no_invented_prices(output)
        assert is_safe is False
        assert any(f["tipo"] == "iva_doble" for f in flagged)

    def test_detects_iva_mas(self):
        output = "El precio es USD 500 más IVA."
        is_safe, flagged = check_no_invented_prices(output)
        assert is_safe is False

    def test_normal_iva_mention_ok(self):
        output = "Todos los precios incluyen IVA 22%."
        is_safe, flagged = check_no_invented_prices(output)
        assert is_safe is True
