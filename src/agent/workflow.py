from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from agno.agent import Agent
from agno.workflow import Workflow
from agno.workflow.router import Router
from agno.workflow.step import Step
from agno.workflow.steps import Steps
from agno.workflow.types import StepInput, StepOutput

from panelin_v4.engine.classifier import OperatingMode, RequestType

from src.quotation.service import QuotationService


class QuoteWorkflowInput(BaseModel):
    text: str = Field(..., min_length=1)
    mode: str = Field(default="pre_cotizacion")
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    client_location: Optional[str] = None


MODE_MAP: dict[str, OperatingMode] = {
    "informativo": OperatingMode.INFORMATIVO,
    "pre_cotizacion": OperatingMode.PRE_COTIZACION,
    "formal": OperatingMode.FORMAL,
}


def _resolve_mode(raw_mode: Optional[str]) -> Optional[OperatingMode]:
    if raw_mode is None:
        return None
    mode = raw_mode.strip().lower()
    if mode not in MODE_MAP:
        return None
    return MODE_MAP[mode]


def _init_context(step_input: StepInput) -> dict[str, Any]:
    if isinstance(step_input.previous_step_content, dict):
        return step_input.previous_step_content

    payload = step_input.input
    if isinstance(payload, BaseModel):
        payload = payload.model_dump()
    if isinstance(payload, str):
        payload = {"text": payload}
    if not isinstance(payload, dict):
        payload = {"text": str(payload)}

    return {
        "text": payload.get("text", ""),
        "mode": payload.get("mode", "pre_cotizacion"),
        "client_name": payload.get("client_name"),
        "client_phone": payload.get("client_phone"),
        "client_location": payload.get("client_location"),
        "processing_notes": [],
    }


def _build_response_prompt(ctx: dict[str, Any]) -> str:
    quotation = ctx.get("quotation", {})
    sai = ctx.get("sai", {})
    pricing = quotation.get("pricing", {})
    summary = {
        "quote_id": quotation.get("quote_id"),
        "status": quotation.get("status"),
        "mode": quotation.get("mode"),
        "total_usd": pricing.get("subtotal_total_usd"),
        "missing_prices": pricing.get("missing_prices", []),
        "warnings": quotation.get("validation", {}).get("warnings", []),
        "sai_score": sai.get("score"),
    }
    return (
        "Redacta una respuesta comercial-tecnica en espanol para BMC Uruguay.\n"
        "No inventes precios ni productos.\n"
        "Si faltan precios, dilo explicitamente.\n"
        f"Datos estructurados: {summary}"
    )


def _fallback_response_message(ctx: dict[str, Any]) -> str:
    quotation = ctx.get("quotation", {})
    pricing = quotation.get("pricing", {})
    total = pricing.get("subtotal_total_usd", 0.0)
    missing = pricing.get("missing_prices", [])
    status = quotation.get("status", "draft")
    quote_id = quotation.get("quote_id", "N/A")
    if missing:
        missing_block = " | ".join(missing)
        return (
            f"Cotizacion {quote_id} ({status}). Total parcial USD {total}. "
            f"Faltan precios en KB: {missing_block}."
        )
    return f"Cotizacion {quote_id} ({status}) lista. Total USD {total} (IVA incluido)."


def build_panelin_workflow(
    *,
    service: QuotationService,
    response_agent: Optional[Agent] = None,
    workflow_id: str = "panelin-workflow-v4",
    db: Any = None,
) -> Workflow:
    """Construye workflow deterministico Panelin con routing condicional."""

    def classify_step(step_input: StepInput) -> StepOutput:
        ctx = _init_context(step_input)
        classification = service.classify(
            ctx["text"],
            force_mode=_resolve_mode(ctx.get("mode")),
        )
        ctx["_classification"] = classification
        ctx["classification"] = classification.to_dict()
        ctx["mode"] = classification.operating_mode.value
        return StepOutput(content=ctx)

    def parse_step(step_input: StepInput) -> StepOutput:
        ctx = _init_context(step_input)
        request = service.parse(ctx["text"])
        service.inject_client_data(
            request,
            client_name=ctx.get("client_name"),
            client_phone=ctx.get("client_phone"),
            client_location=ctx.get("client_location"),
        )
        ctx["_request"] = request
        ctx["request"] = request.to_dict()
        return StepOutput(content=ctx)

    def defaults_step(step_input: StepInput) -> StepOutput:
        ctx = _init_context(step_input)
        request = ctx.get("_request")
        classification = ctx.get("_classification")
        if request is None or classification is None:
            return StepOutput(content=ctx, success=False, error="Missing parse/classification context")
        assumptions = service.apply_defaults(request, classification.operating_mode)
        ctx["assumptions"] = assumptions
        ctx["request"] = request.to_dict()
        return StepOutput(content=ctx)

    def sre_step(step_input: StepInput) -> StepOutput:
        ctx = _init_context(step_input)
        request = ctx.get("_request")
        if request is None:
            return StepOutput(content=ctx, success=False, error="Missing request context")
        sre = service.sre(request)
        ctx["_sre"] = sre
        ctx["sre"] = sre.to_dict()
        return StepOutput(content=ctx)

    def bom_step(step_input: StepInput) -> StepOutput:
        ctx = _init_context(step_input)
        request = ctx.get("_request")
        if request is None:
            return StepOutput(content=ctx, success=False, error="Missing request context")
        bom = service.bom(request)
        ctx["_bom"] = bom
        ctx["bom"] = bom.to_dict()
        return StepOutput(content=ctx)

    def pricing_step(step_input: StepInput) -> StepOutput:
        ctx = _init_context(step_input)
        request = ctx.get("_request")
        bom = ctx.get("_bom")
        if request is None or bom is None:
            return StepOutput(content=ctx, success=False, error="Missing request/bom context")
        pricing = service.pricing(request, bom)
        ctx["_pricing"] = pricing
        ctx["pricing"] = pricing.to_dict()
        return StepOutput(content=ctx)

    def accessories_short_path_step(step_input: StepInput) -> StepOutput:
        ctx = _init_context(step_input)
        ctx["_bom"] = service.empty_bom()
        ctx["_pricing"] = service.empty_pricing()
        ctx["bom"] = ctx["_bom"].to_dict()
        ctx["pricing"] = ctx["_pricing"].to_dict()
        ctx.setdefault("processing_notes", []).append(
            "Ruta accessories_only: se omite BOM estructural."
        )
        return StepOutput(content=ctx)

    def validation_step(step_input: StepInput) -> StepOutput:
        ctx = _init_context(step_input)
        request = ctx.get("_request")
        sre = ctx.get("_sre")
        bom = ctx.get("_bom", service.empty_bom())
        pricing = ctx.get("_pricing", service.empty_pricing())
        classification = ctx.get("_classification")
        if request is None or sre is None or classification is None:
            return StepOutput(content=ctx, success=False, error="Missing context for validation")

        validation = service.validation(
            request=request,
            sre=sre,
            bom=bom,
            pricing=pricing,
            mode=classification.operating_mode,
        )
        ctx["_validation"] = validation
        output = service.build_output(
            classification=classification,
            request=request,
            sre=sre,
            bom=bom,
            pricing=pricing,
            validation=validation,
            assumptions=ctx.get("assumptions", []),
        )
        ctx["_output"] = output
        ctx["quotation"] = output.to_dict()
        return StepOutput(content=ctx)

    def sai_step(step_input: StepInput) -> StepOutput:
        ctx = _init_context(step_input)
        output = ctx.get("_output")
        if output is None:
            return StepOutput(content=ctx, success=False, error="Missing output context")
        sai = service.sai(output)
        ctx["sai"] = sai.to_dict()
        ctx["response_prompt"] = _build_response_prompt(ctx)
        return StepOutput(content=ctx)

    full_quote_branch = Steps(
        name="full_quote_branch",
        steps=[
            Step(name="bom_step", executor=bom_step),
            Step(name="pricing_step", executor=pricing_step),
        ],
    )

    accessories_only_branch = Steps(
        name="accessories_only_branch",
        steps=[Step(name="accessories_short_path_step", executor=accessories_short_path_step)],
    )

    def route_bom_and_pricing(step_input: StepInput):
        ctx = _init_context(step_input)
        classification = ctx.get("_classification")
        if classification and classification.request_type == RequestType.ACCESSORIES_ONLY:
            return [accessories_only_branch]
        return [full_quote_branch]

    if response_agent is None:
        response_step = Step(
            name="response_step",
            executor=lambda si: StepOutput(content=_fallback_response_message(_init_context(si))),
        )
    else:
        response_step = Step(name="response_step", agent=response_agent)

    def finalize_step(step_input: StepInput) -> StepOutput:
        message = step_input.previous_step_content
        previous = step_input.previous_step_outputs or {}
        sai_output = previous.get("sai_step")
        ctx = sai_output.content if sai_output else {}
        if not isinstance(ctx, dict):
            ctx = {}
        if not isinstance(message, str):
            message = _fallback_response_message(ctx)
        return StepOutput(
            content={
                "message": message,
                "quotation": ctx.get("quotation", {}),
                "sai": ctx.get("sai", {}),
                "response_prompt": ctx.get("response_prompt", ""),
            }
        )

    workflow = Workflow(
        id=workflow_id,
        name="Panelin Deterministic Workflow",
        description=(
            "Pipeline explicito de cotizacion (classify->parse->defaults->sre->"
            "router(bom/pricing)->validate->sai->response)"
        ),
        db=db,
        input_schema=QuoteWorkflowInput,
        steps=[
            Step(name="classify_step", executor=classify_step),
            Step(name="parse_step", executor=parse_step),
            Step(name="defaults_step", executor=defaults_step),
            Step(name="sre_step", executor=sre_step),
            Router(
                name="route_bom_pricing",
                choices=[full_quote_branch, accessories_only_branch],
                selector=route_bom_and_pricing,
            ),
            Step(name="validation_step", executor=validation_step),
            Step(name="sai_step", executor=sai_step),
            response_step,
            Step(name="finalize_step", executor=finalize_step),
        ],
    )
    return workflow
