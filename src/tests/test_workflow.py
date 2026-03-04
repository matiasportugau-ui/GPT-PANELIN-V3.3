"""
Panelin Agno — Workflow Integration Tests

Tests the deterministic pipeline steps WITHOUT requiring an LLM.
The LLM respond step is tested separately (requires API key).
"""

from __future__ import annotations

import json
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.quotation.service import QuotationService


class TestQuotationService:
    """Test the QuotationService wrapper."""

    def test_classify_roof(self):
        result = QuotationService.classify("Necesito cotizar ISODEC 100mm para techo")
        assert result["request_type"] == "roof_system"
        assert result["has_roof"] is True

    def test_classify_wall(self):
        result = QuotationService.classify("ISOPANEL 50mm para pared de galpón")
        assert result["request_type"] == "wall_system"
        assert result["has_wall"] is True

    def test_classify_formal(self):
        result = QuotationService.classify("Necesito presupuesto formal PDF para ISODEC 100mm techo")
        assert result["operating_mode"] == "formal"

    def test_parse_basic(self):
        result = QuotationService.parse("6 paneles ISODEC EPS 100mm de 6.5m para techo")
        assert result["familia"] == "ISODEC"
        assert result["sub_familia"] == "EPS"
        assert result["thickness_mm"] == 100
        assert result["uso"] == "techo"

    def test_parse_dimensions(self):
        result = QuotationService.parse("ISODEC 100mm techo 10 x 12 m")
        assert result["geometry"]["width_m"] == 10 or result["geometry"]["length_m"] == 10

    def test_sre_low_risk(self):
        parsed = QuotationService.parse("6 paneles ISODEC EPS 100mm de 6.5m para techo estructura metal luz 3m")
        sre = QuotationService.calculate_sre(parsed)
        assert sre["score"] <= 60

    def test_bom_roof(self):
        parsed = QuotationService.parse("ISODEC EPS 100mm techo 8 x 12 m estructura metal")
        bom = QuotationService.calculate_bom(parsed)
        assert bom["panel_count"] > 0
        assert bom["area_m2"] > 0
        assert len(bom["items"]) > 0

    def test_bom_wall(self):
        parsed = QuotationService.parse("ISOPANEL 50mm pared 10 x 3 m estructura metal")
        bom = QuotationService.calculate_bom(parsed)
        assert bom["panel_count"] > 0

    def test_pricing(self):
        parsed = QuotationService.parse("ISODEC EPS 100mm techo 8 x 12 m")
        bom = QuotationService.calculate_bom(parsed)
        pricing = QuotationService.calculate_pricing(bom, parsed)
        assert isinstance(pricing, dict)
        assert "subtotal_total_usd" in pricing

    def test_validate(self):
        parsed = QuotationService.parse("ISODEC EPS 100mm techo 8 x 12 m")
        sre = QuotationService.calculate_sre(parsed)
        bom = QuotationService.calculate_bom(parsed)
        pricing = QuotationService.calculate_pricing(bom, parsed)
        validation = QuotationService.validate(parsed, sre, bom, pricing, "pre_cotizacion")
        assert isinstance(validation, dict)
        assert "is_valid" in validation

    def test_full_pipeline(self):
        result = QuotationService.full_pipeline(
            "6 paneles ISODEC EPS 100mm de 6.5m para techo estructura metal"
        )
        assert "quote_id" in result
        assert result["mode"] == "pre_cotizacion"
        assert "bom" in result
        assert "pricing" in result

    def test_full_pipeline_formal(self):
        result = QuotationService.full_pipeline(
            "Necesito cotización formal PDF para ISODEC 100mm techo 8x12m",
            force_mode="formal",
        )
        assert result["mode"] == "formal"

    def test_batch_pipeline(self):
        requests = [
            {"text": "ISODEC 100mm techo 8 x 12 m"},
            {"text": "ISOPANEL 50mm pared 10 x 3 m"},
        ]
        results = QuotationService.batch_pipeline(requests)
        assert len(results) == 2
        assert all("quote_id" in r for r in results)


class TestWorkflowSteps:
    """Test individual workflow step functions."""

    def test_step_classify(self):
        from src.agent.workflow import _step_classify, StepInput

        step_input = StepInput(input="ISODEC 100mm techo 8x12m")
        result = _step_classify(step_input)
        data = json.loads(result.content)
        assert "classification" in data
        assert data["classification"]["request_type"] == "roof_system"

    def test_step_parse(self):
        from src.agent.workflow import _step_parse, StepInput

        prev = json.dumps({"text": "ISODEC EPS 100mm techo 8 x 12 m"})
        step_input = StepInput(input="", previous_step_content=prev)
        result = _step_parse(step_input)
        data = json.loads(result.content)
        assert "parsed" in data
        assert data["parsed"]["familia"] == "ISODEC"

    def test_step_sre(self):
        from src.agent.workflow import _step_sre, StepInput

        prev = json.dumps({
            "text": "ISODEC 100mm techo",
            "classification": {"request_type": "roof_system", "operating_mode": "pre_cotizacion"},
            "parsed": QuotationService.parse("ISODEC EPS 100mm techo 8 x 12 m"),
        })
        step_input = StepInput(input="", previous_step_content=prev)
        result = _step_sre(step_input)
        data = json.loads(result.content)
        assert "sre" in data
        assert "score" in data["sre"]

    def test_step_bom(self):
        from src.agent.workflow import _step_bom, StepInput

        prev = json.dumps({
            "text": "ISODEC 100mm techo",
            "classification": {"request_type": "roof_system", "operating_mode": "pre_cotizacion"},
            "parsed": QuotationService.parse("ISODEC EPS 100mm techo 8 x 12 m"),
            "sre": {"score": 20},
        })
        step_input = StepInput(input="", previous_step_content=prev)
        result = _step_bom(step_input)
        data = json.loads(result.content)
        assert "bom" in data
        assert data["bom"]["panel_count"] > 0

    def test_step_pricing(self):
        from src.agent.workflow import _step_pricing, StepInput

        parsed = QuotationService.parse("ISODEC EPS 100mm techo 8 x 12 m")
        bom = QuotationService.calculate_bom(parsed)
        prev = json.dumps({
            "text": "ISODEC 100mm techo",
            "parsed": parsed,
            "bom": bom,
        })
        step_input = StepInput(input="", previous_step_content=prev)
        result = _step_pricing(step_input)
        data = json.loads(result.content)
        assert "pricing" in data

    def test_step_validate(self):
        from src.agent.workflow import _step_validate, StepInput

        parsed = QuotationService.parse("ISODEC EPS 100mm techo 8 x 12 m")
        sre = QuotationService.calculate_sre(parsed)
        bom = QuotationService.calculate_bom(parsed)
        pricing = QuotationService.calculate_pricing(bom, parsed)
        prev = json.dumps({
            "text": "ISODEC 100mm techo",
            "classification": {"request_type": "roof_system", "operating_mode": "pre_cotizacion"},
            "parsed": parsed,
            "sre": sre,
            "bom": bom,
            "pricing": pricing,
        })
        step_input = StepInput(input="", previous_step_content=prev)
        result = _step_validate(step_input)
        data = json.loads(result.content)
        assert "validation" in data
        assert "quote_id" in data

    def test_needs_full_pipeline_roof(self):
        from src.agent.workflow import _needs_full_pipeline, StepInput

        prev = json.dumps({
            "classification": {"request_type": "roof_system", "operating_mode": "pre_cotizacion"},
        })
        step_input = StepInput(input="", previous_step_content=prev)
        assert _needs_full_pipeline(step_input) is True

    def test_needs_full_pipeline_info_only(self):
        from src.agent.workflow import _needs_full_pipeline, StepInput

        prev = json.dumps({
            "classification": {"request_type": "info_only", "operating_mode": "informativo"},
        })
        step_input = StepInput(input="", previous_step_content=prev)
        assert _needs_full_pipeline(step_input) is False


class TestGuardrails:
    """Test guardrail functions."""

    def test_no_invented_prices_ok(self):
        from src.agent.guardrails import validate_no_invented_prices

        response = "La cotización incluye USD 1500.00 por paneles y USD 200.00 por accesorios."
        result = validate_no_invented_prices(response)
        assert result is None

    def test_spanish_response_ok(self):
        from src.agent.guardrails import validate_spanish_response

        response = "La cotización incluye 10 paneles ISODEC 100mm para techo."
        result = validate_spanish_response(response)
        assert result is None

    def test_english_response_detected(self):
        from src.agent.guardrails import validate_spanish_response

        response = "Here is your quote. The total cost is $1500. Based on your request, the price is competitive."
        result = validate_spanish_response(response)
        assert result is not None


class TestConfigModule:
    """Test configuration module."""

    def test_settings_defaults(self):
        from src.core.config import AppSettings

        settings = AppSettings()
        assert settings.version == "5.0.0"
        assert settings.llm.provider == "openai"
        assert settings.llm.model_id == "gpt-4o"
        assert settings.db.sessions_table == "panelin_sessions"

    def test_settings_env_override(self, monkeypatch):
        from src.core.config import AppSettings

        monkeypatch.setenv("LLM_MODEL_ID", "gpt-4o-mini")
        monkeypatch.setenv("ENVIRONMENT", "production")
        settings = AppSettings()
        assert settings.llm.model_id == "gpt-4o-mini"
        assert settings.environment == "production"


class TestToolWrappers:
    """Test the Agno tool wrapper functions."""

    def test_generate_quotation(self):
        from src.quotation.tools import generate_quotation

        result = generate_quotation("ISODEC EPS 100mm techo 8 x 12 m estructura metal")
        data = json.loads(result)
        assert "quote_id" in data
        assert "bom" in data
        assert "pricing" in data

    def test_classify_request(self):
        from src.quotation.tools import classify_request

        result = classify_request("Necesito cotizar ISODEC 100mm para techo")
        data = json.loads(result)
        assert data["request_type"] == "roof_system"

    def test_get_accessory_catalog(self):
        from src.quotation.tools import get_accessory_catalog

        result = get_accessory_catalog()
        data = json.loads(result)
        assert "total" in data or "error" in data
