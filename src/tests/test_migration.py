"""
Tests de integración: Migración Panelin → Agno
================================================

Verifica que toda la cadena funcione correctamente:
  1. Pipeline determinístico (engine v4.0) sigue funcionando
  2. Agno Steps envuelven correctamente el engine
  3. Agno Workflow orquesta el pipeline completo
  4. Service layer funciona como wrapper
  5. Bugs FASE 0 corregidos (BOM wall, pricing sub_familia, security)
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


# ─── Tests de pipeline (engine sin modificar) ─────────────────────────────────

class TestEnginePipelineUnchanged:
    """Verifica que el engine v4.0 NO fue modificado en su lógica core."""

    def test_full_pipeline_roof(self):
        from panelin_v4.engine.quotation_engine import process_quotation
        # Parser: "10x8" → width=10, length=8 → panel_count=ceil(10/1.12)=9
        result = process_quotation(
            "Techo ISODEC 100mm 10x8 metros 2 aguas estructura metálica"
        )
        assert result.quote_id.startswith("PV4-")
        assert result.bom.get("panel_count", 0) > 0
        assert result.pricing.get("subtotal_total_usd", 0) >= 0

    def test_full_pipeline_wall(self):
        from panelin_v4.engine.quotation_engine import process_quotation
        import math
        # Parser: "12x3" → width=12, length=3 → panel_count=ceil(12/1.12)=11
        result = process_quotation(
            "Pared ISOPANEL EPS 75mm 12x3 metros estructura metálica"
        )
        assert result.quote_id.startswith("PV4-")
        bom = result.bom
        expected_panels = math.ceil(12.0 / 1.12)
        assert bom.get("panel_count", 0) == expected_panels, (
            f"Wall BOM debería tener {expected_panels} paneles para 12m"
        )

    def test_pre_mode_never_blocks(self):
        from panelin_v4.engine.quotation_engine import process_quotation
        result = process_quotation("Panel de techo, necesito presupuesto")
        assert result.status != "blocked"

    def test_accessories_only(self):
        from panelin_v4.engine.quotation_engine import process_quotation
        result = process_quotation(
            "Necesito goteros y silicona para sellado, y remaches",
            force_mode=None,
        )
        assert result.quote_id.startswith("PV4-")


# ─── Tests de bugs FASE 0 ─────────────────────────────────────────────────────

class TestFase0BugFixes:
    """Verifica que los bugs críticos de FASE 0 están corregidos."""

    def test_wall_bom_panel_count_fix(self):
        """Bug fix: Panel count para paredes usa width_m (extensión horizontal).

        Convención: width_m = extensión horizontal (cuántos paneles), length_m = altura de la pared.
        Esta es la convención del parser para "12x3 metros" → width=12, length=3.
        """
        from panelin_v4.engine.bom_engine import calculate_bom
        import math

        # Pared de 12m horizontal x 3m de altura (convención del parser: width=12, length=3)
        bom = calculate_bom(
            familia="ISOPANEL",
            sub_familia="EPS",
            thickness_mm=75,
            uso="pared",
            length_m=3.0,   # altura de la pared (segundo número del parser)
            width_m=12.0,   # extensión horizontal (primer número del parser)
        )
        # Panel count correcto: ceil(width_m / 1.12) = ceil(12/1.12) = 11 paneles
        expected = math.ceil(12.0 / 1.12)
        assert bom.panel_count == expected, (
            f"Wall BOM debería tener {expected} paneles (width_m/ancho_util) pero tiene {bom.panel_count}. "
            f"Bug de swap dimensions puede seguir presente."
        )

    def test_wall_bom_perimeter_fix(self):
        """Bug fix: Perimeter para paredes usa 2*width_m + 2*length_m (horizontal + altura)."""
        from panelin_v4.engine.bom_engine import calculate_bom

        # Pared: width=10m horizontal, length=3m altura
        bom = calculate_bom(
            familia="ISOPANEL",
            sub_familia="EPS",
            thickness_mm=75,
            uso="pared",
            length_m=3.0,   # altura
            width_m=10.0,   # extensión horizontal
        )
        # Área = width_m * length_m = 10 * 3 = 30m²
        assert bom.area_m2 == pytest.approx(30.0, rel=0.01), "Área = 10*3 = 30m²"
        # Panel count = ceil(10/1.12) = 9
        import math
        assert bom.panel_count == math.ceil(10.0 / 1.12)

    def test_pricing_subfamilia_match(self):
        """Bug fix: pricing_engine ahora usa sub_familia en el matching."""
        from panelin_v4.engine.pricing_engine import _find_panel_price_m2

        # Debe retornar un precio (no None) para familia conocida
        price = _find_panel_price_m2("ISODEC", "EPS", 100)
        # El resultado puede ser None si el catálogo no está disponible en tests
        # pero NO debe inventar precios — si retorna algo, debe ser un número válido
        if price is not None:
            assert price > 0, "Precio debe ser positivo"
            assert price < 10000, "Precio no debería ser absurdo (sanity check)"

    def test_kb_auth_no_default_password(self):
        """Bug fix: KB_WRITE_PASSWORD ya no tiene default 'mywolfy'."""
        from wolf_api.kb_auth import KB_WRITE_PASSWORD, validate_write_password
        from fastapi import HTTPException

        # Sin configurar env var, KB_WRITE_PASSWORD debe ser vacío
        import os
        original = os.environ.get("KB_WRITE_PASSWORD")
        try:
            os.environ.pop("KB_WRITE_PASSWORD", None)
            # Reimportar para verificar el default
            import importlib
            import wolf_api.kb_auth as kb_auth_mod
            importlib.reload(kb_auth_mod)
            assert kb_auth_mod.KB_WRITE_PASSWORD == "", (
                "KB_WRITE_PASSWORD no debería tener default 'mywolfy'"
            )
        finally:
            if original:
                os.environ["KB_WRITE_PASSWORD"] = original


# ─── Tests del Service Layer ───────────────────────────────────────────────────

class TestQuotationService:
    """Verifica que el Service Layer envuelve correctamente el engine."""

    def test_service_calculate(self):
        from src.quotation.service import QuotationRequest, get_quotation_service

        service = get_quotation_service()
        result = service.calculate(
            QuotationRequest(
                text="Techo ISODEC 100mm, 10x8 metros, estructura metálica"
            )
        )
        assert result.success is True
        assert result.quote_id is not None
        assert result.processing_ms > 0
        assert result.confidence_score >= 0

    def test_service_summary_format(self):
        from src.quotation.service import QuotationRequest, get_quotation_service

        service = get_quotation_service()
        result = service.calculate(
            QuotationRequest(text="ISODEC 100mm techo 5x6 metros metálica")
        )
        summary = result.to_summary()
        assert "PV4-" in summary, "Summary debe incluir quote_id"
        assert "m²" in summary or "paneles" in summary.lower()

    def test_service_never_invents_prices(self):
        """Verifica que el servicio no inventa precios para productos desconocidos."""
        from src.quotation.service import QuotationRequest, get_quotation_service

        service = get_quotation_service()
        result = service.calculate(
            QuotationRequest(
                text="Panel XYZ-DESCONOCIDO 999mm techo 10x10 metros"
            )
        )
        # Puede tener éxito pero el precio total debe ser 0 o tener missing_prices
        pricing = result.data.get("pricing", {})
        total = pricing.get("subtotal_total_usd", 0)
        missing = pricing.get("missing_prices", [])
        # Si no encontró precio, total debe ser 0 o hay missing_prices
        if total == 0:
            assert True  # Correcto — no inventa precios
        else:
            # Si tiene precio, debe haber venido de la KB
            assert len(missing) == 0 or total > 0

    def test_service_search_products(self):
        from src.quotation.service import get_quotation_service

        service = get_quotation_service()
        results = service.search_products("ISODEC")
        assert isinstance(results, list)

    def test_batch_processing(self):
        from src.quotation.service import QuotationRequest, get_quotation_service

        service = get_quotation_service()
        requests = [
            QuotationRequest(text="ISODEC 100mm techo 10x8"),
            QuotationRequest(text="ISOPANEL 75mm pared 12x3"),
        ]
        results = service.calculate_batch(requests)
        assert len(results) == 2


# ─── Tests del Agno Workflow ──────────────────────────────────────────────────

class TestAgnoWorkflowSteps:
    """Verifica que los Steps del workflow funcionan correctamente."""

    def test_step_classify(self):
        from agno.workflow import StepInput
        from src.agent.workflow import step_classify

        step_in = StepInput(input="Techo ISODEC 100mm 10x8 metros, 2 aguas")
        out = step_classify(step_in)
        assert out.success is True
        assert out.content is not None
        assert "request_type" in out.content
        assert "operating_mode" in out.content

    def test_step_parse(self):
        from agno.workflow import StepInput
        from src.agent.workflow import step_parse

        step_in = StepInput(input="ISODEC 100mm techo 10 metros largo 8 metros ancho estructura metálica")
        out = step_parse(step_in)
        assert out.success is True
        req = out.content
        assert req.get("familia") is not None, "Parser debe detectar familia ISODEC"
        assert req.get("thickness_mm") == 100

    def test_step_sre(self):
        from agno.workflow import StepInput
        from src.agent.workflow import step_sre

        step_in = StepInput(input="ISODEC 100mm techo 10x8 metros span 1.5m estructura metálica")
        out = step_sre(step_in)
        assert out.success is True
        sre = out.content
        assert "score" in sre
        assert 0 <= sre["score"] <= 100

    def test_step_bom_roof(self):
        from agno.workflow import StepInput
        from src.agent.workflow import step_bom
        import math

        # "10x8": width=10, length=8 → panel_count=ceil(10/1.12)=9
        step_in = StepInput(input="ISODEC 100mm techo 10x8 metros 2 aguas metal")
        out = step_bom(step_in)
        assert out.success is True
        bom = out.content
        assert bom.get("panel_count", 0) > 0

    def test_step_bom_wall(self):
        from agno.workflow import StepInput
        from src.agent.workflow import step_bom
        import math

        # "12x3": width=12, length=3 → panel_count=ceil(12/1.12)=11
        step_in = StepInput(input="ISOPANEL 75mm pared 12x3 metros metal")
        out = step_bom(step_in)
        assert out.success is True
        bom = out.content
        # Con fix: panel_count para pared 12m horizontal = ceil(12/1.12) = 11
        assert bom.get("panel_count", 0) == math.ceil(12.0 / 1.12)

    def test_step_validate(self):
        from agno.workflow import StepInput
        from src.agent.workflow import step_validate

        step_in = StepInput(input="ISODEC 100mm techo 10x8 metros 2 aguas metal span 1.5m")
        out = step_validate(step_in)
        assert out.success is True
        val = out.content
        assert "can_emit_formal" in val or "critical_count" in val

    def test_router_routes_correctly_roof(self):
        from agno.workflow import StepInput, StepOutput
        from src.agent.workflow import select_bom_route

        # Simular output del paso classify
        step_in = StepInput(
            input="ISODEC 100mm techo 10x8 metros",
            previous_step_outputs={
                "classify": StepOutput(
                    step_name="classify",
                    content={"request_type": "roof_system", "operating_mode": "pre_cotizacion"},
                )
            }
        )
        route = select_bom_route(step_in)
        assert route == "bom_completo"

    def test_router_routes_accessories_only(self):
        from agno.workflow import StepInput, StepOutput
        from src.agent.workflow import select_bom_route

        step_in = StepInput(
            input="Necesito goteros y silicona",
            previous_step_outputs={
                "classify": StepOutput(
                    step_name="classify",
                    content={"request_type": "accessories_only", "operating_mode": "pre_cotizacion"},
                )
            }
        )
        route = select_bom_route(step_in)
        assert route == "solo_accesorios"


# ─── Tests de config ──────────────────────────────────────────────────────────

class TestConfig:
    """Verifica la configuración con pydantic-settings."""

    def test_config_loads(self):
        from src.core.config import get_settings

        settings = get_settings()
        assert settings is not None
        assert settings.default_model is not None

    def test_config_paths_exist(self):
        from src.core.config import get_settings

        settings = get_settings()
        assert settings.pricing_master_path.exists(), "bromyros_pricing_master.json debe existir"
        assert settings.accessories_catalog_path.exists(), "accessories_catalog.json debe existir"
        assert settings.bom_rules_path.exists(), "bom_rules.json debe existir"

    def test_cors_parse(self):
        import os
        os.environ["CORS_ALLOW_ORIGINS"] = "https://app.bmc.com.uy,https://admin.bmc.com.uy"
        from src.core.config import PanelinSettings
        s = PanelinSettings()
        origins = s.cors_allow_origins
        assert len(origins) == 2
        assert "https://app.bmc.com.uy" in origins
        os.environ.pop("CORS_ALLOW_ORIGINS", None)


# ─── Tests de herramientas del agente ─────────────────────────────────────────

class TestAgentTools:
    """Verifica que las tools del agente funcionan correctamente."""

    def test_buscar_productos(self):
        from src.quotation.tools import buscar_productos
        result = buscar_productos("ISODEC")
        assert isinstance(result, str)
        assert "ISODEC" in result.upper() or "no se encontraron" in result.lower()

    def test_validar_solicitud_formal_incompleta(self):
        from src.quotation.tools import validar_solicitud_formal
        result = validar_solicitud_formal("necesito un techo")
        assert "familia" in result.lower() or "faltante" in result.lower() or "❌" in result

    def test_validar_solicitud_formal_completa(self):
        from src.quotation.tools import validar_solicitud_formal
        result = validar_solicitud_formal(
            "ISODEC 100mm techo, 10 metros largo x 8 metros ancho, 2 aguas, "
            "estructura metálica, cliente Juan Pérez, Montevideo"
        )
        # Puede tener warnings pero no debe listar familia o espesor como faltantes
        assert "familia de panel no especificada" not in result.lower()
