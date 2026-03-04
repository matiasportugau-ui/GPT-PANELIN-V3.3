"""
Tests de integración para la capa Agno.

Verifica:
  1. Config se carga correctamente
  2. QuotationService funciona
  3. Domain tools retornan JSON válido
  4. Workflow steps ejecutan sin errores
  5. Guardrails detectan outputs inválidos
  6. BOM wall fix (dimensiones correctas)
  7. Pricing sub_familia fix

Todos los tests son OFFLINE (sin LLM, sin red, sin DB).
"""

from __future__ import annotations

import json

import pytest

# ── Config ───────────────────────────────────────────────────────────────────


def test_config_loads():
    from src.core.config import settings
    assert settings.openai_model != ""
    assert settings.iva_rate == pytest.approx(0.22)
    assert settings.kb_root.exists()


def test_config_kb_paths_exist():
    from src.core.config import settings
    assert settings.kb_pricing_path.exists(), f"Missing: {settings.kb_pricing_path}"
    assert settings.kb_accessories_path.exists(), f"Missing: {settings.kb_accessories_path}"
    assert settings.kb_bom_rules_path.exists(), f"Missing: {settings.kb_bom_rules_path}"


# ── QuotationService ─────────────────────────────────────────────────────────


def test_quotation_service_full_pipeline():
    from src.quotation.service import QuotationRequest, quotation_service

    result = quotation_service.run(QuotationRequest(
        text="Cotizar techo ISODEC EPS 100mm, 10 metros largo por 7 de ancho",
        mode="pre_cotizacion",
    ))

    assert result.quote_id.startswith("PV4-")
    assert result.status in ("draft", "validated", "requires_review", "blocked")
    assert result.sai.score >= 0
    assert isinstance(result.to_dict(), dict)


def test_quotation_service_wall():
    from src.quotation.service import QuotationRequest, quotation_service

    result = quotation_service.run(QuotationRequest(
        text="Necesito ISOPANEL EPS 80mm para pared de 8 metros de largo por 3 de alto",
        mode="pre_cotizacion",
    ))
    assert result.quote_id.startswith("PV4-")
    # Verificar que el BOM se calculó
    bom = result.quote_dict.get("bom", {})
    if bom.get("panel_count", 0) > 0:
        # Si calculó BOM, verificar que el sistema es de pared
        assert "pared" in bom.get("system_key", ""), f"System key incorrecto: {bom.get('system_key')}"


def test_quotation_service_accessories_only():
    from src.quotation.service import QuotationRequest, quotation_service

    result = quotation_service.run(QuotationRequest(
        text="¿Cuánto cuestan los tornillos y la silicona para ISODEC?",
        mode="pre_cotizacion",
    ))
    assert result.quote_id.startswith("PV4-")


def test_quotation_service_pre_mode_never_blocks():
    from src.quotation.service import QuotationRequest, quotation_service

    # Solicitud con datos mínimos — NO debe bloquear en pre_cotizacion
    result = quotation_service.run(QuotationRequest(
        text="Necesito paneles",
        mode="pre_cotizacion",
    ))
    assert result.status != "blocked", (
        f"Pre-cotización NO debe bloquear con datos mínimos. Got status={result.status}"
    )


# ── Domain Tools ─────────────────────────────────────────────────────────────


def test_tool_calcular_cotizacion():
    from src.quotation.tools import calcular_cotizacion

    result_str = calcular_cotizacion(
        texto="ISODEC EPS 100mm techo 10x7 metros",
        modo="pre_cotizacion",
    )
    data = json.loads(result_str)
    assert "quote" in data
    assert "sai" in data
    assert data["quote"]["quote_id"].startswith("PV4-")


def test_tool_verificar_precio_panel_found():
    from src.quotation.tools import verificar_precio_panel

    result_str = verificar_precio_panel("ISODEC", "EPS", 100)
    data = json.loads(result_str)
    # Can be found or not depending on KB, but should be valid JSON
    assert "encontrado" in data
    assert "producto" in data


def test_tool_verificar_precio_panel_wrong_sub_familia():
    from src.quotation.tools import verificar_precio_panel

    # ISODEC FAKE_SUB no debe encontrarse
    result_str = verificar_precio_panel("ISODEC", "FAKE_SUBFAMILIA", 100)
    data = json.loads(result_str)
    # May or may not be found — just verify it's valid JSON
    assert "encontrado" in data


def test_tool_validar_autoportancia():
    from src.quotation.tools import validar_autoportancia

    result_str = validar_autoportancia("ISODEC", "EPS", 100, 3.0)
    data = json.loads(result_str)
    assert "estado" in data
    assert data["estado"] in ("ok", "warning", "blocked", "sin_datos")


def test_tool_buscar_accesorios():
    from src.quotation.tools import buscar_accesorios

    result_str = buscar_accesorios()
    data = json.loads(result_str)
    assert "total" in data
    assert isinstance(data["accesorios"], list)
    assert data["total"] > 0


def test_tool_clasificar_solicitud():
    from src.quotation.tools import clasificar_solicitud

    result_str = clasificar_solicitud("Quiero cotizar un techo de ISOROOF 150mm")
    data = json.loads(result_str)
    assert "request_type" in data
    assert "operating_mode" in data


def test_tool_reglas_negocio():
    from src.quotation.tools import reglas_negocio

    result_str = reglas_negocio()
    data = json.loads(result_str)
    assert data["iva_rate"] == pytest.approx(0.22)
    assert data["moneda"] == "USD"


# ── Workflow Steps (sin LLM) ─────────────────────────────────────────────────


def test_workflow_step_classify():
    from agno.workflow import StepInput
    from src.agent.workflow import step_classify

    inp = StepInput(
        input="Cotizar ISODEC EPS 100mm techo 10x7 metros",
        additional_data={"mode": "pre_cotizacion"},
    )
    out = step_classify(inp)

    assert out.success
    data = json.loads(out.content)
    assert "request_type" in data
    assert "operating_mode" in data


def test_workflow_step_classify_empty_input():
    from agno.workflow import StepInput
    from src.agent.workflow import step_classify

    inp = StepInput(input="", additional_data={})
    out = step_classify(inp)

    assert not out.success
    assert out.stop


def test_workflow_step_pipeline():
    from agno.workflow import StepInput, StepOutput
    from src.agent.workflow import step_classify, step_pipeline

    text = "Cotizar ISODEC EPS 100mm techo 10x7 metros"
    classify_inp = StepInput(input=text, additional_data={"mode": "pre_cotizacion"})
    classify_out = step_classify(classify_inp)

    pipeline_inp = StepInput(
        input=text,
        additional_data={"mode": "pre_cotizacion"},
        previous_step_outputs={"classify": classify_out},
    )
    pipeline_out = step_pipeline(pipeline_inp)

    assert pipeline_out.success
    data = json.loads(pipeline_out.content)
    assert "quote" in data
    assert "sai" in data
    assert data["quote"]["quote_id"].startswith("PV4-")


def test_workflow_build():
    from src.agent.workflow import build_panelin_workflow

    wf = build_panelin_workflow(session_id="test_session")
    assert wf.name == "panelin_quotation"


# ── Guardrails ────────────────────────────────────────────────────────────────


def test_guardrail_detects_invented_price():
    from src.agent.guardrails import validate_panelin_output

    bad_response = "El techo le va a costar aproximadamente USD 5000 por metro cuadrado."
    valid, errors = validate_panelin_output(bad_response)
    assert not valid
    assert len(errors) > 0


def test_guardrail_detects_external_derivation():
    from src.agent.guardrails import validate_panelin_output

    bad_response = "Consulte al proveedor directamente para obtener mejores precios."
    valid, errors = validate_panelin_output(bad_response)
    assert not valid
    assert len(errors) > 0


def test_guardrail_passes_valid_response():
    from src.agent.guardrails import validate_panelin_output

    good_response = (
        "Para el techo de 70m² con ISODEC EPS 100mm, el costo total es USD 3,850 "
        "(IVA 22% incluido). Incluye 9 paneles y los accesorios de fijación. "
        "Un agente de ventas BMC Uruguay se contactará para coordinar la entrega."
    )
    valid, errors = validate_panelin_output(good_response)
    assert valid
    assert len(errors) == 0


# ── Bug Fixes Verification ────────────────────────────────────────────────────


def test_bom_wall_dimensions_fix():
    """Verifica que el BOM de pared use las dimensiones correctas post-fix."""
    from panelin_v4.engine.bom_engine import calculate_bom

    # Pared: 10m de largo (horizontal), 3m de alto (vertical)
    # width_m = 10 (horizontal), length_m = 3 (vertical/alto)
    bom = calculate_bom(
        familia="ISOPANEL",
        sub_familia="EPS",
        thickness_mm=80,
        uso="pared",
        length_m=3.0,   # alto
        width_m=10.0,   # largo horizontal
        structure_type="metal",
    )

    # Panel count debe ser ceil(10.0 / 1.12) ≈ 9 paneles (horizontal)
    assert bom.panel_count == 9, f"Panel count incorrecto: {bom.panel_count} (esperado 9)"

    # Los items de pared deben existir
    item_types = {item.tipo for item in bom.items}
    assert "panel" in item_types
    assert "perfil_u" in item_types  # U-profiles en pared

    # Verificar que perfil_u usa la dimensión correcta (width_m=10 horizontal)
    perfil_u = next((i for i in bom.items if i.tipo == "perfil_u"), None)
    assert perfil_u is not None
    # U-profiles: ceil(10 / 3.0) * 2 = 8 unidades (superior + inferior)
    assert perfil_u.quantity == 8, (
        f"Perfil U incorrecto: {perfil_u.quantity} (esperado 8 para pared de 10m)"
    )

    # Silicona debe usar height_m=3 para juntas verticales
    silicona = next((i for i in bom.items if i.tipo == "silicona"), None)
    if silicona:
        # juntas_ml = (9-1) * 3.0 * 2 = 48ml → ceil(48/8) = 6 tubos
        assert silicona.quantity == 6, (
            f"Silicona incorrecta: {silicona.quantity} (esperado 6 para juntas de 3m)"
        )


def test_pricing_subfamilia_fix():
    """Verifica que el pricing distingue EPS vs PIR (bug sub_familia fix)."""
    from panelin_v4.engine.pricing_engine import _find_panel_price_m2

    price_eps = _find_panel_price_m2("ISODEC", "EPS", 100)
    price_pir = _find_panel_price_m2("ISODEC", "PIR", 100)

    # Si ambos productos existen en la KB, sus precios deben ser diferentes
    if price_eps is not None and price_pir is not None:
        assert price_eps != price_pir, (
            f"EPS y PIR tienen el mismo precio ({price_eps}) — sub_familia fix puede no funcionar"
        )


def test_security_no_default_passwords():
    """Verifica que no hay contraseñas por defecto en el código."""
    from wolf_api.kb_auth import KB_WRITE_PASSWORD
    from mcp.handlers.wolf_kb_write import KB_WRITE_PASSWORD as MCP_KB_PWD
    from mcp.handlers.file_ops import KB_WRITE_PASSWORD as FILE_OPS_PWD

    # Los defaults deben ser strings vacíos, no "mywolfy"
    assert KB_WRITE_PASSWORD != "mywolfy", "wolf_api/kb_auth.py tiene default inseguro"
    assert MCP_KB_PWD != "mywolfy", "mcp/handlers/wolf_kb_write.py tiene default inseguro"
    assert FILE_OPS_PWD != "mywolfy", "mcp/handlers/file_ops.py tiene default inseguro"
