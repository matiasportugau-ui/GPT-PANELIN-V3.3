"""
Panelin v4.0 - Engine Tests
==============================

pytest-based test suite for the quotation engine pipeline.

Run: python -m pytest panelin_v4/tests/test_engine.py -v
"""

import pytest

from panelin_v4.engine.classifier import classify_request, RequestType, OperatingMode
from panelin_v4.engine.parser import parse_request
from panelin_v4.engine.sre_engine import calculate_sre, QuotationLevel
from panelin_v4.engine.bom_engine import calculate_bom
from panelin_v4.engine.quotation_engine import process_quotation
from panelin_v4.evaluator.sai_engine import calculate_sai
from panelin_v4.evaluator.regression_suite import run_regression_suite


# ──────────────────── Classifier Tests ──────────────────────

class TestClassifier:
    def test_roof_detection(self):
        result = classify_request("Isodec 100 mm / 6 paneles de 6.5 m / techo completo")
        assert result.has_roof is True
        assert result.request_type in (RequestType.ROOF_SYSTEM, RequestType.MIXED)

    def test_wall_detection(self):
        result = classify_request("Isopanel 50 mm / 13 paneles de 2.60 mts / pared")
        assert result.has_wall is True
        assert result.request_type == RequestType.WALL_SYSTEM

    def test_update_detection(self):
        result = classify_request("Actualizar cotización - agregar 1 panel")
        assert result.is_update is True
        assert result.request_type == RequestType.UPDATE

    def test_accessories_only(self):
        result = classify_request("12 Goteros Frontales 100 mm + 8 Goteros Laterales 100 mm")
        assert result.has_accessories is True

    def test_formal_mode_detection(self):
        result = classify_request("Isodec 100 mm PDF formal")
        assert result.operating_mode == OperatingMode.FORMAL

    def test_force_mode(self):
        result = classify_request(
            "Isodec 100 mm / 6 paneles",
            force_mode=OperatingMode.FORMAL,
        )
        assert result.operating_mode == OperatingMode.FORMAL


# ──────────────────── Parser Tests ──────────────────────

class TestParser:
    def test_basic_parsing(self):
        req = parse_request("Isodec EPS 100 mm / 6 paneles de 6,5 mts / techo completo a H°")
        assert req.familia == "ISODEC"
        assert req.sub_familia == "EPS"
        assert req.thickness_mm == 100
        assert req.uso == "techo"
        assert req.structure_type == "hormigon"

    def test_panel_lengths(self):
        req = parse_request("3 paneles de 2,30 m + 1 panel de 3,05 m")
        assert len(req.geometry.panel_lengths) == 4
        assert req.geometry.panel_lengths[0] == 2.30
        assert req.geometry.panel_lengths[3] == 3.05

    def test_dimensions(self):
        req = parse_request("techo 7 x 10 Isodec 100 mm")
        assert req.geometry.width_m == 7.0
        assert req.geometry.length_m == 10.0

    def test_isoroof_detection(self):
        req = parse_request("Isoroof 50 mm / 22 paneles de 4.60 m / techo 2 aguas")
        assert req.familia == "ISOROOF"
        assert req.thickness_mm == 50
        assert req.roof_type == "2_aguas"

    def test_isopanel_wall(self):
        req = parse_request("Isopanel 100 mm / 14 paneles de 2.4 m / pared")
        assert req.familia == "ISOPANEL"
        assert req.uso == "pared"

    def test_flete_detection(self):
        req = parse_request("Isodec 100 mm / 6 paneles + flete")
        assert req.include_shipping is True

    def test_thickness_cm(self):
        req = parse_request("chapa de 10 cm")
        assert req.thickness_mm == 100

    def test_incomplete_marks_fields(self):
        req = parse_request("Isodec / techo")
        assert "thickness_mm" in req.incomplete_fields

    def test_never_raises(self):
        req = parse_request("")
        assert req is not None
        assert len(req.incomplete_fields) > 0

    def test_subfamilia_inference(self):
        req = parse_request("Isodec 100 mm / techo")
        assert req.sub_familia == "EPS"

    def test_height_detection(self):
        req = parse_request("Isopanel 100 mm / pared altura 2,5 m")
        assert req.geometry.height_m == 2.5


# ──────────────────── SRE Tests ──────────────────────

class TestSRE:
    def test_complete_low_risk(self):
        req = parse_request("Isodec EPS 100 mm / 6 paneles de 4.5 mts / techo a metal")
        req.span_m = 4.5
        sre = calculate_sre(req)
        assert sre.score <= 30
        assert sre.level == QuotationLevel.LEVEL_3_FORMAL

    def test_missing_span_high_risk(self):
        req = parse_request("Isodec 100 mm / techo 7 x 10")
        sre = calculate_sre(req)
        assert sre.r_datos >= 40  # span missing penalty

    def test_wall_low_risk(self):
        req = parse_request("Isopanel 50 mm / 13 paneles de 2.60 mts / pared")
        sre = calculate_sre(req)
        assert sre.r_sistema == 0  # walls have no structural risk

    def test_autoportancia_exceeded(self):
        req = parse_request("Isodec EPS 100 mm / techo")
        req.span_m = 7.0  # exceeds 5.5m capacity
        sre = calculate_sre(req)
        assert sre.r_autoportancia == 50
        assert len(sre.alternative_thicknesses) > 0

    def test_geometry_risk(self):
        req = parse_request("Isodec 100 mm / techo mariposa / 8 paneles")
        sre = calculate_sre(req)
        assert sre.r_geometria > 0


# ──────────────────── BOM Tests ──────────────────────

class TestBOM:
    def test_roof_bom_complete(self):
        bom = calculate_bom(
            familia="ISODEC", sub_familia="EPS", thickness_mm=100,
            uso="techo", length_m=5.0, width_m=11.0, structure_type="metal",
        )
        assert bom.panel_count >= 10
        assert bom.area_m2 == 55.0
        item_types = [i.tipo for i in bom.items]
        assert "panel" in item_types
        assert "gotero_frontal" in item_types
        assert "gotero_lateral" in item_types
        assert "varilla" in item_types

    def test_wall_bom(self):
        bom = calculate_bom(
            familia="ISOPANEL", sub_familia="EPS", thickness_mm=100,
            uso="pared", length_m=10.0, width_m=2.5, structure_type="metal",
        )
        assert bom.panel_count > 0
        item_types = [i.tipo for i in bom.items]
        assert "perfil_u" in item_types

    def test_hormigon_includes_tacos(self):
        bom = calculate_bom(
            familia="ISODEC", sub_familia="EPS", thickness_mm=100,
            uso="techo", length_m=5.0, width_m=5.0, structure_type="hormigon",
        )
        item_types = [i.tipo for i in bom.items]
        assert "taco" in item_types

    def test_cumbrera_for_2_aguas(self):
        bom = calculate_bom(
            familia="ISODEC", sub_familia="EPS", thickness_mm=150,
            uso="techo", length_m=6.5, width_m=10.0, structure_type="metal",
            roof_type="2_aguas",
        )
        item_types = [i.tipo for i in bom.items]
        assert "cumbrera" in item_types


# ──────────────────── Orchestrator Tests ──────────────────────

class TestOrchestrator:
    def test_full_pipeline(self):
        output = process_quotation(
            "Isodec EPS 100 mm / 6 paneles de 6.5 mts / techo completo a metal + flete",
            client_name="Test",
            client_location="Montevideo",
        )
        assert output.quote_id.startswith("PV4-")
        assert output.mode in ("pre_cotizacion", "formal", "informativo")
        assert output.bom.get("panel_count", 0) > 0

    def test_pre_mode_never_blocks(self):
        output = process_quotation(
            "Isodec 100 mm / techo 7 x 10",
            force_mode=OperatingMode.PRE_COTIZACION,
        )
        assert output.status != "blocked"

    def test_accessories_only(self):
        output = process_quotation(
            "12 Goteros Frontales 100 mm + 8 Goteros Laterales 100 mm + flete",
        )
        assert output.status != "blocked"

    def test_batch_processing(self):
        from panelin_v4.engine.quotation_engine import process_batch
        results = process_batch([
            {"text": "Isodec 100 mm / 6 paneles de 5 mts"},
            {"text": "Isopanel 50 mm / 13 paneles de 2.60 mts"},
        ])
        assert len(results) == 2


# ──────────────────── SAI Tests ──────────────────────

class TestSAI:
    def test_good_quotation_high_sai(self):
        output = process_quotation(
            "Isodec EPS 100 mm / 10 paneles de 5 mts / techo completo a metal + flete",
            client_name="Test",
            client_location="Montevideo",
        )
        sai = calculate_sai(output)
        assert sai.score >= 50

    def test_sai_grade(self):
        output = process_quotation(
            "Isopanel EPS 50 mm / 6 paneles de 2.50 mts / pared",
        )
        sai = calculate_sai(output)
        assert sai.grade in ("A", "B", "C", "D", "F")


# ──────────────────── Regression Suite Tests ──────────────────────

class TestRegressionSuite:
    def test_regression_runs(self):
        results = run_regression_suite()
        assert results["total"] > 0
        assert results["pass_rate"] >= 0

    def test_pass_rate_above_minimum(self):
        results = run_regression_suite()
        assert results["pass_rate"] >= 60, (
            f"Regression pass rate {results['pass_rate']}% below minimum 60%"
        )
