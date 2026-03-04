"""Deterministic Agno workflow for Panelin quotation pipeline."""

from __future__ import annotations

import json
from typing import Any, Optional

from agno.agent import Agent
from agno.db.base import AsyncBaseDb, BaseDb
from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat
from agno.run.base import RunContext
from agno.workflow import Router, Step, StepInput, StepOutput, Workflow
from pydantic import BaseModel, Field

from src.core.config import Settings
from src.quotation.service import QuotationService


class WorkflowRequest(BaseModel):
    """Input contract for panelin workflow executions."""

    text: str = Field(..., min_length=1)
    mode: str = Field(default="pre_cotizacion")
    client_name: str | None = None
    client_phone: str | None = None
    client_location: str | None = None


def _build_response_agent(settings: Settings) -> Agent:
    if settings.model_provider == "anthropic":
        model = Claude(id=settings.anthropic_model_id, api_key=settings.anthropic_api_key)
    else:
        model = OpenAIChat(id=settings.openai_model_id, api_key=settings.openai_api_key)

    return Agent(
        id="panelin-workflow-responder",
        name="Panelin Workflow Responder",
        model=model,
        markdown=True,
        instructions=[
            "Responde SIEMPRE en español.",
            "Nunca inventes precios, cantidades ni especificaciones.",
            "Usa únicamente los datos del JSON recibido.",
            "Si faltan precios o hay warnings, decláralos explícitamente.",
            "Entrega resumen claro con totales, estado de validación y próximos pasos.",
        ],
    )


def build_panelin_workflow(
    settings: Settings,
    db: BaseDb | AsyncBaseDb | None = None,
    service: QuotationService | None = None,
) -> Workflow:
    """Build the deterministic 7-step workflow + response formatter."""
    quotation_service = service or QuotationService()

    def ensure_state(run_context: RunContext | None) -> dict[str, Any]:
        if run_context is None:
            return {}
        if run_context.session_state is None:
            run_context.session_state = {}
        return run_context.session_state

    def read_payload(raw_input: Any) -> dict[str, Any]:
        if isinstance(raw_input, dict):
            payload = dict(raw_input)
        elif isinstance(raw_input, str):
            payload = {"text": raw_input}
        elif isinstance(raw_input, BaseModel):
            payload = raw_input.model_dump()
        else:
            raise ValueError("Workflow input must be dict, string, or pydantic model")

        if not payload.get("text"):
            raise ValueError("Field 'text' is required")
        return payload

    def classify_step(step_input: StepInput, run_context: RunContext) -> StepOutput:
        state = ensure_state(run_context)
        payload = read_payload(step_input.input)
        force_mode = quotation_service.resolve_mode(payload.get("mode")) if payload.get("mode") else None
        classification = quotation_service.classify(payload["text"], mode=force_mode)
        state["payload"] = payload
        state["classification"] = classification.to_dict()
        return StepOutput(content=classification.to_dict())

    def parse_step(step_input: StepInput, run_context: RunContext) -> StepOutput:
        state = ensure_state(run_context)
        payload = state.get("payload") or read_payload(step_input.input)
        classification_dict = state.get("classification")
        if not classification_dict:
            raise ValueError("Classification state missing before parse step")

        mode = quotation_service.classification_from_dict(classification_dict).operating_mode
        request = quotation_service.parse(payload["text"])
        quotation_service.enrich_request(
            request=request,
            mode=mode,
            client_name=payload.get("client_name"),
            client_phone=payload.get("client_phone"),
            client_location=payload.get("client_location"),
        )
        state["request"] = request.to_dict()
        return StepOutput(content=state["request"])

    def sre_step(_: StepInput, run_context: RunContext) -> StepOutput:
        state = ensure_state(run_context)
        request_dict = state.get("request")
        if not request_dict:
            raise ValueError("Request state missing before SRE step")
        request = quotation_service.request_from_dict(request_dict)
        sre = quotation_service.calculate_sre(request)
        state["sre"] = sre.to_dict()
        return StepOutput(content=state["sre"])

    def select_bom_pricing_path(
        _: StepInput,
        session_state: dict[str, Any],
        step_choices: list[Any],
    ) -> Any:
        classification = session_state.get("classification", {})
        if classification.get("request_type") == "accessories_only":
            return step_choices[0]
        return step_choices[1]

    def skip_bom_step(_: StepInput, run_context: RunContext) -> StepOutput:
        state = ensure_state(run_context)
        empty_bom = {
            "system_key": "accessories_only",
            "area_m2": 0,
            "panel_count": 0,
            "supports_per_panel": 0,
            "fixation_points": 0,
            "items": [],
            "warnings": ["BOM omitido: solicitud de accesorios únicamente."],
        }
        state["bom"] = empty_bom
        return StepOutput(content=empty_bom)

    def skip_pricing_step(_: StepInput, run_context: RunContext) -> StepOutput:
        state = ensure_state(run_context)
        empty_pricing = {
            "items": [],
            "subtotal_panels_usd": 0.0,
            "subtotal_accessories_usd": 0.0,
            "subtotal_total_usd": 0.0,
            "iva_mode": "incluido",
            "warnings": ["Pricing de paneles omitido para solicitud de accesorios."],
            "missing_prices": [],
        }
        state["pricing"] = empty_pricing
        return StepOutput(content=empty_pricing)

    def bom_step(_: StepInput, run_context: RunContext) -> StepOutput:
        state = ensure_state(run_context)
        request_dict = state.get("request")
        if not request_dict:
            raise ValueError("Request state missing before BOM step")
        request = quotation_service.request_from_dict(request_dict)
        bom = quotation_service.calculate_bom(request)
        state["bom"] = bom.to_dict()
        return StepOutput(content=state["bom"])

    def pricing_step(_: StepInput, run_context: RunContext) -> StepOutput:
        state = ensure_state(run_context)
        request_dict = state.get("request")
        bom_dict = state.get("bom")
        if not request_dict or not bom_dict:
            raise ValueError("Request/BOM state missing before pricing step")
        request = quotation_service.request_from_dict(request_dict)
        bom = quotation_service.bom_from_dict(bom_dict)
        pricing = quotation_service.calculate_pricing(request, bom)
        state["pricing"] = pricing.to_dict()
        return StepOutput(content=state["pricing"])

    def validation_step(_: StepInput, run_context: RunContext) -> StepOutput:
        state = ensure_state(run_context)
        classification_dict = state.get("classification")
        request_dict = state.get("request")
        sre_dict = state.get("sre")
        bom_dict = state.get("bom")
        pricing_dict = state.get("pricing")
        if not all([classification_dict, request_dict, sre_dict, bom_dict, pricing_dict]):
            raise ValueError("Missing state before validation step")

        classification = quotation_service.classification_from_dict(classification_dict)
        request = quotation_service.request_from_dict(request_dict)
        sre = quotation_service.sre_from_dict(sre_dict)
        bom = quotation_service.bom_from_dict(bom_dict)
        pricing = quotation_service.pricing_from_dict(pricing_dict)

        validation = quotation_service.validate(
            request=request,
            sre=sre,
            bom=bom,
            pricing=pricing,
            mode=classification.operating_mode,
        )
        output = quotation_service.build_output(
            classification=classification,
            request=request,
            sre=sre,
            bom=bom,
            pricing=pricing,
            validation=validation,
        )

        state["validation"] = validation.to_dict()
        state["output"] = output.to_dict()
        return StepOutput(content={"validation": state["validation"], "output": state["output"]})

    def sai_step(_: StepInput, run_context: RunContext) -> StepOutput:
        state = ensure_state(run_context)
        output_dict = state.get("output")
        if not output_dict:
            raise ValueError("Missing quotation output before SAI step")

        output = quotation_service.output_from_dict(output_dict)
        sai = quotation_service.calculate_sai(output)

        state["sai"] = sai.to_dict()
        state["response_payload"] = {
            "quote": output.to_dict(),
            "sai": sai.to_dict(),
        }
        state["quotes_generated"] = int(state.get("quotes_generated", 0)) + 1
        return StepOutput(content=json.dumps(state["response_payload"], ensure_ascii=False))

    def deterministic_response_step(_: StepInput, run_context: RunContext) -> StepOutput:
        state = ensure_state(run_context)
        payload = state.get("response_payload", {})
        quote = payload.get("quote", {})
        sai = payload.get("sai", {})
        pricing = quote.get("pricing", {})
        validation = quote.get("validation", {})

        message = (
            f"Cotización {quote.get('quote_id', 'N/A')} ({quote.get('mode', 'pre_cotizacion')}).\n"
            f"Total USD: {pricing.get('subtotal_total_usd', 0)}.\n"
            f"Estado: {quote.get('status', 'draft')} | "
            f"Críticos: {validation.get('critical_count', 0)} | "
            f"Warnings: {validation.get('warning_count', 0)}.\n"
            f"SAI: {sai.get('score', 0)} ({sai.get('grade', 'F')})."
        )
        return StepOutput(content=message)

    accessories_path = [
        Step(name="skip_bom_for_accessories", executor=skip_bom_step),
        Step(name="skip_pricing_for_accessories", executor=skip_pricing_step),
    ]
    full_path = [
        Step(name="calculate_bom", executor=bom_step),
        Step(name="calculate_pricing", executor=pricing_step),
    ]

    response_step: Step
    if settings.enable_llm_response_step and (
        settings.openai_api_key or settings.anthropic_api_key
    ):
        response_step = Step(
            name="format_user_response_llm",
            agent=_build_response_agent(settings),
        )
    else:
        response_step = Step(
            name="format_user_response_deterministic",
            executor=deterministic_response_step,
        )

    return Workflow(
        id="panelin-quotation-workflow",
        name="Panelin Deterministic Workflow",
        description=(
            "Workflow secuencial determinístico: classify → parse → SRE → "
            "router(BOM/pricing) → validate → SAI → respuesta."
        ),
        db=db,
        input_schema=WorkflowRequest,
        session_state={"quotes_generated": 0},
        steps=[
            Step(name="classify_request", executor=classify_step),
            Step(name="parse_request", executor=parse_step),
            Step(name="calculate_sre", executor=sre_step),
            Router(
                name="route_bom_pricing",
                choices=[accessories_path, full_path],
                selector=select_bom_pricing_path,
            ),
            Step(name="validate_quote", executor=validation_step),
            Step(name="calculate_sai", executor=sai_step),
            response_step,
        ],
    )
