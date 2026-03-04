"""
Integration tests for the QuotationService layer.

Verifies that the service wrapper correctly delegates to the panelin_v4 engine
and that all pipeline stages produce valid results.
"""

from __future__ import annotations

import json
import pytest

from panelin_v4.engine.classifier import OperatingMode
from src.quotation.service import QuotationService


class TestQuotationServiceClassify:
    def test_classify_roof_request(self):
        result = QuotationService.classify("Necesito ISODEC 100mm para techo de 10x7")
        assert result.request_type.value == "roof_system"
        assert result.has_roof is True

    def test_classify_wall_request(self):
        result = QuotationService.classify("Quiero ISOPANEL de 80mm para pared")
        assert result.request_type.value == "wall_system"
        assert result.has_wall is True

    def test_classify_accessories_only(self):
        result = QuotationService.classify("Necesito 10 tornillos y 20 arandelas")
        assert result.request_type.value == "accessories_only"
        assert result.has_accessories is True

    def test_classify_formal_mode(self):
        result = QuotationService.classify(
            "Cotización formal para techo ISODEC 100mm", 
            force_mode=OperatingMode.FORMAL,
        )
        assert result.operating_mode == OperatingMode.FORMAL

    def test_classify_informativo_mode(self):
        result = QuotationService.classify("Qué espesores tienen?")
        assert result.operating_mode.value == "informativo"


class TestQuotationServiceParse:
    def test_parse_complete_request(self):
        result = QuotationService.parse(
            "6 paneles ISODEC EPS de 100mm, 6.5 mts de largo, para techo sobre metal"
        )
        assert result.familia == "ISODEC"
        assert result.sub_familia == "EPS"
        assert result.thickness_mm == 100
        assert result.uso == "techo"
        assert result.structure_type == "metal"

    def test_parse_wall_request(self):
        result = QuotationService.parse("ISOPANEL 80mm para pared de 15x3")
        assert result.familia == "ISOPANEL"
        assert result.thickness_mm == 80
        assert result.uso == "pared"

    def test_parse_missing_fields(self):
        result = QuotationService.parse("Paneles para techo")
        assert "familia" in result.incomplete_fields
        assert "thickness_mm" in result.incomplete_fields

    def test_parse_phone_detection(self):
        result = QuotationService.parse("ISODEC 100mm techo, mi tel es 099123456")
        assert result.client.phone == "099123456"


class TestQuotationServiceSRE:
    def test_sre_low_risk(self):
        request = QuotationService.parse(
            "ISODEC EPS 100mm para techo de 10x7 sobre metal, luz 3m"
        )
        sre = QuotationService.calculate_sre(request)
        assert sre.score <= 60

    def test_sre_missing_data_penalty(self):
        request = QuotationService.parse("Paneles para techo")
        sre = QuotationService.calculate_sre(request)
        assert sre.r_datos > 0


class TestQuotationServiceBOM:
    def test_bom_roof_calculation(self):
        request = QuotationService.parse(
            "6 paneles ISODEC EPS 100mm para techo de 10x7m sobre metal"
        )
        QuotationService.apply_defaults(request, OperatingMode.PRE_COTIZACION)
        bom = QuotationService.calculate_bom(request)
        assert bom.panel_count > 0
        assert bom.area_m2 > 0
        assert len(bom.items) > 0

    def test_bom_insufficient_data(self):
        request = QuotationService.parse("Paneles para techo")
        bom = QuotationService.calculate_bom(request)
        assert bom.panel_count == 0
        assert len(bom.warnings) > 0

    def test_bom_wall_calculation(self):
        request = QuotationService.parse(
            "ISOPANEL EPS 80mm para pared de 12x3m sobre metal"
        )
        QuotationService.apply_defaults(request, OperatingMode.PRE_COTIZACION)
        bom = QuotationService.calculate_bom(request)
        assert bom.panel_count > 0


class TestQuotationServicePricing:
    def test_pricing_with_bom(self):
        request = QuotationService.parse(
            "6 paneles ISODEC EPS 100mm para techo de 10x7m"
        )
        QuotationService.apply_defaults(request, OperatingMode.PRE_COTIZACION)
        bom = QuotationService.calculate_bom(request)
        pricing = QuotationService.calculate_pricing(bom, request)
        assert pricing.iva_mode == "incluido"

    def test_pricing_empty_bom(self):
        from panelin_v4.engine.bom_engine import BOMResult
        bom = BOMResult(
            system_key="unknown", area_m2=0,
            panel_count=0, supports_per_panel=0, fixation_points=0,
        )
        request = QuotationService.parse("Paneles")
        pricing = QuotationService.calculate_pricing(bom, request)
        assert pricing.subtotal_total_usd == 0


class TestQuotationServiceFullPipeline:
    def test_full_pipeline_roof(self):
        output = QuotationService.process_full(
            text="Necesito cotizar 6 paneles ISODEC EPS de 100mm, 6.5 mts de largo, para techo de 10x7 sobre estructura metálica",
            force_mode=OperatingMode.PRE_COTIZACION,
        )
        assert output.quote_id.startswith("PV4-")
        assert output.mode == "pre_cotizacion"
        assert output.status in ("draft", "validated", "requires_review")

    def test_full_pipeline_wall(self):
        output = QuotationService.process_full(
            text="ISOPANEL 80mm para pared de 15x3m sobre hormigón",
            force_mode=OperatingMode.PRE_COTIZACION,
        )
        assert output.quote_id.startswith("PV4-")

    def test_full_pipeline_formal(self):
        output = QuotationService.process_full(
            text="Cotización formal ISODEC EPS 100mm techo 10x7m, luz 3m, metal. Cliente: Juan Pérez, tel 099123456, Montevideo",
            force_mode=OperatingMode.FORMAL,
        )
        assert output.mode == "formal"

    def test_full_pipeline_batch(self):
        results = QuotationService.process_batch([
            {"text": "ISODEC 100mm techo 10x7"},
            {"text": "ISOPANEL 80mm pared 15x3"},
        ])
        assert len(results) == 2
        for r in results:
            assert r.quote_id.startswith("PV4-")


class TestQuotationServiceSAI:
    def test_sai_score(self):
        output = QuotationService.process_full(
            text="ISODEC EPS 100mm para techo de 10x7m sobre metal",
            force_mode=OperatingMode.PRE_COTIZACION,
        )
        sai = QuotationService.calculate_sai(output)
        assert 0 <= sai.score <= 100
        assert sai.grade in ("A", "B", "C", "D", "F")
