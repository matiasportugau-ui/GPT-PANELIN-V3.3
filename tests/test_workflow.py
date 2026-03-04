"""
Tests for the Agno Workflow pipeline.

Tests the deterministic steps (classify through validate) without
requiring an LLM or database connection. The LLM respond step is
tested separately with mocking.
"""

import json
import pytest

from agno.workflow.types import StepInput, StepOutput
from src.agent.workflow import (
    _step_classify,
    _step_parse,
    _step_apply_defaults,
    _step_sre,
    _step_bom,
    _step_pricing,
    _step_validate,
    _is_not_accessories_only,
)


def _make_input(text: str, previous_outputs: dict = None) -> StepInput:
    """Helper to create a StepInput with optional previous step outputs."""
    return StepInput(
        input=text,
        previous_step_outputs=previous_outputs,
    )


class TestStepClassify:
    def test_roof_system(self):
        result = _step_classify(_make_input("Isodec 100 mm techo completo"))
        data = json.loads(result.content)
        assert data["request_type"] == "roof_system"
        assert data["has_roof"] is True

    def test_wall_system(self):
        result = _step_classify(_make_input("Isopanel 50 mm pared"))
        data = json.loads(result.content)
        assert data["request_type"] == "wall_system"

    def test_returns_step_output(self):
        result = _step_classify(_make_input("hola"))
        assert isinstance(result, StepOutput)
        assert result.content is not None


class TestStepParse:
    def test_parse_isodec(self):
        result = _step_parse(_make_input("Isodec EPS 100 mm 6 paneles de 6.5 mts techo"))
        data = json.loads(result.content)
        assert data["familia"] == "ISODEC"
        assert data["sub_familia"] == "EPS"
        assert data["thickness_mm"] == 100

    def test_parse_dimensions(self):
        result = _step_parse(_make_input("techo 7 x 10 Isodec 100 mm"))
        data = json.loads(result.content)
        assert data["geometry"]["width_m"] == 7.0
        assert data["geometry"]["length_m"] == 10.0


class TestStepApplyDefaults:
    def test_applies_defaults_in_pre_mode(self):
        classify_output = StepOutput(
            step_name="classify",
            content=json.dumps({"operating_mode": "pre_cotizacion", "request_type": "roof_system"}),
        )
        parse_output = StepOutput(
            step_name="parse",
            content=json.dumps({
                "familia": "ISODEC", "sub_familia": "EPS",
                "thickness_mm": 100, "uso": "techo",
                "structure_type": None, "span_m": None,
                "geometry": {"length_m": 5, "width_m": 10},
                "assumptions_used": [],
            }),
        )

        step_input = StepInput(
            input="test",
            previous_step_outputs={
                "classify": classify_output,
                "parse": parse_output,
            },
        )

        result = _step_apply_defaults(step_input)
        data = json.loads(result.content)
        parsed = data["parsed"]
        assert parsed["structure_type"] == "metal"
        assert parsed["span_m"] == 1.5
        assert len(parsed["assumptions_used"]) >= 2

    def test_no_defaults_in_formal_mode(self):
        classify_output = StepOutput(
            step_name="classify",
            content=json.dumps({"operating_mode": "formal", "request_type": "roof_system"}),
        )
        parse_output = StepOutput(
            step_name="parse",
            content=json.dumps({
                "familia": "ISODEC", "uso": "techo",
                "structure_type": None, "span_m": None,
                "geometry": {},
                "assumptions_used": [],
            }),
        )

        step_input = StepInput(
            input="test",
            previous_step_outputs={
                "classify": classify_output,
                "parse": parse_output,
            },
        )

        result = _step_apply_defaults(step_input)
        data = json.loads(result.content)
        parsed = data["parsed"]
        assert parsed["structure_type"] is None
        assert parsed["span_m"] is None


class TestConditionAccessoriesOnly:
    def test_not_accessories_returns_true(self):
        defaults_output = StepOutput(
            step_name="apply_defaults",
            content=json.dumps({
                "classification": {"request_type": "roof_system"},
                "parsed": {},
                "mode": "pre_cotizacion",
            }),
        )
        step_input = StepInput(
            input="test",
            previous_step_outputs={"apply_defaults": defaults_output},
        )
        assert _is_not_accessories_only(step_input) is True

    def test_accessories_only_returns_false(self):
        defaults_output = StepOutput(
            step_name="apply_defaults",
            content=json.dumps({
                "classification": {"request_type": "accessories_only"},
                "parsed": {},
                "mode": "pre_cotizacion",
            }),
        )
        step_input = StepInput(
            input="test",
            previous_step_outputs={"apply_defaults": defaults_output},
        )
        assert _is_not_accessories_only(step_input) is False


class TestStepSRE:
    def test_sre_low_risk(self):
        defaults_output = StepOutput(
            step_name="apply_defaults",
            content=json.dumps({
                "parsed": {
                    "familia": "ISOPANEL", "sub_familia": "EPS",
                    "thickness_mm": 50, "uso": "pared",
                    "structure_type": "metal",
                    "geometry": {"length_m": 10, "width_m": 2.5, "panel_lengths": []},
                    "raw_text": "",
                    "incomplete_fields": [],
                },
                "mode": "pre_cotizacion",
            }),
        )
        step_input = StepInput(
            input="test",
            previous_step_outputs={"apply_defaults": defaults_output},
        )
        result = _step_sre(step_input)
        data = json.loads(result.content)
        assert data["r_sistema"] == 0


class TestStepBOM:
    def test_bom_generation(self):
        defaults_output = StepOutput(
            step_name="apply_defaults",
            content=json.dumps({
                "parsed": {
                    "familia": "ISODEC", "sub_familia": "EPS",
                    "thickness_mm": 100, "uso": "techo",
                    "structure_type": "metal", "span_m": 1.5,
                    "roof_type": None,
                    "geometry": {
                        "length_m": 5.0, "width_m": 11.0,
                        "panel_count": None, "panel_lengths": [],
                    },
                },
                "mode": "pre_cotizacion",
            }),
        )
        step_input = StepInput(
            input="test",
            previous_step_outputs={"apply_defaults": defaults_output},
        )
        result = _step_bom(step_input)
        data = json.loads(result.content)
        assert data["panel_count"] >= 10
        assert data["area_m2"] == 55.0


class TestStepPricing:
    def test_pricing_lookup(self):
        defaults_output = StepOutput(
            step_name="apply_defaults",
            content=json.dumps({
                "parsed": {
                    "familia": "ISODEC", "sub_familia": "EPS",
                    "thickness_mm": 100, "uso": "techo",
                    "iva_mode": "incluido",
                },
                "mode": "pre_cotizacion",
            }),
        )
        bom_output = StepOutput(
            step_name="bom",
            content=json.dumps({
                "system_key": "techo_isodec_eps",
                "area_m2": 55.0,
                "panel_count": 10,
                "supports_per_panel": 2,
                "fixation_points": 40,
                "items": [
                    {"tipo": "panel", "referencia": "ISODEC_EPS_100mm", "quantity": 10, "unit": "unid"},
                ],
                "warnings": [],
            }),
        )
        step_input = StepInput(
            input="test",
            previous_step_outputs={
                "apply_defaults": defaults_output,
                "bom": bom_output,
            },
        )
        result = _step_pricing(step_input)
        data = json.loads(result.content)
        assert "items" in data
        assert data["iva_mode"] == "incluido"


class TestStepValidate:
    def test_validation_output(self):
        defaults_output = StepOutput(
            step_name="apply_defaults",
            content=json.dumps({
                "parsed": {
                    "familia": "ISODEC", "sub_familia": "EPS",
                    "thickness_mm": 100, "uso": "techo",
                    "structure_type": "metal", "span_m": 1.5,
                    "geometry": {"length_m": 5, "width_m": 11},
                    "include_accessories": True,
                    "include_shipping": False,
                    "client": {"name": None, "phone": None, "location": None},
                    "raw_text": "test",
                    "incomplete_fields": [],
                    "assumptions_used": [],
                    "iva_mode": "incluido",
                    "roof_type": None,
                    "raw_accessories_requested": [],
                    "include_fixings": True,
                },
                "classification": {"request_type": "roof_system"},
                "mode": "pre_cotizacion",
            }),
        )
        sre_output = StepOutput(
            step_name="sre",
            content=json.dumps({
                "score": 15, "level": "formal_certified",
                "r_datos": 0, "r_autoportancia": 0,
                "r_geometria": 0, "r_sistema": 5,
                "breakdown": [], "recommendations": [],
                "alternative_thicknesses": [],
            }),
        )
        bom_output = StepOutput(
            step_name="bom",
            content=json.dumps({
                "system_key": "techo_isodec_eps", "area_m2": 55.0,
                "panel_count": 10, "supports_per_panel": 2,
                "fixation_points": 40, "items": [], "warnings": [],
            }),
        )
        pricing_output = StepOutput(
            step_name="pricing",
            content=json.dumps({
                "items": [], "subtotal_panels_usd": 0,
                "subtotal_accessories_usd": 0, "subtotal_total_usd": 0,
                "iva_mode": "incluido", "warnings": [], "missing_prices": [],
            }),
        )
        step_input = StepInput(
            input="test",
            previous_step_outputs={
                "apply_defaults": defaults_output,
                "sre": sre_output,
                "bom": bom_output,
                "pricing": pricing_output,
            },
        )
        result = _step_validate(step_input)
        data = json.loads(result.content)
        assert "quote_id" in data
        assert data["quote_id"].startswith("PV5-")
        assert "validation" in data
        assert "mode" in data
