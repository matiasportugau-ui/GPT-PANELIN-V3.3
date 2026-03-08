"""Deterministic Agno workflow for Panelin quotations."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from typing import Any

from agno.agent import Agent
from agno.exceptions import OutputCheckError
from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat
from agno.run import RunContext
from agno.run.workflow import WorkflowRunOutput
from agno.workflow import Router, Step, StepInput, StepOutput, Steps, Workflow
from panelin_v4.engine.classifier import OperatingMode, RequestType, classify_request
from panelin_v4.engine.quotation_engine import (
    QuotationOutput,
    _apply_defaults,
    _calculate_confidence,
    _determine_status,
)
from panelin_v4.engine.bom_engine import BOMResult, calculate_bom
from panelin_v4.engine.parser import parse_request
from panelin_v4.engine.pricing_engine import PricingResult, calculate_pricing
from panelin_v4.engine.sre_engine import calculate_sre
from panelin_v4.engine.validation_engine import validate_quotation
from panelin_v4.evaluator.sai_engine import calculate_sai
from src.core.config import Settings

MODE_MAP: dict[str, OperatingMode] = {
    "informativo": OperatingMode.INFORMATIVO,
    "pre_cotizacion": OperatingMode.PRE_COTIZACION,
    "formal": OperatingMode.FORMAL,
}

MONEY_PATTERN = re.compile(r"(?:USD|US\\$|\\$)\\s*([0-9][0-9.,]*)", re.IGNORECASE)


def _extract_text_input(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _to_mode(mode_value: str | None) -> OperatingMode | None:
    if not mode_value:
        return None
    return MODE_MAP.get(mode_value.strip().lower())


def _build_processing_notes(classification: dict[str, Any], assumptions: list[str]) -> list[str]:
    notes: list[str] = []
    request_type = classification.get("request_type")
    if assumptions:
        notes.append("Pre-cotización con supuestos declarados para completar datos faltantes.")
    if request_type == RequestType.UPDATE.value:
        notes.append("Solicitud de actualización detectada. Recalcular diferencial sugerido.")
    if request_type == RequestType.ACCESSORIES_ONLY.value:
        notes.append("Solicitud de accesorios: se omite cálculo estructural de paneles.")
    return notes


def _collect_canonical_prices(pricing_payload: dict[str, Any]) -> list[float]:
    prices: list[float] = []
    for item in pricing_payload.get("items", []):
        if "unit_price_usd" in item:
            prices.append(float(item["unit_price_usd"]))
        if "subtotal_usd" in item:
            prices.append(float(item["subtotal_usd"]))
    for key in ("subtotal_panels_usd", "subtotal_accessories_usd", "subtotal_total_usd"):
        value = pricing_payload.get(key)
        if value is not None:
            prices.append(float(value))
    return sorted({round(price, 2) for price in prices})


def _extract_money_values(text: str) -> list[float]:
    found: list[float] = []
    for match in MONEY_PATTERN.findall(text):
        normalized = match.replace(".", "").replace(",", ".")
        try:
            found.append(round(float(normalized), 2))
        except ValueError:
            continue
    return found


def _price_output_guardrail(run_output, run_context: RunContext | None = None, **_: Any) -> None:
    """Block responses that mention prices outside deterministic pipeline results."""
    if run_context is None or run_context.session_state is None:
        return
    canonical = run_context.session_state.get("canonical_prices_usd", [])
    if not canonical or not isinstance(run_output.content, str):
        return

    allowed = [round(float(value), 2) for value in canonical]
    observed = _extract_money_values(run_output.content)
    unexpected = [
        value
        for value in observed
        if all(abs(value - allowed_value) > 0.05 for allowed_value in allowed)
    ]
    if unexpected:
        raise OutputCheckError(
            message=f"Se detectaron precios fuera de la KB: {unexpected}",
            additional_data={"allowed_prices_usd": allowed, "observed_prices_usd": observed},
        )


def _make_response_agent(settings: Settings) -> Agent | None:
    if not settings.enable_llm_response:
        return None

    provider = settings.model_provider.strip().lower()
    if provider == "anthropic":
        if not settings.anthropic_api_key:
            return None
        model = Claude(id=settings.anthropic_model_id, api_key=settings.anthropic_api_key)
    else:
        if not settings.openai_api_key:
            return None
        model = OpenAIChat(id=settings.openai_model_id, api_key=settings.openai_api_key)

    return Agent(
        name="panelin_response_formatter",
        model=model,
        markdown=True,
        parse_response=False,
        post_hooks=[_price_output_guardrail],
        instructions=[
            "Responde SIEMPRE en español.",
            "Eres redactor técnico-comercial de BMC Uruguay.",
            "No inventes precios ni cantidades: usa solo los valores del JSON recibido.",
            "Si faltan datos para cotización formal, pide exactamente los campos faltantes.",
            "Incluye: resumen, riesgos SRE, totales y próximos pasos.",
        ],
    )


def _flatten_step_outputs(step_outputs: list[StepOutput]) -> dict[str, StepOutput]:
    """Index nested workflow outputs by step_name."""
    indexed: dict[str, StepOutput] = {}

    def _walk(step_output: StepOutput) -> None:
        if step_output.step_name:
            indexed[step_output.step_name] = step_output
        for nested in step_output.steps or []:
            _walk(nested)

    for item in step_outputs:
        _walk(item)
    return indexed


def build_panelin_workflow(settings: Settings, db: Any | None = None) -> Workflow:
    """Create deterministic workflow: classify→parse→SRE→(router BOM/pricing)→validate→SAI→respond."""

    response_agent = _make_response_agent(settings)

    def classify_step(step_input: StepInput, run_context: RunContext | None = None) -> StepOutput:
        text = _extract_text_input(step_input.input)
        forced_mode = _to_mode((step_input.additional_data or {}).get("mode"))
        classification = classify_request(text, force_mode=forced_mode)
        if run_context and run_context.session_state is not None:
            run_context.session_state["panelin_mode"] = classification.operating_mode.value
        return StepOutput(
            content={
                "text": text,
                "classification": classification.to_dict(),
            }
        )

    def parse_step(step_input: StepInput) -> StepOutput:
        classify_output = step_input.get_step_output("classify_request")
        if classify_output is None:
            raise ValueError("No hay salida de clasificación")
        classify_payload = classify_output.content
        if not isinstance(classify_payload, dict):
            raise ValueError("Formato inválido en classify_request")

        mode = OperatingMode(classify_payload["classification"]["operating_mode"])
        request = parse_request(classify_payload["text"])
        assumptions = _apply_defaults(request, mode)
        request.assumptions_used.extend(assumptions)
        return StepOutput(
            content={
                "mode": mode.value,
                "request_obj": request,
                "request": request.to_dict(),
                "assumptions": assumptions,
            }
        )

    def sre_step(step_input: StepInput) -> StepOutput:
        parse_output = step_input.get_step_output("parse_request")
        if parse_output is None or not isinstance(parse_output.content, dict):
            raise ValueError("No hay salida de parseo")
        request_obj = parse_output.content["request_obj"]
        sre = calculate_sre(request_obj)
        return StepOutput(content={"sre_obj": sre, "sre": sre.to_dict()})

    def bom_step(step_input: StepInput) -> StepOutput:
        parse_output = step_input.get_step_output("parse_request")
        if parse_output is None or not isinstance(parse_output.content, dict):
            raise ValueError("No hay salida de parseo")
        request_obj = parse_output.content["request_obj"]

        bom = BOMResult(
            system_key="unknown",
            area_m2=0,
            panel_count=0,
            supports_per_panel=0,
            fixation_points=0,
        )
        can_calculate = (
            request_obj.familia is not None
            and request_obj.thickness_mm is not None
            and request_obj.uso is not None
            and (request_obj.geometry.length_m is not None or request_obj.geometry.panel_lengths)
        )
        if can_calculate:
            length_m = request_obj.geometry.length_m or 0
            width_m = request_obj.geometry.width_m or 0
            if not width_m and request_obj.geometry.panel_count:
                width_m = request_obj.geometry.panel_count * 1.12
            if length_m > 0 and width_m > 0:
                bom = calculate_bom(
                    familia=request_obj.familia,
                    sub_familia=request_obj.sub_familia or "EPS",
                    thickness_mm=request_obj.thickness_mm,
                    uso=request_obj.uso,
                    length_m=length_m,
                    width_m=width_m,
                    structure_type=request_obj.structure_type or "metal",
                    panel_count=request_obj.geometry.panel_count,
                    panel_lengths=request_obj.geometry.panel_lengths or None,
                    roof_type=request_obj.roof_type,
                    span_m=request_obj.span_m,
                )
        return StepOutput(content={"bom_obj": bom, "bom": bom.to_dict(), "skipped": False})

    def pricing_step(step_input: StepInput) -> StepOutput:
        parse_output = step_input.get_step_output("parse_request")
        bom_output = step_input.get_step_output("calculate_bom")
        if parse_output is None or bom_output is None:
            raise ValueError("No hay insumos para pricing")
        if not isinstance(parse_output.content, dict) or not isinstance(bom_output.content, dict):
            raise ValueError("Formato inválido en parseo/BOM")

        request_obj = parse_output.content["request_obj"]
        bom_obj = bom_output.content["bom_obj"]
        pricing = PricingResult()
        if bom_obj.panel_count > 0 and request_obj.familia and request_obj.thickness_mm:
            pricing = calculate_pricing(
                bom=bom_obj,
                familia=request_obj.familia,
                sub_familia=request_obj.sub_familia or "EPS",
                thickness_mm=request_obj.thickness_mm,
                panel_area_m2=bom_obj.area_m2,
                iva_mode=request_obj.iva_mode,
            )
        return StepOutput(content={"pricing_obj": pricing, "pricing": pricing.to_dict(), "skipped": False})

    def skip_bom_pricing_step(step_input: StepInput) -> StepOutput:
        _ = step_input
        bom = BOMResult(
            system_key="accessories_only",
            area_m2=0,
            panel_count=0,
            supports_per_panel=0,
            fixation_points=0,
            warnings=["BOM omitido por solicitud de accesorios únicamente."],
        )
        pricing = PricingResult(
            warnings=["Pricing de paneles omitido por solicitud de accesorios únicamente."],
        )
        return StepOutput(
            content={
                "bom_obj": bom,
                "bom": bom.to_dict(),
                "pricing_obj": pricing,
                "pricing": pricing.to_dict(),
                "skipped": True,
            }
        )

    def bom_router_selector(step_input: StepInput) -> str:
        classify_output = step_input.get_step_output("classify_request")
        if classify_output is None or not isinstance(classify_output.content, dict):
            return "full_bom_pricing"
        request_type = classify_output.content["classification"].get("request_type")
        if request_type == RequestType.ACCESSORIES_ONLY.value:
            return "skip_bom_pricing"
        return "full_bom_pricing"

    def validate_step(step_input: StepInput) -> StepOutput:
        parse_output = step_input.get_step_output("parse_request")
        sre_output = step_input.get_step_output("calculate_sre")
        if parse_output is None or sre_output is None:
            raise ValueError("No hay insumos para validación")
        if not isinstance(parse_output.content, dict) or not isinstance(sre_output.content, dict):
            raise ValueError("Formato inválido en parseo/SRE")

        request_obj = parse_output.content["request_obj"]
        sre_obj = sre_output.content["sre_obj"]
        mode = OperatingMode(parse_output.content["mode"])

        bom_output = step_input.get_step_output("calculate_bom")
        pricing_output = step_input.get_step_output("calculate_pricing")
        skip_output = step_input.get_step_output("skip_bom_pricing")

        if bom_output is not None and pricing_output is not None:
            bom_obj = bom_output.content["bom_obj"]
            pricing_obj = pricing_output.content["pricing_obj"]
        elif skip_output is not None and isinstance(skip_output.content, dict):
            bom_obj = skip_output.content["bom_obj"]
            pricing_obj = skip_output.content["pricing_obj"]
        else:
            raise ValueError("No se pudo resolver BOM/Pricing para validación")

        validation = validate_quotation(
            request=request_obj,
            sre=sre_obj,
            bom=bom_obj,
            pricing=pricing_obj,
            mode=mode,
        )
        confidence = _calculate_confidence(request_obj, sre_obj, validation, pricing_obj)
        status = _determine_status(mode, sre_obj, validation)

        return StepOutput(
            content={
                "validation_obj": validation,
                "validation": validation.to_dict(),
                "confidence_score": round(confidence, 1),
                "status": status,
            }
        )

    def sai_step(step_input: StepInput, run_context: RunContext | None = None) -> StepOutput:
        classify_output = step_input.get_step_output("classify_request")
        parse_output = step_input.get_step_output("parse_request")
        sre_output = step_input.get_step_output("calculate_sre")
        validate_output = step_input.get_step_output("validate_quotation")
        if not all([classify_output, parse_output, sre_output, validate_output]):
            raise ValueError("No hay insumos suficientes para SAI")

        if not isinstance(classify_output.content, dict):
            raise ValueError("Formato inválido de clasificación")
        if not isinstance(parse_output.content, dict):
            raise ValueError("Formato inválido de parseo")
        if not isinstance(sre_output.content, dict):
            raise ValueError("Formato inválido de SRE")
        if not isinstance(validate_output.content, dict):
            raise ValueError("Formato inválido de validación")

        bom_output = step_input.get_step_output("calculate_bom")
        pricing_output = step_input.get_step_output("calculate_pricing")
        skip_output = step_input.get_step_output("skip_bom_pricing")

        if bom_output is not None and pricing_output is not None:
            bom_dict = bom_output.content["bom"]
            pricing_dict = pricing_output.content["pricing"]
            pricing_obj = pricing_output.content["pricing_obj"]
        elif skip_output is not None and isinstance(skip_output.content, dict):
            bom_dict = skip_output.content["bom"]
            pricing_dict = skip_output.content["pricing"]
            pricing_obj = skip_output.content["pricing_obj"]
        else:
            raise ValueError("No se pudo resolver BOM/Pricing para SAI")

        quote_id = f"PV4-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        notes = _build_processing_notes(
            classification=classify_output.content["classification"],
            assumptions=parse_output.content["assumptions"],
        )
        quotation = QuotationOutput(
            quote_id=quote_id,
            timestamp=datetime.now().isoformat(),
            mode=parse_output.content["mode"],
            level=sre_output.content["sre"]["level"],
            status=validate_output.content["status"],
            classification=classify_output.content["classification"],
            request=parse_output.content["request"],
            sre=sre_output.content["sre"],
            bom=bom_dict,
            pricing=pricing_dict,
            validation=validate_output.content["validation"],
            assumptions_used=parse_output.content["request_obj"].assumptions_used,
            confidence_score=validate_output.content["confidence_score"],
            processing_notes=notes,
        )
        sai = calculate_sai(quotation)
        canonical_prices = _collect_canonical_prices(pricing_dict)

        if run_context is not None and run_context.session_state is not None:
            run_context.session_state["canonical_prices_usd"] = canonical_prices
            run_context.session_state["last_quote_id"] = quote_id

        return StepOutput(
            content={
                "quotation": quotation.to_dict(),
                "sai": sai.to_dict(),
                "canonical_prices_usd": canonical_prices,
                "pricing_obj": pricing_obj,
            }
        )

    def deterministic_response_step(step_input: StepInput) -> StepOutput:
        sai_output = step_input.get_step_output("calculate_sai")
        if sai_output is None or not isinstance(sai_output.content, dict):
            raise ValueError("No hay payload final para respuesta")
        quotation = sai_output.content["quotation"]
        sai = sai_output.content["sai"]
        response = (
            f"Cotización {quotation['quote_id']} ({quotation['mode']})\n"
            f"- Estado: {quotation['status']}\n"
            f"- Total materiales (USD): {quotation['pricing'].get('subtotal_total_usd', 0):.2f}\n"
            f"- SAI: {sai['score']} ({sai['grade']})\n"
            f"- Riesgo SRE: {quotation['sre'].get('score', 0)}\n"
        )
        return StepOutput(content=response)

    deterministic_steps = [
        Step(name="classify_request", executor=classify_step),
        Step(name="parse_request", executor=parse_step),
        Step(name="calculate_sre", executor=sre_step),
        Router(
            name="bom_pricing_router",
            selector=bom_router_selector,
            choices=[
                Steps(
                    name="full_bom_pricing",
                    steps=[
                        Step(name="calculate_bom", executor=bom_step),
                        Step(name="calculate_pricing", executor=pricing_step),
                    ],
                ),
                Step(name="skip_bom_pricing", executor=skip_bom_pricing_step),
            ],
        ),
        Step(name="validate_quotation", executor=validate_step),
        Step(name="calculate_sai", executor=sai_step),
    ]

    if response_agent is not None:
        response_step = Step(name="format_response", agent=response_agent)
    else:
        response_step = Step(name="format_response", executor=deterministic_response_step)

    return Workflow(
        name="panelin_v4_deterministic_workflow",
        db=db,
        steps=[*deterministic_steps, response_step],
        cache_session=True,
    )


def run_panelin_workflow(
    workflow: Workflow,
    *,
    text: str,
    mode: str = "pre_cotizacion",
    session_id: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Execute workflow and return both final text and structured quotation payload."""
    run_output = workflow.run(
        input=text,
        additional_data={"mode": mode},
        session_id=session_id,
        user_id=user_id,
    )
    if not isinstance(run_output, WorkflowRunOutput):
        raise RuntimeError("Workflow execution returned a stream; expected final output.")

    indexed = _flatten_step_outputs(run_output.step_results or [])
    sai_output = indexed.get("calculate_sai")
    if sai_output is None or not isinstance(sai_output.content, dict):
        raise RuntimeError("No se encontró salida estructurada de calculate_sai.")

    return {
        "session_id": run_output.session_id,
        "response_text": str(run_output.content),
        "quote": sai_output.content["quotation"],
        "sai": sai_output.content["sai"],
        "canonical_prices_usd": sai_output.content.get("canonical_prices_usd", []),
        "run_id": run_output.run_id,
    }

