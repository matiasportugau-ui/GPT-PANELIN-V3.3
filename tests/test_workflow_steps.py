"""
Tests for src/agent/workflow.py — deterministic workflow steps.

Tests only the pure Python steps (no LLM calls).
Steps 2-7 are deterministic and cost $0.00.
"""

import json
import pytest

from agno.workflow.step import StepInput, StepOutput

from src.agent.workflow import (
    _step_classify,
    _step_parse,
    _step_sre,
    _step_bom,
    _step_pricing,
    _step_validate,
)


def _make_step_input(content: str, prev: str = None) -> StepInput:
    """Helper to create StepInput for testing."""
    return StepInput(input=content, previous_step_content=prev)


class TestClassifyStep:
    def test_roof_classification(self):
        understand_output = json.dumps({
            "texto_cotizacion": "Isodec EPS 100mm / 6 paneles de 6.5mts / techo a metal",
            "modo": "pre_cotizacion",
            "nombre_cliente": "Juan",
            "telefono_cliente": None,
            "ubicacion_cliente": "Montevideo",
            "es_consulta_info": False,
        })
        si = _make_step_input("", prev=understand_output)
        result = _step_classify(si)
        data = json.loads(result.content)
        assert data["classification"]["request_type"] == "roof_system"
        assert data["classification"]["has_roof"] is True
        assert data["skip_pipeline"] is False

    def test_info_query_skips_pipeline(self):
        understand_output = json.dumps({
            "texto_cotizacion": "¿Qué espesores tienen?",
            "modo": "informativo",
            "es_consulta_info": True,
            "consulta_info": "¿Qué espesores tienen disponibles?",
        })
        si = _make_step_input("", prev=understand_output)
        result = _step_classify(si)
        data = json.loads(result.content)
        assert data["skip_pipeline"] is True
        assert data["tipo"] == "info_query"


class TestParseStep:
    def test_parses_structured_data(self):
        prev = json.dumps({
            "classification": {"request_type": "roof_system"},
            "texto_cotizacion": "Isodec EPS 100mm / 6 paneles de 6.5mts / techo a H°",
            "modo": "pre_cotizacion",
            "nombre_cliente": "Test",
            "telefono_cliente": None,
            "ubicacion_cliente": None,
            "skip_pipeline": False,
        })
        si = _make_step_input("", prev=prev)
        result = _step_parse(si)
        data = json.loads(result.content)
        req = data["request"]
        assert req["familia"] == "ISODEC"
        assert req["sub_familia"] == "EPS"
        assert req["thickness_mm"] == 100
        assert req["uso"] == "techo"

    def test_skips_on_info_query(self):
        prev = json.dumps({"skip_pipeline": True, "tipo": "info_query"})
        si = _make_step_input("", prev=prev)
        result = _step_parse(si)
        data = json.loads(result.content)
        assert data["skip_pipeline"] is True


class TestSREStep:
    def test_calculates_risk_score(self):
        prev = json.dumps({
            "classification": {"request_type": "roof_system"},
            "texto_cotizacion": "Isodec EPS 100mm",
            "modo": "pre_cotizacion",
            "skip_pipeline": False,
            "request": {
                "familia": "ISODEC",
                "sub_familia": "EPS",
                "thickness_mm": 100,
                "uso": "techo",
                "structure_type": "metal",
                "span_m": None,
                "geometry": {"length_m": 6.5, "width_m": None, "height_m": None,
                             "panel_count": 6, "panel_lengths": []},
                "client": {"name": None, "phone": None, "location": None},
                "include_accessories": True,
                "include_fixings": True,
                "include_shipping": False,
                "iva_mode": "incluido",
                "roof_type": None,
                "raw_accessories_requested": [],
                "raw_text": "Isodec EPS 100mm",
                "incomplete_fields": [],
                "assumptions_used": [],
            },
        })
        si = _make_step_input("", prev=prev)
        result = _step_sre(si)
        data = json.loads(result.content)
        assert "sre" in data
        assert "score" in data["sre"]
        assert isinstance(data["sre"]["score"], int)


class TestBOMStep:
    def test_calculates_bom_for_roof(self):
        prev = json.dumps({
            "classification": {"request_type": "roof_system"},
            "modo": "pre_cotizacion",
            "skip_pipeline": False,
            "request": {
                "familia": "ISODEC",
                "sub_familia": "EPS",
                "thickness_mm": 100,
                "uso": "techo",
                "structure_type": "metal",
                "span_m": None,
                "geometry": {"length_m": 5.0, "width_m": 11.0, "height_m": None,
                             "panel_count": None, "panel_lengths": []},
                "client": {"name": None, "phone": None, "location": None},
                "include_accessories": True,
                "include_fixings": True,
                "include_shipping": False,
                "iva_mode": "incluido",
                "roof_type": None,
                "raw_accessories_requested": [],
                "raw_text": "Isodec 100mm techo 5x11",
                "incomplete_fields": [],
                "assumptions_used": [],
            },
            "sre": {"score": 20, "level": "formal_certified",
                    "r_datos": 0, "r_autoportancia": 0, "r_geometria": 0, "r_sistema": 5,
                    "breakdown": [], "recommendations": [], "alternative_thicknesses": []},
        })
        si = _make_step_input("", prev=prev)
        result = _step_bom(si)
        data = json.loads(result.content)
        assert "bom" in data
        assert data["bom"]["panel_count"] >= 10
        assert data["bom"]["area_m2"] == 55.0

    def test_skips_bom_for_accessories_only(self):
        prev = json.dumps({
            "classification": {"request_type": "accessories_only"},
            "modo": "pre_cotizacion",
            "skip_pipeline": False,
            "request": {
                "familia": None, "sub_familia": None, "thickness_mm": None,
                "uso": None, "structure_type": None, "span_m": None,
                "geometry": {"length_m": None, "width_m": None, "height_m": None,
                             "panel_count": None, "panel_lengths": []},
                "client": {"name": None, "phone": None, "location": None},
                "include_accessories": True, "include_fixings": True,
                "include_shipping": False, "iva_mode": "incluido",
                "roof_type": None, "raw_accessories_requested": ["gotero"],
                "raw_text": "12 goteros", "incomplete_fields": [], "assumptions_used": [],
            },
            "sre": {"score": 0, "level": "formal_certified",
                    "r_datos": 0, "r_autoportancia": 0, "r_geometria": 0, "r_sistema": 0,
                    "breakdown": [], "recommendations": [], "alternative_thicknesses": []},
        })
        si = _make_step_input("", prev=prev)
        result = _step_bom(si)
        data = json.loads(result.content)
        assert data.get("bom_skipped") is True


class TestPricingStep:
    def test_calculates_pricing(self):
        prev = json.dumps({
            "classification": {"request_type": "roof_system"},
            "modo": "pre_cotizacion",
            "skip_pipeline": False,
            "request": {
                "familia": "ISODEC", "sub_familia": "EPS", "thickness_mm": 100,
                "uso": "techo", "structure_type": "metal", "span_m": None,
                "geometry": {"length_m": 5.0, "width_m": 11.0, "height_m": None,
                             "panel_count": 10, "panel_lengths": []},
                "client": {"name": None, "phone": None, "location": None},
                "include_accessories": True, "include_fixings": True,
                "include_shipping": False, "iva_mode": "incluido",
                "roof_type": None, "raw_accessories_requested": [],
                "raw_text": "", "incomplete_fields": [], "assumptions_used": [],
            },
            "bom": {
                "system_key": "techo_isodec_eps",
                "area_m2": 55.0,
                "panel_count": 10,
                "supports_per_panel": 3,
                "fixation_points": 72,
                "items": [
                    {"tipo": "panel", "referencia": "ISODEC_EPS_100mm",
                     "sku": None, "name": None, "quantity": 10,
                     "unit": "unid", "formula_used": "", "notes": ""},
                ],
                "warnings": [],
            },
            "sre": {"score": 20},
        })
        si = _make_step_input("", prev=prev)
        result = _step_pricing(si)
        data = json.loads(result.content)
        assert "pricing" in data


class TestValidateStep:
    def test_validates_quotation(self):
        prev = json.dumps({
            "classification": {"request_type": "roof_system"},
            "modo": "pre_cotizacion",
            "skip_pipeline": False,
            "assumptions": [],
            "request": {
                "familia": "ISODEC", "sub_familia": "EPS", "thickness_mm": 100,
                "uso": "techo", "structure_type": "metal", "span_m": None,
                "geometry": {"length_m": 5.0, "width_m": 11.0, "height_m": None,
                             "panel_count": 10, "panel_lengths": []},
                "client": {"name": "Test", "phone": None, "location": None},
                "include_accessories": True, "include_fixings": True,
                "include_shipping": False, "iva_mode": "incluido",
                "roof_type": None, "raw_accessories_requested": [],
                "raw_text": "", "incomplete_fields": [],
                "assumptions_used": [],
            },
            "sre": {
                "score": 20, "level": "formal_certified",
                "r_datos": 0, "r_autoportancia": 0, "r_geometria": 0, "r_sistema": 5,
                "breakdown": [], "recommendations": [], "alternative_thicknesses": [],
            },
            "bom": {
                "system_key": "techo_isodec_eps",
                "area_m2": 55.0, "panel_count": 10,
                "supports_per_panel": 3, "fixation_points": 72,
                "items": [
                    {"tipo": "panel", "referencia": "ISODEC_EPS_100mm",
                     "sku": None, "name": None, "quantity": 10,
                     "unit": "unid", "formula_used": "", "notes": ""},
                ],
                "warnings": [],
            },
            "pricing": {
                "items": [],
                "subtotal_panels_usd": 0, "subtotal_accessories_usd": 0,
                "subtotal_total_usd": 0, "iva_mode": "incluido",
                "warnings": [], "missing_prices": [],
            },
        })
        si = _make_step_input("", prev=prev)
        result = _step_validate(si)
        data = json.loads(result.content)
        assert "validation" in data
        assert "quote_id" in data
        assert data["quote_id"].startswith("PV5-")
        assert "sai" in data
