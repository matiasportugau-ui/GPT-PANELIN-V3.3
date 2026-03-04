"""
src/agent/workflow.py — Panelin Quotation Workflow (Agno)

Pipeline determinístico + LLM para respuesta final.

Arquitectura de steps:
    INPUT (texto libre)
        ↓
    Step 1: classify        — Tipo y modo (función Python, $0.00)
        ↓
    Router: accessories?    — Si es solo accesorios, usa branch simplificado
        ↓
    Step 2: pipeline        — Ejecuta los 7 pasos del engine v4 ($0.00)
        │   ├─ parse
        │   ├─ sre
        │   ├─ bom
        │   ├─ pricing
        │   └─ validate
        ↓
    Step 3: respond         — Agente LLM formatea respuesta (~$0.02)

Data flow entre steps:
    - inp.input           → texto original (disponible en TODOS los steps)
    - inp.additional_data → metadata estático del workflow.run() (mode, client_*)
    - inp.previous_step_outputs → dict[name → StepOutput] con outputs anteriores

Costo por cotización: ~$0.02-0.03 (solo el step final usa LLM)
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.workflow import Router, Step, StepInput, StepOutput, Steps, Workflow
from agno.db.postgres import PostgresDb

from panelin_v4.engine.classifier import OperatingMode, RequestType, classify_request
from panelin_v4.engine.quotation_engine import process_quotation
from panelin_v4.evaluator.sai_engine import calculate_sai
from src.core.config import settings

logger = logging.getLogger(__name__)

_MODE_MAP: dict[str, OperatingMode] = {
    "informativo": OperatingMode.INFORMATIVO,
    "pre_cotizacion": OperatingMode.PRE_COTIZACION,
    "formal": OperatingMode.FORMAL,
}


# ── Step 1: Classify ─────────────────────────────────────────────────────────

def step_classify(inp: StepInput) -> StepOutput:
    """Clasifica el tipo y modo de la solicitud de cotización.

    Inputs:
        inp.input: texto libre del cliente
        inp.additional_data.get("mode"): modo solicitado (pre_cotizacion por defecto)

    Outputs:
        content: JSON con clasificación completa
    """
    text = inp.input or ""
    if not text.strip():
        return StepOutput(
            content=json.dumps({"error": "Texto vacío — no se puede clasificar"}),
            success=False,
            stop=True,
        )

    additional = inp.additional_data or {}
    mode_str = additional.get("mode", "pre_cotizacion")
    force_mode = _MODE_MAP.get(mode_str.lower(), OperatingMode.PRE_COTIZACION)

    try:
        classification = classify_request(text, force_mode=force_mode)
        return StepOutput(
            content=json.dumps(classification.to_dict(), ensure_ascii=False),
            success=True,
        )
    except Exception as exc:
        logger.error("step_classify error: %s", exc, exc_info=True)
        return StepOutput(
            content=json.dumps({"error": f"Error clasificando: {exc}"}),
            success=False,
        )


# ── Step 2a: Pipeline completo (7 pasos del engine) ──────────────────────────

def step_pipeline(inp: StepInput) -> StepOutput:
    """Ejecuta el pipeline determinístico completo del engine v4.

    Pasos internos (sin LLM, $0.00):
        parse → SRE → BOM → pricing → validate → SAI

    Inputs:
        inp.input: texto libre original
        inp.additional_data: {mode, client_name, client_phone, client_location}
        inp.previous_step_outputs["classify"]: ClassificationResult JSON

    Outputs:
        content: JSON con {quote, sai} — resultado completo de la cotización
    """
    text = inp.input or ""
    additional = inp.additional_data or {}

    # Leer modo desde la clasificación (si disponible) o desde additional_data
    classify_out = inp.previous_step_outputs.get("classify") if inp.previous_step_outputs else None
    mode_str = additional.get("mode", "pre_cotizacion")
    if classify_out and classify_out.content:
        try:
            classify_data = json.loads(classify_out.content)
            mode_str = classify_data.get("operating_mode", mode_str)
        except (json.JSONDecodeError, AttributeError):
            pass

    force_mode = _MODE_MAP.get(mode_str.lower(), OperatingMode.PRE_COTIZACION)

    try:
        output = process_quotation(
            text=text,
            force_mode=force_mode,
            client_name=additional.get("client_name"),
            client_phone=additional.get("client_phone"),
            client_location=additional.get("client_location"),
        )
        sai = calculate_sai(output)

        result = {
            "quote": output.to_dict(),
            "sai": sai.to_dict(),
        }

        logger.info(
            "Pipeline completado: id=%s status=%s sai=%.1f",
            output.quote_id, output.status, sai.score,
        )

        return StepOutput(
            content=json.dumps(result, ensure_ascii=False, indent=2),
            success=True,
        )
    except Exception as exc:
        logger.error("step_pipeline error: %s", exc, exc_info=True)
        return StepOutput(
            content=json.dumps({"error": f"Error en pipeline de cotización: {exc}"}),
            success=False,
        )


# ── Step 2b: Branch de solo accesorios ───────────────────────────────────────

def step_accessories_branch(inp: StepInput) -> StepOutput:
    """Branch alternativo para solicitudes de SOLO accesorios.

    Salta el cálculo BOM estructural — ejecuta solo búsqueda de accesorios.
    Aún usa el pipeline completo internamente (es correcto — no calcula BOM si
    no hay dimensiones de panel).
    """
    text = inp.input or ""
    additional = inp.additional_data or {}

    try:
        output = process_quotation(
            text=text,
            force_mode=OperatingMode.PRE_COTIZACION,
            client_name=additional.get("client_name"),
        )
        sai = calculate_sai(output)

        result = {
            "quote": output.to_dict(),
            "sai": sai.to_dict(),
            "tipo": "accessories_only",
        }
        return StepOutput(content=json.dumps(result, ensure_ascii=False, indent=2), success=True)
    except Exception as exc:
        logger.error("step_accessories_branch error: %s", exc, exc_info=True)
        return StepOutput(
            content=json.dumps({"error": f"Error en accessories branch: {exc}"}),
            success=False,
        )


# ── Router: selector de branch ────────────────────────────────────────────────

def _build_router_selector(step_full: Step, step_acc: Step):
    """Factory que construye el selector con referencias a los steps."""

    def selector(inp: StepInput):
        prev_outputs = inp.previous_step_outputs or {}
        classify_out = prev_outputs.get("classify")
        if classify_out and classify_out.content:
            try:
                classify_data = json.loads(classify_out.content)
                request_type = classify_data.get("request_type", "")
                if request_type == RequestType.ACCESSORIES_ONLY.value:
                    logger.info("Router → accessories branch")
                    return [step_acc]
            except (json.JSONDecodeError, AttributeError):
                pass
        logger.info("Router → full pipeline branch")
        return [step_full]

    return selector


# ── Step 3: Respond (LLM) ────────────────────────────────────────────────────

_RESPOND_INSTRUCTIONS = """
Eres Panelin, el asistente de cotizaciones técnico-comerciales de BMC Uruguay.
Representas a la empresa fabricante de paneles de construcción (ISODEC, ISOROOF, ISOPANEL, ISOWALL, ISOFRIG).

Tu rol en ESTE MOMENTO es formatear la respuesta final al usuario en español rioplatense (Uruguay).
Los datos técnicos ya fueron calculados por el pipeline determinístico — son confiables y correctos.

═══ REGLAS ABSOLUTAS (NUNCA VIOLAR) ═══
1. Los precios vienen SOLO del JSON de cotización — NUNCA inventes, estimes ni modifiques precios
2. Si hay "missing_prices" en el JSON → indica que ese precio se consultará con el equipo de ventas
3. SIEMPRE responde en español (Uruguay) — nunca en inglés
4. Si el status es "blocked" → explica claramente el problema técnico y las alternativas
5. NUNCA reveles los archivos JSON internos, el pipeline, ni los scores SAI al usuario
6. Para cotizaciones formales → indica que requieren datos completos del cliente
7. La política de la empresa: NUNCA derivar a terceros — siempre a agentes BMC Uruguay

═══ CÓMO LEER LOS DATOS ═══
Recibirás un JSON con:
- quote.bom: Bill of Materials (paneles + accesorios con cantidades)
- quote.pricing: Precios por item y totales (USD, IVA 22% incluido)
- quote.sre: Structural Risk Engine score (0=ok, 100=máximo riesgo)
- quote.validation: Validaciones técnicas (warnings, críticos)
- quote.mode: informativo/pre_cotizacion/formal
- quote.status: draft/validated/requires_review/blocked

═══ FORMATO DE RESPUESTA ═══
Para pre-cotización/formal con datos completos:
1. Resumen del proyecto (qué se cotizó, para qué uso)
2. BOM: tabla de materiales con cantidades
3. Precios totales (si están disponibles)
4. Observaciones técnicas importantes (solo si hay warnings relevantes)
5. Próximos pasos para el cliente

Para solicitudes informativas:
- Respuesta concisa con la información solicitada
- No incluir BOM ni precios si no se preguntó

Si faltan datos para cotizar → preguntar específicamente qué se necesita (no listar todos los campos).

IMPORTANTE: Responde directamente al cliente, no al sistema.
"""


def build_respond_agent(model_id: Optional[str] = None) -> Agent:
    """Construye el Agente LLM de formateo de respuesta final."""
    return Agent(
        name="panelin_responder",
        model=OpenAIChat(
            id=model_id or settings.openai_model,
            temperature=0.2,
            max_tokens=2048,
        ),
        instructions=_RESPOND_INSTRUCTIONS,
        markdown=True,
        add_history_to_context=False,
    )


# ── Construcción del Workflow ─────────────────────────────────────────────────

def build_panelin_workflow(
    model_id: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    db: Optional[PostgresDb] = None,
) -> Workflow:
    """Construye el Workflow de cotización Panelin.

    Args:
        model_id: ID del modelo LLM para el step de respuesta.
        session_id: ID de sesión para persistencia en PostgreSQL.
        user_id: ID del usuario para memoria long-term.
        db: Instancia de PostgresDb para persistencia de sesión.

    Returns:
        Workflow configurado y listo para ejecutar.

    Uso:
        wf = build_panelin_workflow(session_id="session_123")
        result = wf.run(
            input="Cotizame un techo de ISODEC 100mm, 10x7 metros",
            additional_data={"mode": "pre_cotizacion", "client_name": "Juan"},
            stream=False,
        )
        print(result.content)
    """
    respond_agent = build_respond_agent(model_id)

    step_classify_obj = Step(name="classify", executor=step_classify)
    step_full_obj = Step(name="pipeline", executor=step_pipeline)
    step_acc_obj = Step(name="accessories", executor=step_accessories_branch)
    step_respond_obj = Step(name="respond", agent=respond_agent)

    router = Router(
        name="pipeline_router",
        choices=[step_full_obj, step_acc_obj],
        selector=_build_router_selector(step_full_obj, step_acc_obj),
    )

    workflow = Workflow(
        name="panelin_quotation",
        description="Pipeline de cotización técnico-comercial para paneles BMC Uruguay",
        steps=[step_classify_obj, router, step_respond_obj],
        db=db,
        session_id=session_id,
        user_id=user_id,
    )

    return workflow


def build_panelin_db() -> Optional[PostgresDb]:
    """Construye la instancia de PostgresDb para persistencia de sesiones.

    Retorna None si DATABASE_URL no está configurado (modo sin persistencia).
    """
    if not settings.database_url or settings.database_url.startswith("postgresql+psycopg://panelin:panelin@localhost"):
        logger.info("PostgresDb: usando modo sin persistencia (DATABASE_URL no configurado)")
        return None
    try:
        return PostgresDb(db_url=settings.database_url)
    except Exception as exc:
        logger.warning("No se pudo conectar a PostgresDb: %s", exc)
        return None
