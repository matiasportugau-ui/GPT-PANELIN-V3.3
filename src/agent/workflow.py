"""
Panelin v5.0 — Agno Workflow

Deterministic quotation pipeline as an Agno Workflow with 7 sequential steps.
Each step uses a plain Python executor ($0.00) except the final step which
uses an LLM agent to format the response in Spanish (~$0.02).

Pipeline:
    1. classify   — Determine request type and operating mode        [Python]
    2. parse      — Free-text → structured QuoteRequest              [Python]
    3. defaults   — Apply default assumptions for missing data       [Python]
    4. sre        — Structural Risk Engine (score 0-100)             [Python]
    5. bom        — Bill of Materials generation                     [Python]
    6. pricing    — Price lookup from KB (NEVER invented)            [Python]
    7. validate   — Multi-layer validation                           [Python]
    8. respond    — Format response in Spanish for the user          [LLM Agent]

Steps 1-7 are DETERMINISTIC (pure Python, no LLM).
Step 8 uses the LLM ONLY for natural language formatting.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Optional

from agno.agent.agent import Agent
from agno.models.openai import OpenAIChat
from agno.workflow.workflow import Workflow
from agno.workflow.step import Step
from agno.workflow.condition import Condition
from agno.workflow.types import StepInput, StepOutput

from src.core.config import get_settings
from src.quotation.service import QuotationService


def _step_classify(step_input: StepInput) -> StepOutput:
    """Step 1: Classify the request type and operating mode."""
    text = step_input.get_input_as_string() or ""
    result = QuotationService.classify(text)
    return StepOutput(content=json.dumps(result, ensure_ascii=False))


def _step_parse(step_input: StepInput) -> StepOutput:
    """Step 2: Parse free-text into structured QuoteRequest."""
    text = step_input.get_input_as_string() or ""
    result = QuotationService.parse(text)
    return StepOutput(content=json.dumps(result, ensure_ascii=False))


def _step_apply_defaults(step_input: StepInput) -> StepOutput:
    """Step 3: Apply default assumptions for missing data."""
    classify_data = _get_step_data(step_input, "classify")
    parsed_data = _get_step_data(step_input, "parse")

    mode = classify_data.get("operating_mode", "pre_cotizacion")

    if mode != "formal":
        if parsed_data.get("uso") in ("techo",) and parsed_data.get("span_m") is None:
            parsed_data["span_m"] = 1.5
            parsed_data.setdefault("assumptions_used", []).append(
                "span_m assumed 1.5m (residential default)"
            )
        if not parsed_data.get("structure_type"):
            uso = parsed_data.get("uso", "techo")
            defaults = {"techo": "metal", "pared": "metal", "camara": "hormigon"}
            struct = defaults.get(uso, "metal")
            parsed_data["structure_type"] = struct
            parsed_data.setdefault("assumptions_used", []).append(
                f"structure_type assumed '{struct}' for {uso}"
            )
        geo = parsed_data.get("geometry", {})
        if not geo.get("width_m") and geo.get("panel_count"):
            geo["width_m"] = geo["panel_count"] * 1.12
            parsed_data.setdefault("assumptions_used", []).append(
                f"width_m derived from panel_count ({geo['panel_count']}) × 1.12m"
            )

    return StepOutput(content=json.dumps({
        "parsed": parsed_data,
        "classification": classify_data,
        "mode": mode,
    }, ensure_ascii=False))


def _step_sre(step_input: StepInput) -> StepOutput:
    """Step 4: Calculate Structural Risk Engine score."""
    defaults_data = _get_step_data(step_input, "apply_defaults")
    parsed = defaults_data.get("parsed", {})
    sre = QuotationService.compute_sre(parsed)
    return StepOutput(content=json.dumps(sre, ensure_ascii=False))


def _is_not_accessories_only(step_input: StepInput) -> bool:
    """Condition: skip BOM/pricing if this is an accessories-only request."""
    defaults_data = _get_step_data(step_input, "apply_defaults")
    classification = defaults_data.get("classification", {})
    return classification.get("request_type") != "accessories_only"


def _step_bom(step_input: StepInput) -> StepOutput:
    """Step 5: Calculate Bill of Materials."""
    defaults_data = _get_step_data(step_input, "apply_defaults")
    parsed = defaults_data.get("parsed", {})
    bom = QuotationService.compute_bom(parsed)
    return StepOutput(content=json.dumps(bom, ensure_ascii=False))


def _step_pricing(step_input: StepInput) -> StepOutput:
    """Step 6: Price lookup from KB. NEVER invents prices."""
    defaults_data = _get_step_data(step_input, "apply_defaults")
    parsed = defaults_data.get("parsed", {})
    bom_data = _get_step_data(step_input, "bom")
    pricing = QuotationService.compute_pricing(bom_data, parsed)
    return StepOutput(content=json.dumps(pricing, ensure_ascii=False))


def _step_validate(step_input: StepInput) -> StepOutput:
    """Step 7: Multi-layer validation."""
    defaults_data = _get_step_data(step_input, "apply_defaults")
    parsed = defaults_data.get("parsed", {})
    mode = defaults_data.get("mode", "pre_cotizacion")
    sre_data = _get_step_data(step_input, "sre")
    bom_data = _get_step_data(step_input, "bom")
    pricing_data = _get_step_data(step_input, "pricing")

    if not bom_data:
        bom_data = {
            "system_key": "unknown", "area_m2": 0, "panel_count": 0,
            "supports_per_panel": 0, "fixation_points": 0, "items": [], "warnings": [],
        }
    if not pricing_data:
        pricing_data = {
            "items": [], "subtotal_panels_usd": 0, "subtotal_accessories_usd": 0,
            "subtotal_total_usd": 0, "iva_mode": "incluido", "warnings": [], "missing_prices": [],
        }

    validation = QuotationService.validate(parsed, sre_data, bom_data, pricing_data, mode)

    quote_id = f"PV5-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    result = {
        "quote_id": quote_id,
        "timestamp": datetime.now().isoformat(),
        "mode": mode,
        "classification": defaults_data.get("classification", {}),
        "request": parsed,
        "sre": sre_data,
        "bom": bom_data,
        "pricing": pricing_data,
        "validation": validation,
        "assumptions_used": parsed.get("assumptions_used", []),
    }

    return StepOutput(content=json.dumps(result, ensure_ascii=False))


def _get_step_data(step_input: StepInput, step_name: str) -> dict:
    """Retrieve and parse the output from a named previous step."""
    content = step_input.get_step_content(step_name)
    if content is None:
        content = step_input.previous_step_content
    if content is None:
        return {}
    if isinstance(content, dict):
        return content
    if isinstance(content, str):
        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def create_quotation_workflow(
    db: Any = None,
    session_id: Optional[str] = None,
) -> Workflow:
    """Build the Panelin quotation workflow.

    7 deterministic Python steps + 1 conditional gate for accessories-only.
    The LLM is used only in the final response-formatting step via the agent.
    """
    settings = get_settings()

    respond_agent = Agent(
        name="panelin_formatter",
        model=OpenAIChat(
            id=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=settings.openai_temperature,
        ),
        instructions=[
            "Sos Panelin, asistente técnico-comercial de BMC Uruguay.",
            "Respondé SIEMPRE en español.",
            "Formateá la cotización de forma clara y profesional.",
            "Los precios INCLUYEN IVA 22%. NUNCA inventes precios.",
            "Si hay campos faltantes o warnings, mencionálos al usuario.",
            "Usá formato de tabla o lista para los ítems del BOM.",
            "Incluí el quote_id, modo, y SRE level en la respuesta.",
            "Si la cotización tiene status 'blocked' o 'requires_review', explicá por qué.",
        ],
        markdown=True,
    )

    workflow = Workflow(
        name="PanelinQuotation",
        description="Pipeline determinístico de cotización de paneles BMC Uruguay",
        db=db,
        session_id=session_id,
        steps=[
            Step(name="classify", executor=_step_classify, description="Clasificar tipo de solicitud"),
            Step(name="parse", executor=_step_parse, description="Parsear texto a datos estructurados"),
            Step(name="apply_defaults", executor=_step_apply_defaults, description="Aplicar valores por defecto"),
            Step(name="sre", executor=_step_sre, description="Calcular riesgo estructural"),
            Condition(
                name="bom_gate",
                evaluator=_is_not_accessories_only,
                description="Saltar BOM/pricing si es solo accesorios",
                steps=[
                    Step(name="bom", executor=_step_bom, description="Generar Bill of Materials"),
                    Step(name="pricing", executor=_step_pricing, description="Buscar precios en KB"),
                ],
            ),
            Step(name="validate", executor=_step_validate, description="Validación multi-capa"),
            Step(name="respond", agent=respond_agent, description="Formatear respuesta en español"),
        ],
    )

    return workflow
