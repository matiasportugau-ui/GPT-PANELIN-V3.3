"""Agno workflow implementing the deterministic Panelin quotation pipeline."""

from __future__ import annotations

from typing import Any
import logging

from pydantic import BaseModel, Field

from agno.agent import Agent
from agno.workflow import Workflow
from agno.workflow.step import Step, StepInput, StepOutput
from agno.workflow.router import Router

from panelin_v4.engine.classifier import RequestType
from panelin_v4.evaluator.sai_engine import calculate_sai

from src.agent.models import build_chat_model
from src.core.config import AppSettings, get_settings
from src.quotation.service import QuotationService

logger = logging.getLogger(__name__)


class PanelinWorkflowInput(BaseModel):
    text: str = Field(..., min_length=1)
    mode: str = "pre_cotizacion"
    client_name: str | None = None
    client_phone: str | None = None
    client_location: str | None = None


def _ensure_session_data(step_input: StepInput) -> dict[str, Any]:
    if not step_input.workflow_session:
        return {}
    if step_input.workflow_session.session_data is None:
        step_input.workflow_session.session_data = {}
    return step_input.workflow_session.session_data


def _read_input_payload(step_input: StepInput) -> PanelinWorkflowInput:
    raw_input = step_input.input
    if isinstance(raw_input, PanelinWorkflowInput):
        return raw_input
    if isinstance(raw_input, dict):
        return PanelinWorkflowInput.model_validate(raw_input)
    return PanelinWorkflowInput(text=str(raw_input or ""))


def _copy_context(step_input: StepInput) -> dict[str, Any]:
    previous_content = step_input.previous_step_content
    if isinstance(previous_content, dict):
        return dict(previous_content)
    return {}


def _build_response_agent(settings: AppSettings) -> Agent:
    return Agent(
        name="panelin-response-formatter",
        model=build_chat_model(settings),
        markdown=True,
        add_history_to_context=False,
        search_knowledge=False,
        instructions=[
            "Responde SIEMPRE en español para clientes de BMC Uruguay.",
            "No inventes precios ni SKUs: usa únicamente los datos del JSON que recibes como entrada.",
            "Redacta una respuesta comercial clara y breve (máximo 10 líneas).",
            "Incluye: estado de la cotización, total estimado y advertencias críticas si existen.",
            "Si faltan datos, solicita explícitamente los campos faltantes.",
        ],
    )


def build_panelin_workflow(
    settings: AppSettings | None = None,
    service: QuotationService | None = None,
) -> Workflow:
    """Create the deterministic 7-step quotation workflow + optional LLM response step."""
    cfg = settings or get_settings()
    quotation_service = service or QuotationService()

    def classify_step_executor(step_input: StepInput) -> StepOutput:
        payload = _read_input_payload(step_input)
        classification = quotation_service.classify(payload.text, payload.mode)
        resolved_mode = quotation_service.resolve_mode(payload.mode)
        context = {
            "text": payload.text,
            "mode": resolved_mode,
            "classification": classification,
            "client_name": payload.client_name,
            "client_phone": payload.client_phone,
            "client_location": payload.client_location,
        }
        session_data = _ensure_session_data(step_input)
        if session_data is not None:
            session_data["last_request_text"] = payload.text
            session_data["last_request_mode"] = resolved_mode.value
            session_data["last_request_type"] = classification.request_type.value
        return StepOutput(content=context)

    def parse_step_executor(step_input: StepInput) -> StepOutput:
        context = _copy_context(step_input)
        request = quotation_service.parse(context["text"])
        quotation_service.inject_client_data(
            request,
            client_name=context.get("client_name"),
            client_phone=context.get("client_phone"),
            client_location=context.get("client_location"),
        )
        assumptions = quotation_service.apply_defaults(request, context["mode"])
        context["request"] = request
        context["assumptions"] = assumptions
        return StepOutput(content=context)

    def sre_step_executor(step_input: StepInput) -> StepOutput:
        context = _copy_context(step_input)
        context["sre"] = quotation_service.calculate_sre(context["request"])
        return StepOutput(content=context)

    def bom_step_executor(step_input: StepInput) -> StepOutput:
        context = _copy_context(step_input)
        context["bom"] = quotation_service.calculate_bom(context["request"])
        context["bom_route"] = "calculated"
        return StepOutput(content=context)

    def skip_bom_step_executor(step_input: StepInput) -> StepOutput:
        context = _copy_context(step_input)
        context["bom"] = quotation_service.empty_bom(
            "BOM omitido por solicitud informativa/accesorios."
        )
        context["bom_route"] = "skipped"
        return StepOutput(content=context)

    bom_step = Step(name="bom", executor=bom_step_executor)
    skip_bom_step = Step(name="skip_bom", executor=skip_bom_step_executor)

    def bom_router_selector(step_input: StepInput):
        context = _copy_context(step_input)
        classification = context.get("classification")
        request = context.get("request")
        if classification and classification.request_type in {
            RequestType.ACCESSORIES_ONLY,
            RequestType.INFO_ONLY,
            RequestType.POST_SALE,
        }:
            return [skip_bom_step]
        if request and (not request.familia or not request.thickness_mm or not request.uso):
            return [skip_bom_step]
        return [bom_step]

    def pricing_step_executor(step_input: StepInput) -> StepOutput:
        context = _copy_context(step_input)
        context["pricing"] = quotation_service.calculate_pricing(context["request"], context["bom"])
        return StepOutput(content=context)

    def validation_step_executor(step_input: StepInput) -> StepOutput:
        context = _copy_context(step_input)
        context["validation"] = quotation_service.validate(
            request=context["request"],
            sre=context["sre"],
            bom=context["bom"],
            pricing=context["pricing"],
            mode=context["mode"],
        )
        return StepOutput(content=context)

    def sai_step_executor(step_input: StepInput) -> StepOutput:
        context = _copy_context(step_input)
        output = quotation_service.build_output(
            classification=context["classification"],
            request=context["request"],
            sre=context["sre"],
            bom=context["bom"],
            pricing=context["pricing"],
            validation=context["validation"],
            mode=context["mode"],
        )
        sai = calculate_sai(output)
        payload = quotation_service.response_payload(output, sai)
        payload["bom_route"] = context.get("bom_route", "calculated")
        payload["classification"] = context["classification"].to_dict()

        session_data = _ensure_session_data(step_input)
        if session_data is not None:
            session_data["last_quote_id"] = output.quote_id
            session_data["last_quote_status"] = output.status
            session_data["last_quote_mode"] = output.mode

        return StepOutput(content=payload)

    def deterministic_response_step_executor(step_input: StepInput) -> StepOutput:
        payload = _copy_context(step_input)
        quotation = payload.get("quotation", {})
        pricing = quotation.get("pricing", {})
        sai = payload.get("sai", {})
        total = pricing.get("subtotal_total_usd", 0.0)
        payload["assistant_response"] = (
            f"Cotización {quotation.get('quote_id', 'N/A')} en modo {quotation.get('mode', 'pre_cotizacion')}. "
            f"Estado: {quotation.get('status', 'draft')}. "
            f"Total estimado USD {total:.2f}. "
            f"SAI: {sai.get('score', 0)}/100."
        )
        return StepOutput(content=payload)

    def finalize_llm_step_executor(step_input: StepInput) -> StepOutput:
        previous_outputs = step_input.previous_step_outputs or {}
        sai_output = previous_outputs.get("sai")
        payload: dict[str, Any] = {}
        if sai_output is not None and isinstance(sai_output.content, dict):
            payload = dict(sai_output.content)
        payload["assistant_response"] = str(step_input.previous_step_content or "").strip()
        return StepOutput(content=payload)

    classify_step = Step(name="classify", executor=classify_step_executor)
    parse_step = Step(name="parse", executor=parse_step_executor)
    sre_step = Step(name="sre", executor=sre_step_executor)
    bom_router = Router(
        name="bom_router",
        choices=[bom_step, skip_bom_step],
        selector=bom_router_selector,
    )
    pricing_step = Step(name="pricing", executor=pricing_step_executor)
    validation_step = Step(name="validate", executor=validation_step_executor)
    sai_step = Step(name="sai", executor=sai_step_executor)

    steps: list[Any] = [
        classify_step,
        parse_step,
        sre_step,
        bom_router,
        pricing_step,
        validation_step,
        sai_step,
    ]

    if cfg.use_llm_response_step:
        logger.info("Panelin workflow: enabling LLM response step")
        llm_response_agent = _build_response_agent(cfg)
        steps.append(Step(name="respond_llm", agent=llm_response_agent))
        steps.append(Step(name="finalize", executor=finalize_llm_step_executor))
    else:
        logger.warning(
            "Panelin workflow: using deterministic response step because model credentials are missing "
            "or enable_llm_response_step=false."
        )
        steps.append(Step(name="respond", executor=deterministic_response_step_executor))

    return Workflow(
        id=cfg.panelin_workflow_id,
        name="Panelin Deterministic Workflow",
        description=(
            "Pipeline explícito classify→parse→SRE→BOM→pricing→validate→SAI "
            "con routing condicional y respuesta final."
        ),
        db=cfg.build_postgres_db(),
        input_schema=PanelinWorkflowInput,
        steps=steps,
    )


def run_workflow_sync(
    workflow: Workflow,
    text: str,
    mode: str = "pre_cotizacion",
    session_id: str | None = None,
    user_id: str | None = None,
    client_name: str | None = None,
    client_phone: str | None = None,
    client_location: str | None = None,
) -> dict[str, Any]:
    """Synchronous helper for API/tool integrations."""
    result = workflow.run(
        input={
            "text": text,
            "mode": mode,
            "client_name": client_name,
            "client_phone": client_phone,
            "client_location": client_location,
        },
        session_id=session_id,
        user_id=user_id,
    )
    if hasattr(result, "content") and isinstance(result.content, dict):
        return result.content
    if hasattr(result, "content"):
        return {"assistant_response": str(result.content)}
    return {"assistant_response": str(result)}
