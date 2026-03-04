"""
Panelin v5.0 — Agno Quotation Workflow
=========================================

Deterministic 7-step pipeline implemented as an Agno Workflow.

Steps 1-7 are pure Python functions ($0.00 per execution).
Step 8 (respond) uses an LLM agent (~$0.02) to format the response
in natural Spanish for the user.

Pipeline:
    1. classify   — Determine request type and operating mode
    2. parse      — Extract structured data from free text
    3. defaults   — Apply default assumptions (non-formal modes)
    4. sre        — Calculate structural risk score
    5. bom        — Generate Bill of Materials
    6. pricing    — Price all BOM items from KB
    7. validate   — Multi-layer validation
    8. respond    — LLM formats the results into Spanish response

Router: If request_type == ACCESSORIES_ONLY, skip steps 4-5 (SRE + BOM).
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.run import RunContext
from agno.workflow.step import Step, StepInput, StepOutput
from agno.workflow.workflow import Workflow

from panelin_v4.engine.classifier import (
    ClassificationResult,
    OperatingMode,
    RequestType,
    classify_request,
)
from panelin_v4.engine.parser import QuoteRequest, parse_request
from panelin_v4.engine.sre_engine import SREResult, calculate_sre
from panelin_v4.engine.bom_engine import BOMResult, calculate_bom
from panelin_v4.engine.pricing_engine import PricingResult, calculate_pricing
from panelin_v4.engine.validation_engine import ValidationResult, validate_quotation
from panelin_v4.engine.quotation_engine import (
    QuotationOutput,
    _apply_defaults,
    _calculate_confidence,
    _determine_status,
)
from panelin_v4.evaluator.sai_engine import calculate_sai

from src.quotation.service import QuotationService

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Step 1: Classify
# ═══════════════════════════════════════════════════════════════════

def step_classify(step_input: StepInput, run_context: RunContext) -> StepOutput:
    """Classify the incoming request into type and operating mode."""
    text = step_input.input or ""

    force_mode_str = None
    if run_context.session_state and "force_mode" in run_context.session_state:
        force_mode_str = run_context.session_state["force_mode"]

    force_mode = None
    if force_mode_str:
        mode_map = {
            "informativo": OperatingMode.INFORMATIVO,
            "pre_cotizacion": OperatingMode.PRE_COTIZACION,
            "formal": OperatingMode.FORMAL,
        }
        force_mode = mode_map.get(force_mode_str)

    classification = classify_request(text, force_mode=force_mode)

    if "pipeline" not in run_context.session_state:
        run_context.session_state["pipeline"] = {}

    run_context.session_state["pipeline"]["raw_text"] = text
    run_context.session_state["pipeline"]["classification"] = classification.to_dict()
    run_context.session_state["pipeline"]["mode"] = classification.operating_mode.value
    run_context.session_state["pipeline"]["request_type"] = classification.request_type.value

    logger.info(
        "classify: type=%s mode=%s confidence=%.2f",
        classification.request_type.value,
        classification.operating_mode.value,
        classification.confidence,
    )

    return StepOutput(
        content=json.dumps(classification.to_dict(), ensure_ascii=False)
    )


# ═══════════════════════════════════════════════════════════════════
# Step 2: Parse
# ═══════════════════════════════════════════════════════════════════

def step_parse(step_input: StepInput, run_context: RunContext) -> StepOutput:
    """Parse free-text Spanish into a structured QuoteRequest."""
    text = run_context.session_state.get("pipeline", {}).get("raw_text", "")
    request = parse_request(text)

    client = run_context.session_state.get("client", {})
    if client.get("name"):
        request.client.name = client["name"]
    if client.get("phone"):
        request.client.phone = client["phone"]
    if client.get("location"):
        request.client.location = client["location"]

    run_context.session_state["pipeline"]["request"] = request.to_dict()
    run_context.session_state["pipeline"]["_request_obj"] = request

    logger.info(
        "parse: familia=%s thickness=%s uso=%s incomplete=%s",
        request.familia,
        request.thickness_mm,
        request.uso,
        request.incomplete_fields,
    )

    return StepOutput(
        content=json.dumps(request.to_dict(), ensure_ascii=False)
    )


# ═══════════════════════════════════════════════════════════════════
# Step 3: Apply Defaults
# ═══════════════════════════════════════════════════════════════════

def step_defaults(step_input: StepInput, run_context: RunContext) -> StepOutput:
    """Apply default assumptions for missing data in non-formal modes."""
    pipeline = run_context.session_state.get("pipeline", {})
    request: QuoteRequest = pipeline.get("_request_obj")
    if request is None:
        return StepOutput(content='{"error": "no request object"}')

    mode_str = pipeline.get("mode", "pre_cotizacion")
    mode_map = {
        "informativo": OperatingMode.INFORMATIVO,
        "pre_cotizacion": OperatingMode.PRE_COTIZACION,
        "formal": OperatingMode.FORMAL,
    }
    mode = mode_map.get(mode_str, OperatingMode.PRE_COTIZACION)

    assumptions = _apply_defaults(request, mode)
    request.assumptions_used.extend(assumptions)

    run_context.session_state["pipeline"]["request"] = request.to_dict()
    run_context.session_state["pipeline"]["_request_obj"] = request
    run_context.session_state["pipeline"]["assumptions"] = request.assumptions_used

    logger.info("defaults: %d assumptions applied", len(assumptions))

    return StepOutput(
        content=json.dumps({"assumptions": assumptions}, ensure_ascii=False)
    )


# ═══════════════════════════════════════════════════════════════════
# Step 4: SRE (Structural Risk Engine)
# ═══════════════════════════════════════════════════════════════════

def step_sre(step_input: StepInput, run_context: RunContext) -> StepOutput:
    """Calculate structural risk score."""
    pipeline = run_context.session_state.get("pipeline", {})
    request: QuoteRequest = pipeline.get("_request_obj")
    if request is None:
        return StepOutput(content='{"error": "no request object"}')

    request_type = pipeline.get("request_type", "")
    if request_type == RequestType.ACCESSORIES_ONLY.value:
        sre_dict = {
            "score": 0, "level": "not_applicable",
            "r_datos": 0, "r_autoportancia": 0,
            "r_geometria": 0, "r_sistema": 0,
            "breakdown": ["accessories_only: SRE skipped"],
            "recommendations": [], "alternative_thicknesses": [],
        }
        run_context.session_state["pipeline"]["sre"] = sre_dict
        return StepOutput(content=json.dumps(sre_dict, ensure_ascii=False))

    sre = calculate_sre(request)
    run_context.session_state["pipeline"]["sre"] = sre.to_dict()
    run_context.session_state["pipeline"]["_sre_obj"] = sre

    logger.info("sre: score=%d level=%s", sre.score, sre.level.value)

    return StepOutput(content=json.dumps(sre.to_dict(), ensure_ascii=False))


# ═══════════════════════════════════════════════════════════════════
# Step 5: BOM (Bill of Materials)
# ═══════════════════════════════════════════════════════════════════

def step_bom(step_input: StepInput, run_context: RunContext) -> StepOutput:
    """Generate Bill of Materials."""
    pipeline = run_context.session_state.get("pipeline", {})
    request: QuoteRequest = pipeline.get("_request_obj")
    if request is None:
        return StepOutput(content='{"error": "no request object"}')

    request_type = pipeline.get("request_type", "")
    if request_type == RequestType.ACCESSORIES_ONLY.value:
        bom = BOMResult(
            system_key="accessories_only",
            area_m2=0, panel_count=0,
            supports_per_panel=0, fixation_points=0,
        )
        run_context.session_state["pipeline"]["bom"] = bom.to_dict()
        run_context.session_state["pipeline"]["_bom_obj"] = bom
        return StepOutput(content=json.dumps(bom.to_dict(), ensure_ascii=False))

    svc = QuotationService
    bom = svc.calculate_bom(request)

    run_context.session_state["pipeline"]["bom"] = bom.to_dict()
    run_context.session_state["pipeline"]["_bom_obj"] = bom

    logger.info(
        "bom: system=%s panels=%d items=%d warnings=%d",
        bom.system_key, bom.panel_count, len(bom.items), len(bom.warnings),
    )

    return StepOutput(content=json.dumps(bom.to_dict(), ensure_ascii=False))


# ═══════════════════════════════════════════════════════════════════
# Step 6: Pricing
# ═══════════════════════════════════════════════════════════════════

def step_pricing(step_input: StepInput, run_context: RunContext) -> StepOutput:
    """Price all BOM items from KB sources. Never invents prices."""
    pipeline = run_context.session_state.get("pipeline", {})
    request: QuoteRequest = pipeline.get("_request_obj")
    bom: BOMResult = pipeline.get("_bom_obj")

    if request is None or bom is None:
        return StepOutput(content='{"error": "missing request or bom"}')

    pricing = QuotationService.calculate_pricing(bom, request)

    run_context.session_state["pipeline"]["pricing"] = pricing.to_dict()
    run_context.session_state["pipeline"]["_pricing_obj"] = pricing

    logger.info(
        "pricing: panels=$%.2f accessories=$%.2f total=$%.2f missing=%d",
        pricing.subtotal_panels_usd,
        pricing.subtotal_accessories_usd,
        pricing.subtotal_total_usd,
        len(pricing.missing_prices),
    )

    return StepOutput(content=json.dumps(pricing.to_dict(), ensure_ascii=False))


# ═══════════════════════════════════════════════════════════════════
# Step 7: Validate
# ═══════════════════════════════════════════════════════════════════

def step_validate(step_input: StepInput, run_context: RunContext) -> StepOutput:
    """Multi-layer validation (integrity, technical, commercial, math)."""
    pipeline = run_context.session_state.get("pipeline", {})
    request: QuoteRequest = pipeline.get("_request_obj")
    bom: BOMResult = pipeline.get("_bom_obj")
    pricing: PricingResult = pipeline.get("_pricing_obj")

    if request is None or bom is None or pricing is None:
        return StepOutput(content='{"error": "missing pipeline data"}')

    from panelin_v4.engine.sre_engine import SREResult as SREClass
    sre_obj = pipeline.get("_sre_obj")
    if sre_obj is None:
        sre_obj = calculate_sre(request)

    mode_str = pipeline.get("mode", "pre_cotizacion")
    mode_map = {
        "informativo": OperatingMode.INFORMATIVO,
        "pre_cotizacion": OperatingMode.PRE_COTIZACION,
        "formal": OperatingMode.FORMAL,
    }
    mode = mode_map.get(mode_str, OperatingMode.PRE_COTIZACION)

    validation = validate_quotation(
        request=request, sre=sre_obj, bom=bom, pricing=pricing, mode=mode,
    )

    run_context.session_state["pipeline"]["validation"] = validation.to_dict()

    confidence = _calculate_confidence(request, sre_obj, validation, pricing)
    status = _determine_status(mode, sre_obj, validation)

    run_context.session_state["pipeline"]["confidence"] = round(confidence, 1)
    run_context.session_state["pipeline"]["status"] = status

    logger.info(
        "validate: valid=%s formal=%s criticals=%d warnings=%d confidence=%.1f",
        validation.is_valid,
        validation.can_emit_formal,
        validation.critical_count,
        validation.warning_count,
        confidence,
    )

    return StepOutput(content=json.dumps({
        "validation": validation.to_dict(),
        "confidence": round(confidence, 1),
        "status": status,
    }, ensure_ascii=False))


# ═══════════════════════════════════════════════════════════════════
# Step 8: Respond (LLM)
# ═══════════════════════════════════════════════════════════════════

RESPOND_INSTRUCTIONS = """\
Eres Panelin, el asistente técnico-comercial de BMC Uruguay para cotizaciones de paneles de construcción.

REGLAS ABSOLUTAS:
1. Responde SIEMPRE en español
2. NUNCA inventes precios — si un precio no se encontró en la KB, di explícitamente "precio no disponible"
3. Muestra los precios con IVA 22% incluido (ya están incluidos en los datos)
4. Usa formato de moneda USD con 2 decimales
5. Si hay advertencias o datos faltantes, mencionálos claramente
6. Para cotizaciones formales, indica que se requiere confirmación de datos
7. NUNCA derivar a proveedores externos — siempre a agentes de ventas BMC Uruguay

FORMATO DE RESPUESTA:
- Saludo breve y profesional
- Resumen del pedido (producto, dimensiones, uso)
- Tabla de materiales con cantidades y precios
- Total general
- Advertencias o recomendaciones (si las hay)
- Próximos pasos

Si la solicitud es informativa, responde de forma breve y directa.
Si es pre-cotización, muestra el detalle completo con nota de "sujeto a confirmación".
Si es formal, incluye el quote_id y todos los datos del cliente.
"""


def _build_respond_agent(model_id: str = "gpt-4o") -> Agent:
    """Build the LLM agent for step 8 (response formatting)."""
    return Agent(
        name="PanelinResponder",
        model=OpenAIChat(id=model_id),
        instructions=[RESPOND_INSTRUCTIONS],
        markdown=True,
    )


# ═══════════════════════════════════════════════════════════════════
# Workflow Assembly
# ═══════════════════════════════════════════════════════════════════

def build_quotation_workflow(
    model_id: str = "gpt-4o",
) -> Workflow:
    """Build the complete Panelin quotation workflow.

    Steps 1-7: Pure Python functions ($0.00)
    Step 8: LLM agent for response formatting (~$0.02)
    """
    respond_agent = _build_respond_agent(model_id=model_id)

    workflow = Workflow(
        name="PanelinQuotationWorkflow",
        description="Pipeline de cotización determinístico de 7 etapas + respuesta LLM",
        steps=[
            Step(name="classify", executor=step_classify),
            Step(name="parse", executor=step_parse),
            Step(name="defaults", executor=step_defaults),
            Step(name="sre", executor=step_sre),
            Step(name="bom", executor=step_bom),
            Step(name="pricing", executor=step_pricing),
            Step(name="validate", executor=step_validate),
            Step(name="respond", agent=respond_agent),
        ],
    )

    return workflow
