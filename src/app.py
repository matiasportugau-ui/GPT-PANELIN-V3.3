"""Panelin AgentOS entrypoint with legacy route compatibility."""

from __future__ import annotations

import hashlib
import hmac
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from agno.os import AgentOS
from agno.os.config import AuthorizationConfig
from fastapi import APIRouter, FastAPI, HTTPException, Query, Security, status
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field

from src.agent.panelin import PanelinRuntime
from src.core.config import get_settings
from src.quotation.schemas import PanelinEngineInput

settings = get_settings()
runtime = PanelinRuntime(settings)


def _load_catalog(path: str) -> dict[str, Any]:
    resolved = Path(path)
    if not resolved.exists():
        return {}
    with open(resolved, encoding="utf-8") as f:
        payload = json.load(f)
    return payload if isinstance(payload, dict) else {}


CATALOG = _load_catalog(settings.catalog_path)
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

_kb_customers: dict[str, dict[str, Any]] = {}
_kb_conversations: list[dict[str, Any]] = []
_sheets_rows: list[dict[str, Any]] = []


def _require_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> None:
    expected = settings.mcp_auth_header_value or ""
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WOLF_API_KEY not configured",
        )
    if not api_key or not hmac.compare_digest(api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key",
        )


class QuoteRequest(BaseModel):
    product_id: str = Field(..., description="Product ID")
    length_m: float = Field(..., ge=0.5, le=14.0)
    width_m: float = Field(..., ge=0.5, le=50.0)
    quantity: int = Field(1, ge=1)
    discount_percent: float = Field(0.0, ge=0, le=30)
    include_accessories: bool = Field(False)
    include_tax: bool = Field(True)
    installation_type: str = Field("techo")


class ProductSearchRequest(BaseModel):
    query: str = Field(..., min_length=2)
    max_results: int = Field(5, ge=1, le=50)


class ProductPriceRequest(BaseModel):
    product_id: str


legacy_router = APIRouter(tags=["Panelin legacy compatibility"])
api_router = APIRouter(prefix="/api", tags=["Panelin v4"])


@legacy_router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@legacy_router.get("/ready")
async def ready() -> dict[str, Any]:
    return {
        "status": "ready",
        "agentos": True,
        "catalog_size": len(CATALOG),
        "mcp_enabled": settings.enable_mcp_tools,
    }


@legacy_router.post("/calculate_quote")
async def calculate_quote(req: QuoteRequest, _=Security(_require_api_key)) -> dict[str, Any]:
    product = CATALOG.get(req.product_id)
    if not product:
        raise HTTPException(404, f"Product not found: {req.product_id}")
    unit_price = float(product.get("price_usd", 0))
    area = req.length_m * req.width_m
    subtotal = unit_price * area * req.quantity
    discount = subtotal * (req.discount_percent / 100)
    total = subtotal - discount
    if not req.include_tax:
        total = total / 1.22
    return {
        "product_id": req.product_id,
        "unit_price": unit_price,
        "area_m2": area,
        "quantity": req.quantity,
        "subtotal": round(subtotal, 2),
        "discount": round(discount, 2),
        "total": round(total, 2),
        "tax_included": req.include_tax,
    }


@legacy_router.post("/find_products")
async def find_products(req: ProductSearchRequest, _=Security(_require_api_key)) -> dict[str, Any]:
    return runtime.quotation_service.search_products(query=req.query, max_results=req.max_results)


@legacy_router.post("/product_price")
async def product_price(req: ProductPriceRequest, _=Security(_require_api_key)) -> dict[str, Any]:
    product = CATALOG.get(req.product_id)
    if not product:
        raise HTTPException(404, f"Product not found: {req.product_id}")
    return {"product_id": req.product_id, **product}


@legacy_router.post("/check_availability")
async def check_availability(req: ProductPriceRequest, _=Security(_require_api_key)) -> dict[str, Any]:
    product = CATALOG.get(req.product_id)
    if not product:
        raise HTTPException(404, f"Product not found: {req.product_id}")
    return {
        "product_id": req.product_id,
        "available": product.get("available", True),
        "stock": product.get("stock", "consultar"),
    }


@legacy_router.post("/kb/conversations")
async def kb_conversations(data: dict[str, Any], _=Security(_require_api_key)) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "client_id": data.get("client_id", "unknown"),
        "summary": data.get("summary", ""),
        "quotation_ref": data.get("quotation_ref"),
        "products_discussed": data.get("products_discussed", []),
        "stored_at": now,
    }
    _kb_conversations.append(record)
    return {"ok": True, "stored_at": now}


@legacy_router.post("/kb/corrections")
async def kb_corrections(data: dict[str, Any], _=Security(_require_api_key)) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    source = data.get("source_file", "")
    correction_id = f"cor-{hashlib.md5(f'{source}{now}'.encode()).hexdigest()[:12]}"
    return {"ok": True, "correction_id": correction_id, "stored_at": now}


@legacy_router.post("/kb/customers")
async def kb_customers_save(data: dict[str, Any], _=Security(_require_api_key)) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    raw_id = data.get("phone", data.get("name", "unknown"))
    customer_id = f"cust-{hashlib.md5(raw_id.encode()).hexdigest()[:12]}"
    record = {**data, "customer_id": customer_id, "updated_at": now}
    _kb_customers[customer_id] = record
    return {"ok": True, "customer_id": customer_id, "stored_at": now}


@legacy_router.get("/kb/customers")
async def kb_customers_lookup(search: str = Query(..., min_length=2), _=Security(_require_api_key)) -> dict[str, Any]:
    query = search.lower()
    results = [
        customer
        for customer in _kb_customers.values()
        if query in f"{customer.get('name', '')} {customer.get('phone', '')} {customer.get('city', '')}".lower()
    ]
    return {"ok": True, "customers": results, "count": len(results)}


@legacy_router.get("/sheets/consultations")
async def sheets_consultations(limit: int = Query(50, ge=1, le=200), _=Security(_require_api_key)) -> dict[str, Any]:
    return {"tab": "in_memory", "total_results": min(limit, len(_sheets_rows)), "consultations": _sheets_rows[:limit]}


@legacy_router.post("/sheets/consultations")
async def sheets_add_consultation(data: dict[str, Any], _=Security(_require_api_key)) -> dict[str, Any]:
    row_number = len(_sheets_rows) + 1
    row = {"row_number": row_number, **data}
    _sheets_rows.append(row)
    return {"success": True, "row_number": row_number, "data": row}


@legacy_router.post("/sheets/quotation_line")
async def sheets_quotation_line(data: dict[str, Any], _=Security(_require_api_key)) -> dict[str, Any]:
    row_number = data.get("row_number")
    if row_number and 1 <= row_number <= len(_sheets_rows):
        _sheets_rows[row_number - 1].update(data)
        return {"success": True, "action": "updated", "row_number": row_number}
    row_number = len(_sheets_rows) + 1
    _sheets_rows.append({"row_number": row_number, **data})
    return {"success": True, "action": "appended", "row_number": row_number}


@legacy_router.patch("/sheets/update_row")
async def sheets_update_row(data: dict[str, Any], _=Security(_require_api_key)) -> dict[str, Any]:
    row_number = int(data.get("row_number", 0))
    if row_number <= 0 or row_number > len(_sheets_rows):
        raise HTTPException(404, "Row not found")
    _sheets_rows[row_number - 1].update(data)
    return {"success": True, "row_number": row_number}


@api_router.post("/quote")
async def api_quote(payload: PanelinEngineInput) -> dict[str, Any]:
    return {"ok": True, "data": runtime.quotation_service.quote(payload)}


@api_router.post("/validate")
async def api_validate(payload: PanelinEngineInput) -> dict[str, Any]:
    return {"ok": True, "data": runtime.quotation_service.validate(payload)}


@api_router.post("/sai-score")
async def api_sai(payload: PanelinEngineInput) -> dict[str, Any]:
    return {"ok": True, "data": runtime.quotation_service.sai_score(payload)}


def _build_authorization_config() -> AuthorizationConfig | None:
    if not settings.agentos_authorization:
        return None
    return AuthorizationConfig(
        verification_keys=settings.jwt_verification_keys_list or None,
        algorithm=settings.jwt_algorithm,
        verify_audience=settings.verify_audience,
    )


legacy_app = FastAPI(
    title="Panelin Legacy API (compat)",
    description="Compatibility layer while migrating to Agno AgentOS.",
    version="4.0.0",
)
legacy_app.include_router(legacy_router)
legacy_app.include_router(api_router)


@asynccontextmanager
async def panelin_lifespan(_: FastAPI):
    await runtime.startup()
    yield
    await runtime.shutdown()


agent_os = AgentOS(
    id="panelin-agent-os",
    name="Panelin AgentOS",
    description="Panelin quoting agent with deterministic workflow + conversational layer",
    db=runtime.db,
    agents=[runtime.agent],
    workflows=[runtime.workflow],
    base_app=legacy_app,
    on_route_conflict="preserve_base_app",
    cors_allowed_origins=settings.cors_allow_origins_list or None,
    authorization=settings.agentos_authorization,
    authorization_config=_build_authorization_config(),
    tracing=settings.tracing_enabled,
    lifespan=panelin_lifespan,
)

app = agent_os.get_app()

