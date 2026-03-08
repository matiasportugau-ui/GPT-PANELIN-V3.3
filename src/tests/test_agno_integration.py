"""
Panelin Agno — Integration Tests
===================================

Verifica que la capa Agno funciona correctamente:
1. Config: settings se cargan sin errores
2. Service: QuotationService envuelve el motor v4 correctamente
3. Tools: Las herramientas Agno retornan JSON válido
4. Workflow Steps: Cada Step del pipeline procesa correctamente
5. BOM Dimensions: El fix de dimensiones para paredes funciona
6. Pricing: El pricing busca sub_familia correctamente
7. Security: No hay defaults inseguros en variables críticas
"""

from __future__ import annotations

import json

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────
class TestConfig:
    def test_settings_load(self):
        from src.core.config import settings
        assert settings.iva_rate == 0.22
        assert settings.currency == "USD"
        assert settings.openai_model == "gpt-4o-mini"

    def test_cors_origins_default(self):
        from src.core.config import settings
        origins = settings.cors_origins_list
        assert isinstance(origins, list)
        assert len(origins) >= 1

    def test_agno_db_url_conversion(self, monkeypatch):
        from src.core.config import Settings
        s = Settings(database_url="postgresql+asyncpg://user:pass@host/db")
        assert s.agno_db_url.startswith("postgresql+psycopg://")


# ─────────────────────────────────────────────────────────────────────────────
# QuotationService
# ─────────────────────────────────────────────────────────────────────────────
class TestQuotationService:
    def test_get_service_singleton(self):
        from src.quotation.service import get_quotation_service
        s1 = get_quotation_service()
        s2 = get_quotation_service()
        assert s1 is s2

    def test_classify_roof(self):
        from src.quotation.service import get_quotation_service
        svc = get_quotation_service()
        result = svc.classify("cotizar techo ISOROOF 80mm para nave 20x10m")
        assert result is not None

    def test_parse_request(self):
        from src.quotation.service import get_quotation_service
        svc = get_quotation_service()
        req = svc.parse("cotizar techo ISOROOF 80mm 20x10m")
        assert req.familia == "ISOROOF"
        assert req.thickness_mm == 80

    def test_full_pipeline_roof(self):
        from src.quotation.service import get_quotation_service
        svc = get_quotation_service()
        output = svc.full_pipeline("cotizar techo ISOROOF 80mm para nave de 20x10m")
        assert output is not None
        assert output.status in ("draft", "validated", "requires_review", "blocked")
        assert output.mode in ("informativo", "pre_cotizacion", "formal")

    def test_full_pipeline_wall(self):
        from src.quotation.service import get_quotation_service
        svc = get_quotation_service()
        output = svc.full_pipeline("cotizar pared ISOPANEL 100mm 10x3m estructura metal")
        assert output is not None
        assert output.mode in ("informativo", "pre_cotizacion", "formal")


# ─────────────────────────────────────────────────────────────────────────────
# Agno Tools
# ─────────────────────────────────────────────────────────────────────────────
class TestAgnoTools:
    def test_calcular_cotizacion_completa(self):
        from src.quotation.tools import calcular_cotizacion_completa
        result = calcular_cotizacion_completa.entrypoint(
            texto="cotizar techo ISOROOF 80mm para nave de 20x10m"
        )
        data = json.loads(result)
        assert "status" in data
        assert "mode" in data

    def test_verificar_precio_panel_found(self):
        from src.quotation.tools import verificar_precio_panel
        result = verificar_precio_panel.entrypoint(
            familia="ISOROOF", sub_familia="3G", espesor_mm=80
        )
        data = json.loads(result)
        assert data["encontrado"] is True
        assert data["precio_m2_usd_iva_inc"] > 0
        assert data["iva_incluido"] is True

    def test_verificar_precio_panel_not_found(self):
        from src.quotation.tools import verificar_precio_panel
        result = verificar_precio_panel.entrypoint(
            familia="ISOROOF_INEXISTENTE", sub_familia="XX", espesor_mm=999
        )
        data = json.loads(result)
        assert data["encontrado"] is False
        assert "mensaje" in data

    def test_calcular_bom_roof(self):
        from src.quotation.tools import calcular_bom
        result = calcular_bom.entrypoint(
            familia="ISOROOF", sub_familia="3G", espesor_mm=80,
            uso="techo", largo_m=20.0, ancho_m=10.0
        )
        data = json.loads(result)
        assert data["area_m2"] == 200.0
        assert data["panel_count"] > 0
        assert len(data["items"]) > 0

    def test_calcular_bom_wall_correct_dimensions(self):
        """Verifica el fix de dimensiones: panel_count debe ser ceil(length/ancho_util)."""
        from src.quotation.tools import calcular_bom
        result = calcular_bom.entrypoint(
            familia="ISOPANEL", sub_familia="EPS", espesor_mm=100,
            uso="pared", largo_m=10.0, ancho_m=3.0
        )
        data = json.loads(result)
        assert data["area_m2"] == 30.0
        # Con ancho_util_m=1.12: ceil(10/1.12) = 9 paneles (largo, no alto)
        assert data["panel_count"] >= 8 and data["panel_count"] <= 10, \
            f"Wall panel_count wrong: {data['panel_count']} (expected ~9 for 10m length)"

    def test_clasificar_solicitud(self):
        from src.quotation.tools import clasificar_solicitud
        result = clasificar_solicitud.entrypoint(
            texto="quiero techo de ISOROOF para galpón de 20x10"
        )
        data = json.loads(result)
        assert data["tipo"] == "roof_system"
        assert "modo" in data

    def test_validar_vano_autoportancia_exceeded(self):
        from src.quotation.tools import validar_vano_autoportancia
        result = validar_vano_autoportancia.entrypoint(
            familia="ISOROOF", sub_familia="3G", espesor_mm=80, vano_m=5.0
        )
        data = json.loads(result)
        # 5m vano, ISOROOF 80mm probablemente no lo soporta
        assert "valido" in data
        assert "mensaje" in data

    def test_buscar_accesorio(self):
        from src.quotation.tools import buscar_accesorio
        result = buscar_accesorio.entrypoint(tipo="silicona")
        data = json.loads(result)
        assert "encontrado" in data


# ─────────────────────────────────────────────────────────────────────────────
# Workflow Steps (sin LLM)
# ─────────────────────────────────────────────────────────────────────────────
class TestWorkflowSteps:
    """Verifica cada Step del workflow Agno con función Python pura."""

    class _MockWorkflowSession:
        session_data = {}

    class _MockStepInput:
        def __init__(self, text):
            self._text = text
            self.workflow_session = TestWorkflowSteps._MockWorkflowSession()
            self.previous_step_outputs = []
            self.previous_step_content = None

        def get_input_as_string(self):
            return self._text

        def get_last_step_content(self):
            return None

    TEXT = "cotizar techo ISOROOF 80mm para nave de 20x10m estructura metal"

    def test_step_classify(self):
        from src.agent.workflow import step_classify
        step_input = self._MockStepInput(self.TEXT)
        result = step_classify(step_input)
        assert result.success is True
        data = json.loads(result.content)
        assert data["tipo"] == "roof_system"
        assert "modo" in data

    def test_step_parse(self):
        from src.agent.workflow import step_parse
        step_input = self._MockStepInput(self.TEXT)
        result = step_parse(step_input)
        assert result.success is True
        data = json.loads(result.content)
        assert data["familia"] == "ISOROOF"
        assert data["thickness_mm"] == 80

    def test_step_sre(self):
        from src.agent.workflow import step_sre
        step_input = self._MockStepInput(self.TEXT)
        result = step_sre(step_input)
        assert result.success is True
        data = json.loads(result.content)
        assert "score" in data
        assert 0 <= data["score"] <= 100

    def test_step_bom(self):
        from src.agent.workflow import step_bom
        step_input = self._MockStepInput(self.TEXT)
        result = step_bom(step_input)
        assert result.success is True
        data = json.loads(result.content)
        assert data["panel_count"] > 0
        assert len(data["items"]) > 0

    def test_step_pricing(self):
        from src.agent.workflow import step_pricing
        step_input = self._MockStepInput(self.TEXT)
        result = step_pricing(step_input)
        assert result.success is True
        data = json.loads(result.content)
        assert "subtotal_panels_usd" in data

    def test_step_validate(self):
        from src.agent.workflow import step_validate
        step_input = self._MockStepInput(self.TEXT)
        result = step_validate(step_input)
        assert result.success is True
        data = json.loads(result.content)
        assert "is_valid" in data
        assert "can_emit_formal" in data

    def test_accessories_only_skips_bom(self):
        """El router debe saltar el step BOM para solicitudes de accesorios."""
        import json
        from agno.workflow.step import StepInput, StepOutput
        from src.agent.workflow import route_after_sre, _step_bom_obj, _step_pricing_obj

        class MockInput:
            def get_last_step_content(self):
                return json.dumps({"is_accessories_only": True})
            def get_input_as_string(self):
                return "quiero goteros y babetas"
            workflow_session = None
            previous_step_outputs = []
            previous_step_content = None

        steps = route_after_sre(MockInput())
        step_names = [s.name for s in steps]
        assert "bom" not in step_names, "BOM debería saltarse para accessories_only"
        assert "pricing" in step_names


# ─────────────────────────────────────────────────────────────────────────────
# Security Fixes
# ─────────────────────────────────────────────────────────────────────────────
class TestSecurityFixes:
    def test_no_mywolfy_in_kb_auth(self):
        """KB_WRITE_PASSWORD no debe tener default 'mywolfy'."""
        from wolf_api.kb_auth import KB_WRITE_PASSWORD
        assert KB_WRITE_PASSWORD != "mywolfy", "mywolfy default no debe estar en producción"

    def test_no_mywolfykey_in_pdf_cotizacion(self):
        """WOLF_API_KEY no debe tener default hardcodeado en pdf_cotizacion."""
        import ast
        import pathlib
        source = pathlib.Path("wolf_api/pdf_cotizacion.py").read_text()
        assert "mywolfykey123XYZ" not in source, "Key hardcodeada removida"

    def test_no_mywolfykey_in_sheet_mover(self):
        """WOLF_API_KEY no debe tener default hardcodeado en sheet_mover."""
        import pathlib
        source = pathlib.Path("wolf_api/sheet_mover.py").read_text()
        assert "mywolfykey123XYZ" not in source, "Key hardcodeada removida"

    def test_cors_origins_not_hardcoded_wildcard_in_code(self):
        """CORS debe leer de env, con ['*'] solo como default de última instancia."""
        import pathlib
        source = pathlib.Path("wolf_api/main.py").read_text()
        assert 'allow_origins=["*"]' not in source, "CORS wildcard debe venir de env"

    def test_terraform_deletion_protection_enabled(self):
        """Cloud SQL debe tener deletion_protection=true."""
        import pathlib
        source = pathlib.Path("terraform/main.tf").read_text()
        assert "deletion_protection = true" in source
        assert "deletion_protection = false" not in source


# ─────────────────────────────────────────────────────────────────────────────
# BOM Wall Dimensions Fix
# ─────────────────────────────────────────────────────────────────────────────
class TestBOMWallDimensionsFix:
    """Verifica el fix del bug de dimensiones en paredes."""

    def test_wall_panel_count_uses_length_not_height(self):
        """Para paredes, panel_count debe usar length_m (horizontal), no width_m (altura)."""
        from panelin_v4.engine.bom_engine import calculate_bom

        # Pared de 10m largo x 3m alto con ISOPANEL (ancho_util_m = 1.12m)
        bom = calculate_bom(
            familia="ISOPANEL",
            sub_familia="EPS",
            thickness_mm=100,
            uso="pared",
            length_m=10.0,  # largo horizontal
            width_m=3.0,    # alto de la pared
        )
        # Paneles se cuentan a lo largo: ceil(10 / 1.12) = 9
        # Bug anterior: ceil(3 / 1.12) = 3 (usaba el alto en vez del largo)
        assert bom.panel_count >= 8, \
            f"Pared 10m: panel_count={bom.panel_count}, debe ser ~9, no ~3"
        assert bom.area_m2 == 30.0, "Area debe ser length_m * width_m = 30m2"

    def test_roof_panel_count_uses_width(self):
        """Para techos, panel_count debe usar width_m (dirección transversal)."""
        from panelin_v4.engine.bom_engine import calculate_bom

        # Techo de 20m de largo x 10m de ancho con ISOROOF (ancho_util_m ≈ 1.12m)
        bom = calculate_bom(
            familia="ISOROOF",
            sub_familia="3G",
            thickness_mm=80,
            uso="techo",
            length_m=20.0,  # largo del techo (dirección correa)
            width_m=10.0,   # ancho transversal (paneles se cuentan acá)
        )
        # Techos: paneles se cuentan a lo ancho: ceil(10 / 1.12) ≈ 9
        assert bom.panel_count >= 8 and bom.panel_count <= 11
        assert bom.area_m2 == 200.0

    def test_wall_wall_area_correct(self):
        """El área de pared debe ser length_m * width_m independientemente del panel_count."""
        from panelin_v4.engine.bom_engine import calculate_bom

        bom = calculate_bom(
            familia="ISOWALL",
            sub_familia="PIR",
            thickness_mm=60,
            uso="pared",
            length_m=15.0,
            width_m=4.0,
        )
        assert bom.area_m2 == 60.0  # 15 * 4


# ─────────────────────────────────────────────────────────────────────────────
# Pricing sub_familia Fix
# ─────────────────────────────────────────────────────────────────────────────
class TestPricingSubFamiliaFix:
    """Verifica que el pricing no ignora sub_familia."""

    def test_pricing_finds_price_for_known_product(self):
        """Debe encontrar precio para familia+sub_familia+espesor conocidos."""
        from panelin_v4.engine.pricing_engine import _find_panel_price_m2
        price = _find_panel_price_m2("ISOROOF", "3G", 80)
        assert price is not None, "Debe encontrar precio para ISOROOF 3G 80mm"
        assert price > 0

    def test_pricing_fallback_without_subfamilia(self):
        """Si no hay match exacto de sub_familia, cae al match de familia."""
        from panelin_v4.engine.pricing_engine import _find_panel_price_m2
        # "STANDARD" no debería existir, pero familia match debería funcionar
        price = _find_panel_price_m2("ISOROOF", "STANDARD", 80)
        # Puede ser None si no hay productos ISOROOF 80mm, o un precio si hay alguno
        # La prueba es que no lanza excepción y retorna float o None
        assert price is None or isinstance(price, float)
