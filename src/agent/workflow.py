"""
Panelin Agno — Quotation Workflow

Implements the 7-step deterministic quotation pipeline as an Agno Workflow.
Each step uses a pure Python function executor (cost: $0.00).
Only the final 'respond' step uses an LLM agent (~$0.02).

Pipeline:
    1. classify  — Determine request type & operating mode
    2. parse     — Extract structured data from Spanish free-text
    3. route     — Skip BOM/pricing for accessories-only or info requests
    4. sre       — Structural Risk Engine (0-100 score)
    5. bom       — Bill of Materials (6 construction systems)
    6. pricing   — Price lookup from KB (NEVER invented)
    7. validate  — 4-layer validation (integrity, technical, commercial, math)
    8. respond   — LLM formats the human-friendly response in Spanish
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Optional

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.workflow.workflow import Workflow
from agno.workflow.step import Step, StepOutput
from agno.workflow.condition import Condition
from agno.workflow.types import StepInput

from src.quotation.service import QuotationService


def _step_classify(step_input: StepInput) -> StepOutput:
    """Step 1: Classify the incoming request."""
    text = step_input.input or ""
    classification = QuotationService.classify(text)
    return StepOutput(
        content=json.dumps({
            "text": text,
            "classification": classification,
        }, ensure_ascii=False),
    )


def _step_parse(step_input: StepInput) -> StepOutput:
    """Step 2: Parse free-text into structured QuoteRequest."""
    prev = json.loads(step_input.previous_step_content or "{}")
    text = prev.get("text", "")
    parsed = QuotationService.parse(text)
    return StepOutput(
        content=json.dumps({
            **prev,
            "parsed": parsed,
        }, ensure_ascii=False),
    )


def _needs_full_pipeline(step_input: StepInput) -> bool:
    """Condition: True if request needs BOM/pricing (not info-only or accessories-only)."""
    prev = json.loads(step_input.previous_step_content or "{}")
    classification = prev.get("classification", {})
    req_type = classification.get("request_type", "")
    mode = classification.get("operating_mode", "")

    if mode == "informativo" and req_type == "info_only":
        return False
    return True


def _step_sre(step_input: StepInput) -> StepOutput:
    """Step 4: Calculate Structural Risk Engine score."""
    prev = json.loads(step_input.previous_step_content or "{}")
    parsed = prev.get("parsed", {})
    sre = QuotationService.calculate_sre(parsed)
    return StepOutput(
        content=json.dumps({**prev, "sre": sre}, ensure_ascii=False),
    )


def _step_bom(step_input: StepInput) -> StepOutput:
    """Step 5: Generate Bill of Materials."""
    prev = json.loads(step_input.previous_step_content or "{}")
    parsed = prev.get("parsed", {})
    bom = QuotationService.calculate_bom(parsed)
    return StepOutput(
        content=json.dumps({**prev, "bom": bom}, ensure_ascii=False),
    )


def _step_pricing(step_input: StepInput) -> StepOutput:
    """Step 6: Calculate pricing from KB."""
    prev = json.loads(step_input.previous_step_content or "{}")
    parsed = prev.get("parsed", {})
    bom = prev.get("bom", {})
    pricing = QuotationService.calculate_pricing(bom, parsed)
    return StepOutput(
        content=json.dumps({**prev, "pricing": pricing}, ensure_ascii=False),
    )


def _step_validate(step_input: StepInput) -> StepOutput:
    """Step 7: Multi-layer validation."""
    prev = json.loads(step_input.previous_step_content or "{}")
    parsed = prev.get("parsed", {})
    sre = prev.get("sre", {})
    bom = prev.get("bom", {})
    pricing = prev.get("pricing", {})
    mode = prev.get("classification", {}).get("operating_mode", "pre_cotizacion")
    validation = QuotationService.validate(parsed, sre, bom, pricing, mode)

    quote_id = f"PV5-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    result = {
        **prev,
        "validation": validation,
        "quote_id": quote_id,
        "timestamp": datetime.now().isoformat(),
    }
    return StepOutput(
        content=json.dumps(result, ensure_ascii=False),
    )


def _step_info_only(step_input: StepInput) -> StepOutput:
    """Handles info-only requests without full pipeline."""
    prev = json.loads(step_input.previous_step_content or "{}")
    prev["pipeline_skipped"] = True
    prev["skip_reason"] = "Solicitud informativa — no requiere cotización"
    return StepOutput(
        content=json.dumps(prev, ensure_ascii=False),
    )


def create_respond_agent(model_id: str = "gpt-4o", temperature: float = 0.3) -> Agent:
    """Create the LLM agent that formats quotation results as human-friendly Spanish."""
    return Agent(
        name="PanelinResponder",
        model=OpenAIChat(id=model_id, temperature=temperature),
        instructions=[
            "Eres Panelin, el asistente técnico-comercial de BMC Uruguay para paneles de construcción.",
            "Tu trabajo es presentar los resultados de cotización de forma clara y profesional en español.",
            "",
            "REGLAS ESTRICTAS:",
            "- NUNCA inventes precios. Usa EXCLUSIVAMENTE los datos del pipeline.",
            "- Todos los precios incluyen IVA 22%. NUNCA agregues IVA adicional.",
            "- Si hay precios faltantes, indícalo explícitamente.",
            "- Si hay warnings de validación, menciónalos como recomendaciones.",
            "- Si el SRE indica riesgo alto, sugiere alternativas (espesores mayores o apoyo intermedio).",
            "- Responde SIEMPRE en español.",
            "- Usa formato estructurado: resumen, detalle BOM, precios, total, observaciones.",
            "- Para cotizaciones pre, indica que es aproximada y requiere confirmación.",
            "- Para cotizaciones formales, indica que es vinculante y válida por 15 días.",
            "",
            "FORMATO DE RESPUESTA:",
            "📋 **Cotización [quote_id]** — [modo]",
            "📦 **Producto**: [familia] [sub_familia] [espesor]mm",
            "📐 **Área**: [largo]m × [ancho]m = [area]m²",
            "🔧 **BOM**: [panel_count] paneles + [n] accesorios",
            "💰 **Total**: USD [total] (IVA incluido)",
            "⚠️ **Observaciones**: [si las hay]",
        ],
        markdown=True,
    )


def create_quotation_workflow(
    model_id: str = "gpt-4o",
    temperature: float = 0.3,
) -> Workflow:
    """Create the Panelin quotation workflow with 7 deterministic steps + 1 LLM step."""

    respond_agent = create_respond_agent(model_id=model_id, temperature=temperature)

    workflow = Workflow(
        name="PanelinQuotationPipeline",
        steps=[
            Step(name="Classify", executor=_step_classify),
            Step(name="Parse", executor=_step_parse),
            Condition(
                name="NeedsFullPipeline",
                evaluator=_needs_full_pipeline,
                steps=[
                    Step(name="SRE", executor=_step_sre),
                    Step(name="BOM", executor=_step_bom),
                    Step(name="Pricing", executor=_step_pricing),
                    Step(name="Validate", executor=_step_validate),
                ],
                else_steps=[
                    Step(name="InfoOnly", executor=_step_info_only),
                ],
            ),
            Step(name="Respond", executor=respond_agent),
        ],
    )
    return workflow
