from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from agno.os import AgentOS
from agno.os.config import AuthorizationConfig

from panelin_v4.engine.classifier import OperatingMode
from src.agent.panelin import build_panelin_runtime
from src.core.config import get_settings
from src.quotation.service import QuotationService
from wolf_api.main import app as wolf_app


class PanelinEngineInput(BaseModel):
    text: str = Field(..., min_length=1)
    mode: str = Field(default="pre_cotizacion")
    client_name: str | None = None
    client_phone: str | None = None
    client_location: str | None = None


MODE_MAP: dict[str, OperatingMode] = {
    "informativo": OperatingMode.INFORMATIVO,
    "pre_cotizacion": OperatingMode.PRE_COTIZACION,
    "formal": OperatingMode.FORMAL,
}


def _resolve_mode(raw_mode: str | None) -> OperatingMode:
    mode_key = (raw_mode or "pre_cotizacion").strip().lower()
    if mode_key not in MODE_MAP:
        valid_modes = ", ".join(sorted(MODE_MAP.keys()))
        raise ValueError(f"Invalid mode '{raw_mode}'. Valid options: {valid_modes}")
    return MODE_MAP[mode_key]


def _create_legacy_router(service: QuotationService) -> APIRouter:
    api_router = APIRouter(prefix="/api", tags=["Panelin v4"])

    @api_router.get("/health")
    async def api_health() -> dict[str, str]:
        return {"status": "healthy"}

    def _run_quote(input_data: PanelinEngineInput) -> dict[str, Any]:
        mode = _resolve_mode(input_data.mode)
        output = service.process(
            text=input_data.text,
            force_mode=mode,
            client_name=input_data.client_name,
            client_phone=input_data.client_phone,
            client_location=input_data.client_location,
        )
        return output.to_dict()

    @api_router.post("/quote")
    async def quote(payload: PanelinEngineInput) -> dict[str, Any]:
        try:
            return {"ok": True, "data": await run_in_threadpool(_run_quote, payload)}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def _run_validation(input_data: PanelinEngineInput) -> dict[str, Any]:
        mode = _resolve_mode(input_data.mode)
        classification = service.classify(input_data.text, force_mode=mode)
        request = service.parse(input_data.text)
        service.inject_client_data(
            request,
            client_name=input_data.client_name,
            client_phone=input_data.client_phone,
            client_location=input_data.client_location,
        )
        service.apply_defaults(request, classification.operating_mode)
        sre = service.sre(request)
        bom = service.bom(request)
        pricing = service.pricing(request, bom)
        validation = service.validation(
            request=request,
            sre=sre,
            bom=bom,
            pricing=pricing,
            mode=classification.operating_mode,
        )
        return {
            "mode": classification.operating_mode.value,
            "classification": classification.to_dict(),
            "request": request.to_dict(),
            "sre": sre.to_dict(),
            "bom": bom.to_dict(),
            "pricing": pricing.to_dict(),
            "validation": validation.to_dict(),
        }

    @api_router.post("/validate")
    async def validate(payload: PanelinEngineInput) -> dict[str, Any]:
        try:
            return {"ok": True, "data": await run_in_threadpool(_run_validation, payload)}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def _run_sai_score(input_data: PanelinEngineInput) -> dict[str, Any]:
        mode = _resolve_mode(input_data.mode)
        output = service.process(
            text=input_data.text,
            force_mode=mode,
            client_name=input_data.client_name,
            client_phone=input_data.client_phone,
            client_location=input_data.client_location,
        )
        sai = service.sai(output)
        return {
            "quote_id": output.quote_id,
            "quote_status": output.status,
            "mode": output.mode,
            "sai": sai.to_dict(),
        }

    @api_router.post("/sai-score")
    async def sai_score(payload: PanelinEngineInput) -> dict[str, Any]:
        try:
            return {"ok": True, "data": await run_in_threadpool(_run_sai_score, payload)}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    return api_router


def _mount_legacy_routes(base_app, service: QuotationService) -> None:
    existing = {(route.path, tuple(sorted(route.methods))) for route in base_app.routes if hasattr(route, "methods")}
    router = _create_legacy_router(service)
    already_mounted = any(path == "/api/quote" for path, _ in existing)
    if not already_mounted:
        base_app.include_router(router)


settings = get_settings()
service = QuotationService()
_mount_legacy_routes(wolf_app, service)

runtime = build_panelin_runtime(settings)

auth_config = None
if settings.agentos_authorization:
    auth_config = AuthorizationConfig(
        verification_keys=settings.agentos_jwt_verification_keys or None,
        algorithm=settings.agentos_jwt_algorithm,
        verify_audience=settings.agentos_verify_audience,
    )

agent_os = AgentOS(
    id="panelin-agent-os",
    name="Panelin AgentOS",
    description="AgentOS para Panelin con workflow deterministico + agente conversacional.",
    db=runtime.db,
    agents=[runtime.agent],
    workflows=[runtime.workflow],
    base_app=wolf_app,
    on_route_conflict="preserve_base_app",
    authorization=settings.agentos_authorization,
    authorization_config=auth_config,
    tracing=settings.agentos_tracing,
)

app = agent_os.get_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=int(os.environ.get("PORT", settings.port)))
