"""Comprehensive tests for business-rule validators."""

from __future__ import annotations

import math

import pytest

from panelin_sheets_orchestrator.validators import (
    AUTOPORTANCIA,
    USEFUL_WIDTH,
    calculate_fixing_points,
    calculate_nuts,
    calculate_panels_needed,
    calculate_rods,
    calculate_supports,
    compute_bom_summary,
    validate_autoportancia,
    validate_bom_quantities,
    validate_dimensions,
    validate_price,
    validate_write_plan_values,
)


class TestAutoportancia:
    def test_valid_span_isodec_eps_100(self):
        result = validate_autoportancia("ISODEC_EPS", 100, 4.0, safety_margin=0.15)
        assert result.valid
        assert result.details["span_max_nominal_m"] == 5.5

    def test_valid_span_with_safety_warning(self):
        result = validate_autoportancia("ISODEC_EPS", 100, 5.0, safety_margin=0.15)
        assert result.valid
        assert len(result.warnings) > 0
        assert "margen" in result.warnings[0].lower()

    def test_exceeds_nominal(self):
        result = validate_autoportancia("ISODEC_EPS", 100, 6.0)
        assert not result.valid
        assert any("excede" in e.lower() for e in result.errors)

    def test_unknown_family(self):
        result = validate_autoportancia("UNKNOWN_PANEL", 100, 3.0)
        assert not result.valid
        assert "desconocida" in result.errors[0].lower()

    def test_invalid_thickness(self):
        result = validate_autoportancia("ISODEC_EPS", 75, 3.0)
        assert not result.valid
        assert "espesor" in result.errors[0].lower()

    def test_alternatives_suggested(self):
        result = validate_autoportancia("ISODEC_EPS", 100, 6.0)
        assert not result.valid
        alternatives = result.details.get("alternatives", [])
        assert len(alternatives) > 0
        assert all(a["max_span_m"] > 5.5 for a in alternatives)

    def test_all_families_have_entries(self):
        for family, table in AUTOPORTANCIA.items():
            for thickness, span in table.items():
                result = validate_autoportancia(family, thickness, span * 0.5)
                assert result.valid, f"{family} {thickness}mm failed"

    def test_isoroof_3g(self):
        result = validate_autoportancia("ISOROOF_3G", 30, 2.0)
        assert result.valid
        assert result.details["span_max_nominal_m"] == 2.8

    def test_isofrig_pir(self):
        result = validate_autoportancia("ISOFRIG_PIR", 100, 5.0)
        assert result.valid

    def test_no_alternatives_when_maxed_out(self):
        result = validate_autoportancia("ISOROOF_3G", 80, 5.0)
        assert not result.valid
        if not result.details.get("alternatives"):
            assert any("apoyos intermedios" in w.lower() for w in result.warnings)

    def test_hyphen_in_family_name(self):
        result = validate_autoportancia("ISODEC-EPS", 100, 3.0)
        assert result.valid

    def test_zero_safety_margin(self):
        result = validate_autoportancia("ISODEC_EPS", 100, 5.5, safety_margin=0.0)
        assert result.valid
        assert len(result.warnings) == 0


class TestDimensions:
    def test_valid_dimensions(self):
        result = validate_dimensions(6.0, 10.0)
        assert result.valid

    def test_length_too_short(self):
        result = validate_dimensions(0.1, 5.0)
        assert not result.valid

    def test_length_too_long(self):
        result = validate_dimensions(15.0, 5.0)
        assert not result.valid

    def test_width_too_small(self):
        result = validate_dimensions(5.0, 0.05)
        assert not result.valid

    def test_boundary_values(self):
        assert validate_dimensions(0.5, 0.1).valid
        assert validate_dimensions(14.0, 100.0).valid


class TestBOMCalculations:
    def test_panels_needed_exact(self):
        assert calculate_panels_needed(5.6, 1.12) == 5

    def test_panels_needed_ceil(self):
        assert calculate_panels_needed(6.0, 1.12) == 6

    def test_panels_needed_wide(self):
        assert calculate_panels_needed(1.0, 1.14) == 1

    def test_supports_basic(self):
        assert calculate_supports(5.5, 5.5) == 2

    def test_supports_long_span(self):
        assert calculate_supports(12.0, 5.5) == 4

    def test_supports_minimum(self):
        assert calculate_supports(1.0, 10.0) == 2

    def test_fixing_points_roof(self):
        pts = calculate_fixing_points(5, 3, 6.0, "techo")
        assert pts > 0
        assert pts == math.ceil((5 * 3 * 2) + (6.0 * 2 / 2.5))

    def test_fixing_points_wall(self):
        pts = calculate_fixing_points(5, 3, 6.0, "pared")
        assert pts == math.ceil(5 * 3 * 2)

    def test_rods(self):
        assert calculate_rods(16) == 4
        assert calculate_rods(17) == 5
        assert calculate_rods(1) == 1

    def test_nuts_metal(self):
        assert calculate_nuts(10, "metal") == 20

    def test_nuts_concrete(self):
        assert calculate_nuts(10, "hormigon") == 10


class TestBOMQuantityValidation:
    def test_valid_quantities(self):
        items = [
            {"name": "panel", "quantity": 5},
            {"name": "rod", "quantity": 2},
        ]
        result = validate_bom_quantities(items)
        assert result.valid

    def test_zero_quantity(self):
        items = [{"name": "panel", "quantity": 0}]
        result = validate_bom_quantities(items)
        assert not result.valid

    def test_negative_quantity(self):
        items = [{"name": "panel", "quantity": -1}]
        result = validate_bom_quantities(items)
        assert not result.valid

    def test_non_integer_warns(self):
        items = [{"name": "panel", "quantity": 4.5}]
        result = validate_bom_quantities(items)
        assert result.valid
        assert len(result.warnings) > 0

    def test_missing_quantity(self):
        items = [{"name": "panel"}]
        result = validate_bom_quantities(items)
        assert not result.valid


class TestPriceValidation:
    def test_normal_price(self):
        assert validate_price(46.07).valid

    def test_negative_price(self):
        assert not validate_price(-10.0).valid

    def test_high_price_warns(self):
        result = validate_price(600.0)
        assert result.valid
        assert len(result.warnings) > 0


class TestWritePlanValues:
    def test_formula_rejected(self):
        writes = [{"range": "A1", "values": [["=SUM(B1:B10)"]]}]
        result = validate_write_plan_values(writes, {})
        assert not result.valid
        assert "fórmula" in result.errors[0].lower()

    def test_formula_in_non_first_cell_rejected(self):
        """Formulas in any cell position must be caught, not just [0][0]."""
        writes = [{"range": "A1:C2", "values": [
            ["ok", "fine", "=SUM(X1:X9)"],
            ["also ok", "=VLOOKUP()", "safe"],
        ]}]
        result = validate_write_plan_values(writes, {})
        assert not result.valid
        assert len(result.errors) == 2

    def test_valid_values(self):
        writes = [{"range": "A1", "values": [["hello"]]}]
        result = validate_write_plan_values(writes, {})
        assert result.valid

    def test_multi_row_valid(self):
        writes = [{"range": "A1:B3", "values": [
            ["a", "b"],
            ["c", "d"],
            ["e", "f"],
        ]}]
        result = validate_write_plan_values(writes, {})
        assert result.valid

    def test_date_hint_warns_on_bad_format(self):
        writes = [{"range": "EPS_100!F3", "values": [["not-a-date"]]}]
        hints = {"cells": {"fecha": "EPS_100!F3"}}
        result = validate_write_plan_values(writes, hints)
        assert len(result.warnings) > 0

    def test_date_hint_ok(self):
        writes = [{"range": "EPS_100!F3", "values": [["2026-02-25"]]}]
        hints = {"cells": {"fecha": "EPS_100!F3"}}
        result = validate_write_plan_values(writes, hints)
        assert len(result.warnings) == 0


class TestComputeBOMSummary:
    def test_full_bom_isodec_eps(self):
        result = compute_bom_summary(
            product_family="ISODEC_EPS",
            thickness_mm=100,
            length_m=4.0,
            width_m=10.0,
            usage="techo",
            structure="metal",
        )
        assert result.valid
        d = result.details
        assert d["panels_needed"] == math.ceil(10.0 / 1.12)
        assert d["supports"] >= 2
        assert d["area_m2"] == 40.0
        assert d["fixing_points"] > 0
        assert d["rods_varilla_3_8"] > 0
        assert d["nuts_tuercas"] > 0

    def test_bom_invalid_span(self):
        result = compute_bom_summary(
            product_family="ISODEC_EPS",
            thickness_mm=100,
            length_m=8.0,
            width_m=5.0,
        )
        assert not result.valid

    def test_bom_isopanel_wall(self):
        result = compute_bom_summary(
            product_family="ISOPANEL_EPS",
            thickness_mm=100,
            length_m=4.0,
            width_m=20.0,
            usage="pared",
        )
        assert result.valid
        assert result.details["usage"] == "pared"
