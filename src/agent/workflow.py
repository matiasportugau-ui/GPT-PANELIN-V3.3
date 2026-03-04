"""
Panelin v5.0 - Agno Quotation Workflow
========================================

Deterministic 7-step pipeline implemented as an Agno Workflow.
Each step uses a Python function executor (NO LLM) except the final
"respond" step which uses an Agent to format the response in Spanish.

Pipeline:
    1. understand  — (Agent/LLM) Interpret user intent from conversational text
    2. classify    — (function) Classify request type + operating mode
    3. parse       — (function) Free-text → structured QuoteRequest
    4. sre         — (function) Structural Risk Engine score
    5. bom         — (function) Bill of Materials calculation
    6. pricing     — (function) Price lookup from KB
    7. validate    — (function) Multi-layer validation
    8. respond     — (Agent/LLM) Format quotation response in Spanish

Cost: Steps 2-7 = $0.00 (pure Python). Steps 1+8 ≈ $0.02-0.03 (LLM).
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.workflow.workflow import Workflow
from agno.workflow.step import Step, StepInput, StepOutput

from panelin_v4.engine.classifier import OperatingMode, classify_request, RequestType
from panelin_v4.engine.parser import parse_request
from panelin_v4.engine.sre_engine import calculate_sre
from panelin_v4.engine.bom_engine import BOMResult, calculate_bom
from panelin_v4.engine.pricing_engine import PricingResult, calculate_pricing
from panelin_v4.engine.validation_engine import validate_quotation
from panelin_v4.engine.quotation_engine import _apply_defaults, QuotationOutput
from panelin_v4.evaluator.sai_engine import calculate_sai

from src.quotation.service import QuotationService

logger = logging.getLogger(__name__)


UNDERSTAND_INSTRUCTIONS = [
    "Eres Panelin, asistente técnico-comercial de BMC Uruguay para paneles de construcción.",
    "Tu trabajo es extraer del mensaje del usuario la información necesaria para cotizar.",
    "Responde EXCLUSIVAMENTE con un JSON válido (sin markdown, sin texto adicional).",
    "El JSON debe tener esta estructura:",
    '{"texto_cotizacion": "...", "modo": "pre_cotizacion|formal|informativo",',
    ' "nombre_cliente": "...", "telefono_cliente": "...", "ubicacion_cliente": "...",',
    ' "es_consulta_info": false, "consulta_info": ""}',
    "",
    "Si el usuario pide información general (no cotización), usa es_consulta_info=true.",
    "Si no se menciona modo, usa pre_cotizacion por defecto.",
    "Extrae datos del cliente si se mencionan.",
    "El texto_cotizacion debe preservar los datos técnicos tal cual los escribió el usuario.",
]

RESPOND_INSTRUCTIONS = [
    "Eres Panelin, asistente técnico-comercial de BMC Uruguay.",
    "Formatea la cotización de forma clara y profesional en ESPAÑOL.",
    "REGLAS CRÍTICAS:",
    "- NUNCA inventes precios. Si falta un precio, decí 'precio pendiente de confirmación'.",
    "- Los precios del KB ya incluyen IVA 22%. NUNCA sumes IVA adicional.",
    "- Siempre incluí el quote_id para referencia.",
    "- Si hay warnings de validación, mencionálos como notas.",
    "- Si el SRE detecta riesgo alto, recomendá consultar con ingeniería.",
    "- Usá formato con emojis y secciones claras para WhatsApp/chat.",
    "- Siempre cerrá con: '¿Necesitás algún ajuste o tenés otra consulta?'",
    "",
    "FORMATO SUGERIDO:",
    "📋 Cotización [quote_id]",
    "📦 Producto: [familia] [sub_familia] [espesor]mm",
    "📐 Área: [area] m² | Paneles: [count]",
    "💰 Paneles: USD [precio]",
    "🔩 Accesorios: USD [precio]",
    "💵 TOTAL: USD [total] (IVA incluido)",
    "⚠️ Notas: [si aplica]",
]


def _step_classify(step_input: StepInput) -> StepOutput:
    """Step 2: Classify request type and operating mode."""
    try:
        data = json.loads(step_input.previous_step_content or step_input.input)
    except (json.JSONDecodeError, TypeError):
        data = {"texto_cotizacion": step_input.input, "modo": "pre_cotizacion"}

    if data.get("es_consulta_info"):
        return StepOutput(content=json.dumps({
            "tipo": "info_query",
            "consulta": data.get("consulta_info", data.get("texto_cotizacion", "")),
            "skip_pipeline": True,
        }, ensure_ascii=False))

    text = data.get("texto_cotizacion", step_input.input)
    mode_str = data.get("modo", "pre_cotizacion")
    mode_map = {
        "informativo": OperatingMode.INFORMATIVO,
        "pre_cotizacion": OperatingMode.PRE_COTIZACION,
        "formal": OperatingMode.FORMAL,
    }
    force_mode = mode_map.get(mode_str)

    classification = classify_request(text, force_mode=force_mode)

    result = {
        "classification": classification.to_dict(),
        "texto_cotizacion": text,
        "modo": classification.operating_mode.value,
        "nombre_cliente": data.get("nombre_cliente"),
        "telefono_cliente": data.get("telefono_cliente"),
        "ubicacion_cliente": data.get("ubicacion_cliente"),
        "skip_pipeline": False,
    }
    return StepOutput(content=json.dumps(result, ensure_ascii=False))


def _step_parse(step_input: StepInput) -> StepOutput:
    """Step 3: Parse free-text into structured QuoteRequest."""
    data = json.loads(step_input.previous_step_content)
    if data.get("skip_pipeline"):
        return StepOutput(content=step_input.previous_step_content)

    text = data["texto_cotizacion"]
    request = parse_request(text)

    if data.get("nombre_cliente"):
        request.client.name = data["nombre_cliente"]
    if data.get("telefono_cliente"):
        request.client.phone = data["telefono_cliente"]
    if data.get("ubicacion_cliente"):
        request.client.location = data["ubicacion_cliente"]

    mode_map = {
        "informativo": OperatingMode.INFORMATIVO,
        "pre_cotizacion": OperatingMode.PRE_COTIZACION,
        "formal": OperatingMode.FORMAL,
    }
    mode = mode_map.get(data["modo"], OperatingMode.PRE_COTIZACION)
    assumptions = _apply_defaults(request, mode)
    request.assumptions_used.extend(assumptions)

    data["request"] = request.to_dict()
    data["assumptions"] = request.assumptions_used
    return StepOutput(content=json.dumps(data, ensure_ascii=False))


def _step_sre(step_input: StepInput) -> StepOutput:
    """Step 4: Calculate Structural Risk Engine score."""
    data = json.loads(step_input.previous_step_content)
    if data.get("skip_pipeline"):
        return StepOutput(content=step_input.previous_step_content)

    from src.quotation.service import _rebuild_quote_request
    req = _rebuild_quote_request(data["request"])
    sre = calculate_sre(req)

    data["sre"] = sre.to_dict()
    return StepOutput(content=json.dumps(data, ensure_ascii=False))


def _step_bom(step_input: StepInput) -> StepOutput:
    """Step 5: Calculate Bill of Materials.

    Skips if: accessories_only request OR insufficient data.
    """
    data = json.loads(step_input.previous_step_content)
    if data.get("skip_pipeline"):
        return StepOutput(content=step_input.previous_step_content)

    req = data["request"]
    classification = data.get("classification", {})

    if classification.get("request_type") == "accessories_only":
        data["bom"] = BOMResult(
            system_key="accessories_only", area_m2=0, panel_count=0,
            supports_per_panel=0, fixation_points=0,
        ).to_dict()
        data["bom_skipped"] = True
        return StepOutput(content=json.dumps(data, ensure_ascii=False))

    can_bom = (
        req.get("familia")
        and req.get("thickness_mm")
        and req.get("uso")
        and (req.get("geometry", {}).get("length_m") or req.get("geometry", {}).get("panel_lengths"))
    )

    if not can_bom:
        data["bom"] = BOMResult(
            system_key="unknown", area_m2=0, panel_count=0,
            supports_per_panel=0, fixation_points=0,
        ).to_dict()
        data["bom_skipped"] = True
        return StepOutput(content=json.dumps(data, ensure_ascii=False))

    geo = req.get("geometry", {})
    length_m = geo.get("length_m") or 0
    width_m = geo.get("width_m") or 0
    if not width_m and geo.get("panel_count"):
        width_m = geo["panel_count"] * 1.12

    if length_m > 0 and width_m > 0:
        bom = calculate_bom(
            familia=req["familia"],
            sub_familia=req.get("sub_familia") or "EPS",
            thickness_mm=req["thickness_mm"],
            uso=req["uso"],
            length_m=length_m,
            width_m=width_m,
            structure_type=req.get("structure_type") or "metal",
            panel_count=geo.get("panel_count"),
            panel_lengths=geo.get("panel_lengths") or None,
            roof_type=req.get("roof_type"),
            span_m=req.get("span_m"),
        )
        data["bom"] = bom.to_dict()
    else:
        data["bom"] = BOMResult(
            system_key="unknown", area_m2=0, panel_count=0,
            supports_per_panel=0, fixation_points=0,
        ).to_dict()
        data["bom_skipped"] = True

    return StepOutput(content=json.dumps(data, ensure_ascii=False))


def _step_pricing(step_input: StepInput) -> StepOutput:
    """Step 6: Calculate pricing from KB. Never invents prices."""
    data = json.loads(step_input.previous_step_content)
    if data.get("skip_pipeline"):
        return StepOutput(content=step_input.previous_step_content)

    req = data["request"]
    bom_dict = data.get("bom", {})

    if bom_dict.get("panel_count", 0) > 0 and req.get("familia") and req.get("thickness_mm"):
        from src.quotation.service import _rebuild_bom_result
        bom = _rebuild_bom_result(bom_dict)
        pricing = calculate_pricing(
            bom=bom,
            familia=req["familia"],
            sub_familia=req.get("sub_familia") or "EPS",
            thickness_mm=req["thickness_mm"],
            panel_area_m2=bom_dict.get("area_m2"),
            iva_mode=req.get("iva_mode", "incluido"),
        )
        data["pricing"] = pricing.to_dict()
    else:
        data["pricing"] = PricingResult().to_dict()

    return StepOutput(content=json.dumps(data, ensure_ascii=False))


def _step_validate(step_input: StepInput) -> StepOutput:
    """Step 7: Multi-layer validation."""
    data = json.loads(step_input.previous_step_content)
    if data.get("skip_pipeline"):
        return StepOutput(content=step_input.previous_step_content)

    from src.quotation.service import (
        _rebuild_quote_request,
        _rebuild_sre_result,
        _rebuild_bom_result,
        _rebuild_pricing_result,
    )

    req = _rebuild_quote_request(data["request"])
    sre = _rebuild_sre_result(data.get("sre", {}))
    bom = _rebuild_bom_result(data.get("bom", {}))
    pricing = _rebuild_pricing_result(data.get("pricing", {}))

    mode_map = {
        "informativo": OperatingMode.INFORMATIVO,
        "pre_cotizacion": OperatingMode.PRE_COTIZACION,
        "formal": OperatingMode.FORMAL,
    }
    mode = mode_map.get(data.get("modo", ""), OperatingMode.PRE_COTIZACION)

    validation = validate_quotation(
        request=req, sre=sre, bom=bom, pricing=pricing, mode=mode,
    )

    import uuid
    from datetime import datetime
    from panelin_v4.engine.quotation_engine import _calculate_confidence, _determine_status

    confidence = _calculate_confidence(req, sre, validation, pricing)
    status = _determine_status(mode, sre, validation)
    quote_id = f"PV5-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    output = QuotationOutput(
        quote_id=quote_id,
        timestamp=datetime.now().isoformat(),
        mode=data.get("modo", "pre_cotizacion"),
        level=sre.level.value,
        status=status,
        classification=data.get("classification", {}),
        request=data.get("request", {}),
        sre=data.get("sre", {}),
        bom=data.get("bom", {}),
        pricing=data.get("pricing", {}),
        validation=validation.to_dict(),
        assumptions_used=data.get("assumptions", []),
        confidence_score=round(confidence, 1),
        processing_notes=[],
    )

    sai = calculate_sai(output)

    data["validation"] = validation.to_dict()
    data["quote_id"] = quote_id
    data["status"] = status
    data["confidence"] = round(confidence, 1)
    data["sai"] = sai.to_dict()
    data["quotation_output"] = output.to_dict()

    return StepOutput(content=json.dumps(data, ensure_ascii=False))


def create_understand_agent(model_id: str = "gpt-4o") -> Agent:
    """Create the LLM agent for step 1 (understand user intent)."""
    return Agent(
        name="PanelinUnderstand",
        model=OpenAIChat(id=model_id, temperature=0.1),
        instructions=UNDERSTAND_INSTRUCTIONS,
        markdown=False,
        show_tool_calls=False,
    )


def create_respond_agent(model_id: str = "gpt-4o") -> Agent:
    """Create the LLM agent for step 8 (format response)."""
    return Agent(
        name="PanelinRespond",
        model=OpenAIChat(id=model_id, temperature=0.5),
        instructions=RESPOND_INSTRUCTIONS,
        markdown=True,
        show_tool_calls=False,
    )


def create_quotation_workflow(
    model_id: str = "gpt-4o",
    storage=None,
    session_id: Optional[str] = None,
) -> Workflow:
    """Create the complete Panelin quotation workflow.

    7 deterministic steps + 1 LLM response step.
    Total LLM cost per quotation: ~$0.02-0.03.
    """
    understand_agent = create_understand_agent(model_id)
    respond_agent = create_respond_agent(model_id)

    workflow = Workflow(
        name="PanelinQuotationPipeline",
        steps=[
            Step(name="Understand", agent=understand_agent),
            Step(name="Classify", executor=_step_classify),
            Step(name="Parse", executor=_step_parse),
            Step(name="SRE", executor=_step_sre),
            Step(name="BOM", executor=_step_bom),
            Step(name="Pricing", executor=_step_pricing),
            Step(name="Validate", executor=_step_validate),
            Step(name="Respond", agent=respond_agent),
        ],
        storage=storage,
        session_id=session_id,
    )
    return workflow
