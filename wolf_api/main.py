"""
Wolf API - FastAPI Backend for Panelin Knowledge Base
v3.0.0 — 2026-02-26
"""

import logging
import os
import json
import hmac
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Security, Query, status
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)
app = FastAPI(
    title="Panelin Wolf API",
    description="Complete API for BMC Uruguay — quotations, KB persistence, Google Sheets",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
WOLF_API_KEY = os.environ.get("WOLF_API_KEY", "")

def require_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> None:
    if not WOLF_API_KEY:
        raise HTTPException(503, "WOLF_API_KEY not configured")
    if not api_key or not hmac.compare_digest(api_key, WOLF_API_KEY):
        raise HTTPException(401, "Invalid or missing X-API-Key")


KB_GCS_BUCKET = os.environ.get("KB_GCS_BUCKET", "")
_storage_client = None
_bucket = None


def _get_gcs_bucket():
    global _storage_client, _bucket
    if _bucket is None:
        if not KB_GCS_BUCKET:
            raise HTTPException(503, "KB_GCS_BUCKET not configured")
        try:
            from google.cloud import storage
            _storage_client = storage.Client()
            _bucket = _storage_client.bucket(KB_GCS_BUCKET)
        except Exception as e:
            raise HTTPException(503, f"GCS connection failed: {e}")
    return _bucket

def _append_jsonl(blob_path: str, record: dict) -> dict:
    bucket = _get_gcs_bucket()
    blob = bucket.blob(blob_path)
    existing = ""
    if blob.exists():
        existing = blob.download_as_text()
    line = json.dumps(record, ensure_ascii=False, default=str)
    new_content = existing + line + "\n"
    blob.upload_from_string(new_content, content_type="application/jsonl")
    return {"bucket": KB_GCS_BUCKET, "blob": blob_path}


CATALOG = {}


def _load_catalog():
    global CATALOG
    catalog_path = os.environ.get("CATALOG_PATH", "catalog.json")
    if os.path.exists(catalog_path):
        with open(catalog_path) as f:
            CATALOG = json.load(f)
        logger.info(f"Loaded catalog: {len(CATALOG)} products")
    else:
        logger.warning(f"Catalog not found at {catalog_path}")


@app.on_event("startup")
async def startup():
    _load_catalog()


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/ready")
async def ready_check():
    return {
        "status": "ready",
        "version": "3.0.1",
        "gcs_configured": bool(KB_GCS_BUCKET),
        "sheets_configured": bool(os.environ.get("SHEETS_SPREADSHEET_ID", "")),
    }

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
    query: str = Field(..., min_length=3)
    max_results: int = Field(5, ge=1, le=20)


class ProductPriceRequest(BaseModel):
    product_id: str


@app.post("/calculate_quote")
async def api_calculate_quote(req: QuoteRequest, _=Security(require_api_key)):
    product = CATALOG.get(req.product_id)
    if not product:
        raise HTTPException(404, f"Product not found: {req.product_id}")
    price = float(product.get("price_usd", 0))
    area = req.length_m * req.width_m
    subtotal = price * area * req.quantity
    discount = subtotal * (req.discount_percent / 100)
    total = subtotal - discount
    if not req.include_tax:
        total = total / 1.22
    return {
        "product_id": req.product_id,
        "unit_price": price,
        "area_m2": area,
        "quantity": req.quantity,
        "subtotal": round(subtotal, 2),
        "discount": round(discount, 2),
        "total": round(total, 2),
        "tax_included": req.include_tax,
    }

@app.post("/find_products")
async def api_find_products(req: ProductSearchRequest, _=Security(require_api_key)):
    query_lower = req.query.lower()
    results = []
    for pid, pdata in CATALOG.items():
        searchable = f"{pid} {pdata.get('name', '')} {pdata.get('description', '')}".lower()
        if any(term in searchable for term in query_lower.split()):
            results.append({"product_id": pid, **pdata})
            if len(results) >= req.max_results:
                break
    return {"query": req.query, "results": results, "count": len(results)}


@app.post("/product_price")
async def api_product_price(req: ProductPriceRequest, _=Security(require_api_key)):
    product = CATALOG.get(req.product_id)
    if not product:
        raise HTTPException(404, f"Product not found: {req.product_id}")
    return {"product_id": req.product_id, **product}


@app.post("/check_availability")
async def api_check_availability(req: ProductPriceRequest, _=Security(require_api_key)):
    product = CATALOG.get(req.product_id)
    if not product:
        raise HTTPException(404, f"Product not found: {req.product_id}")
    return {
        "product_id": req.product_id,
        "available": product.get("available", True),
        "stock": product.get("stock", "consultar"),
    }

@app.post("/kb/conversations")
async def persist_conversation(data: dict, _=Security(require_api_key)):
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "client_id": data.get("client_id", "unknown"),
        "summary": data.get("summary", ""),
        "quotation_ref": data.get("quotation_ref"),
        "products_discussed": data.get("products_discussed", []),
        "date": data.get("date", now),
        "stored_at": now,
    }
    gcs = await run_in_threadpool(_append_jsonl, "kb/conversations.jsonl", record)
    return {"ok": True, "stored_at": now, "gcs": gcs}


@app.post("/kb/corrections")
async def register_correction(data: dict, _=Security(require_api_key)):
    now = datetime.now(timezone.utc).isoformat()
    src = data.get("source_file", "")
    cid = f"cor-{hashlib.md5(f'{src}{now}'.encode()).hexdigest()[:12]}"
    record = {
        "correction_id": cid,
        "source_file": src,
        "field_path": data.get("field_path", ""),
        "old_value": data.get("old_value", ""),
        "new_value": data.get("new_value", ""),
        "reason": data.get("reason", ""),
        "reported_by": data.get("reported_by", "panelin_gpt"),
        "date": now,
        "status": "pending",
    }
    gcs = await run_in_threadpool(_append_jsonl, "kb/corrections.jsonl", record)
    return {"ok": True, "correction_id": cid, "stored_at": now, "gcs": gcs}

@app.post("/kb/customers")
async def save_customer(data: dict, _=Security(require_api_key)):
    now = datetime.now(timezone.utc).isoformat()
    raw_id = data.get("phone", data.get("name", "unknown"))
    cust_id = f"cust-{hashlib.md5(raw_id.encode()).hexdigest()[:12]}"
    blob_path = f"kb/customers/{cust_id}.json"
    bucket = _get_gcs_bucket()
    blob = bucket.blob(blob_path)
    existing = {}
    if blob.exists():
        existing = json.loads(blob.download_as_text())
    customer = {
        **existing,
        "customer_id": cust_id,
        "name": data.get("name", existing.get("name", "")),
        "phone": data.get("phone", existing.get("phone", "")),
        "address": data.get("address", existing.get("address", "")),
        "city": data.get("city", existing.get("city", "")),
        "department": data.get("department", existing.get("department", "")),
        "notes": data.get("notes", existing.get("notes", "")),
        "last_interaction": now,
        "updated_at": now,
    }
    blob.upload_from_string(
        json.dumps(customer, ensure_ascii=False, indent=2),
        content_type="application/json",
    )
    return {"ok": True, "customer_id": cust_id, "stored_at": now}

@app.get("/kb/customers")
async def lookup_customer(search: str = Query(..., min_length=2), _=Security(require_api_key)):
    bucket = _get_gcs_bucket()
    search_lower = search.lower()
    results = []
    for blob in bucket.list_blobs(prefix="kb/customers/"):
        if not blob.name.endswith(".json"):
            continue
        try:
            cdata = json.loads(blob.download_as_text())
            haystack = f"{cdata.get('name','')} {cdata.get('phone','')} {cdata.get('city','')}".lower()
            if search_lower in haystack:
                results.append(cdata)
        except Exception:
            continue
    return {"ok": True, "customers": results, "count": len(results)}

SHEETS_ID = os.environ.get("SHEETS_SPREADSHEET_ID", "")
SHEETS_TAB_2026 = os.environ.get("SHEETS_TAB_2026", "Administrador de Cotizaciones 2026")
SHEETS_TAB_2025 = os.environ.get("SHEETS_TAB_2025", "2.0 -  Administrador de Cotizaciones")
SHEETS_TAB_ADMIN = os.environ.get("SHEETS_TAB_ADMIN", "Admin.")
_gc = None
_spreadsheet = None


def _get_spreadsheet():
    global _gc, _spreadsheet
    if _spreadsheet is None:
        if not SHEETS_ID:
            raise HTTPException(503, "SHEETS_SPREADSHEET_ID not configured")
        try:
            import gspread
            from google.auth import default as gauth_default
            creds, _ = gauth_default(scopes=["https://www.googleapis.com/auth/spreadsheets"])
            _gc = gspread.authorize(creds)
            _spreadsheet = _gc.open_by_key(SHEETS_ID)
        except Exception as e:
            raise HTTPException(503, f"Sheets connection failed: {e}")
    return _spreadsheet


def _get_worksheet(tab=None):
    ss = _get_spreadsheet()
    tab_name = tab or SHEETS_TAB_2026
    try:
        return ss.worksheet(tab_name)
    except Exception:
        raise HTTPException(404, f"Tab '{tab_name}' not found")


def _get_admin_worksheet():
    """Get the Admin tab for write operations (new consultations, quotation lines)."""
    ss = _get_spreadsheet()
    tab_name = SHEETS_TAB_ADMIN.strip()
    try:
        return ss.worksheet(tab_name)
    except Exception:
        # Fallback to default tab if Admin not found
        logger.warning(f"Admin tab '{tab_name}' not found, falling back to default")
        return _get_worksheet()


def _row_to_dict(row, row_number):
    return {
        "row_number": row_number,
        "asignado": row[0] if len(row) > 0 else "",
        "estado": row[1] if len(row) > 1 else "",
        "fecha": row[2] if len(row) > 2 else "",
        "cliente": row[3] if len(row) > 3 else "",
        "origen": row[4] if len(row) > 4 else "",
        "telefono": row[5] if len(row) > 5 else "",
        "direccion": row[6] if len(row) > 6 else "",
        "consulta": row[7] if len(row) > 7 else "",
        "comentarios": row[8] if len(row) > 8 else "",
    }


def _find_last_data_row(all_rows):
    last = 2
    for i, row in enumerate(all_rows):
        if i < 2:
            continue
        if len(row) > 3 and row[3].strip():
            last = i + 1
    return last

@app.get("/sheets/consultations")
async def read_consultations(
    tab: Optional[str] = None,
    estado: Optional[str] = None,
    origen: Optional[str] = None,
    asignado: Optional[str] = None,
    cliente: Optional[str] = None,
    fecha: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    _=Security(require_api_key),
):
    ws = await run_in_threadpool(_get_worksheet, tab)
    all_rows = await run_in_threadpool(ws.get_all_values)
    results = []
    for i, row in enumerate(all_rows):
        if i < 2 or not any(c.strip() for c in row[:8]):
            continue
        entry = _row_to_dict(row, i + 1)
        if estado and entry["estado"].strip() != estado.strip():
            continue
        if origen and entry["origen"].strip().upper() != origen.strip().upper():
            continue
        if asignado and entry["asignado"].strip().upper() != asignado.strip().upper():
            continue
        if cliente and cliente.lower() not in entry["cliente"].lower():
            continue
        if fecha and entry["fecha"].strip() != fecha.strip():
            continue
        results.append(entry)
        if len(results) >= limit:
            break
    return {"tab": tab or SHEETS_TAB_2026, "total_results": len(results), "consultations": results}

@app.post("/sheets/consultations")
async def add_consultation(data: dict, _=Security(require_api_key)):
    ws = await run_in_threadpool(_get_admin_worksheet)
    fecha = data.get("fecha") or datetime.now(timezone.utc).strftime("%d-%m")
    new_row = [
        data.get("asignado", ""), "Pendiente", fecha,
        data.get("cliente", ""), (data.get("origen", "")).upper(),
        data.get("telefono", ""), data.get("direccion", ""),
        data.get("consulta", ""), data.get("comentarios", ""),
    ]
    all_rows = await run_in_threadpool(ws.get_all_values)
    r = _find_last_data_row(all_rows) + 1
    await run_in_threadpool(ws.update, f"A{r}:I{r}", [new_row])
    return {"success": True, "row_number": r, "data": _row_to_dict(new_row, r)}


@app.post("/sheets/quotation_line")
async def add_quotation_line(data: dict, _=Security(require_api_key)):
    ws = await run_in_threadpool(_get_admin_worksheet)
    fecha = datetime.now(timezone.utc).strftime("%d-%m")
    row_num = data.get("row_number")
    if row_num:
        current = await run_in_threadpool(ws.row_values, row_num)
        if data.get("estado"):
            await run_in_threadpool(ws.update_acell, f"B{row_num}", data["estado"])
        if data.get("comentarios"):
            old = current[8] if len(current) > 8 else ""
            sep = " | " if old else ""
            await run_in_threadpool(
                ws.update_acell, f"I{row_num}",
                f"{old}{sep}[Cotizado {fecha}] {data['comentarios']}",
            )
        return {"success": True, "action": "updated", "row_number": row_num}
    else:
        new_row = [
            data.get("asignado", ""), data.get("estado", "Enviado"), fecha,
            data.get("cliente", ""), (data.get("origen", "")).upper(),
            data.get("telefono", ""), data.get("direccion", ""),
            data.get("consulta", ""), data.get("comentarios", ""),
        ]
        all_rows = await run_in_threadpool(ws.get_all_values)
        r = _find_last_data_row(all_rows) + 1
        await run_in_threadpool(ws.update, f"A{r}:I{r}", [new_row])
        return {"success": True, "action": "appended", "row_number": r}

@app.patch("/sheets/update_row")
async def update_row(data: dict, _=Security(require_api_key)):
    ws = await run_in_threadpool(_get_worksheet)
    rn = data.get("row_number")
    if not rn:
        raise HTTPException(400, "row_number is required")
    col_map = {
        "estado": "B", "asignado": "A", "consulta": "H",
        "telefono": "F", "direccion": "G", "comentarios": "I",
    }
    updated = []
    for field, col in col_map.items():
        if data.get(field):
            await run_in_threadpool(ws.update_acell, f"{col}{rn}", data[field])
            updated.append(field)
    if not updated:
        raise HTTPException(400, "No fields to update")
    return {"success": True, "row_number": rn, "fields_updated": updated}


@app.get("/sheets/row/{row_number}")
async def get_row(row_number: int, tab: Optional[str] = None, _=Security(require_api_key)):
    ws = await run_in_threadpool(_get_worksheet, tab)
    values = await run_in_threadpool(ws.row_values, row_number)
    if not values:
        raise HTTPException(404, f"Row {row_number} is empty")
    return _row_to_dict(values, row_number)

@app.get("/sheets/search")
async def search_sheets(
    q: str = Query(..., min_length=2),
    tab: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    _=Security(require_api_key),
):
    ws = await run_in_threadpool(_get_worksheet, tab)
    all_rows = await run_in_threadpool(ws.get_all_values)
    q_lower = q.lower()
    results = []
    for i, row in enumerate(all_rows):
        if i < 2:
            continue
        cliente = row[3].lower() if len(row) > 3 else ""
        consulta = row[7].lower() if len(row) > 7 else ""
        if q_lower in cliente or q_lower in consulta:
            results.append(_row_to_dict(row, i + 1))
            if len(results) >= limit:
                break
    return {"query": q, "total_results": len(results), "results": results}


@app.get("/sheets/stats")
async def get_sheet_stats(tab: Optional[str] = None, _=Security(require_api_key)):
    ws = await run_in_threadpool(_get_worksheet, tab)
    all_rows = await run_in_threadpool(ws.get_all_values)
    stats = {"total_rows": 0, "by_estado": {}, "by_origen": {}, "by_asignado": {}}
    for i, row in enumerate(all_rows):
        if i < 2 or not any(c.strip() for c in row[:8]):
            continue
        stats["total_rows"] += 1
        e = row[1].strip() if len(row) > 1 else ""
        o = row[4].strip() if len(row) > 4 else ""
        a = row[0].strip() if len(row) > 0 else ""
        if e:
            stats["by_estado"][e] = stats["by_estado"].get(e, 0) + 1
        if o:
            stats["by_origen"][o] = stats["by_origen"].get(o, 0) + 1
        if a:
            stats["by_asignado"][a] = stats["by_asignado"].get(a, 0) + 1
    return stats


# ─── Multi-Sheet Inspector (Admin-Hub) ────────────────────────────────
@app.get("/sheets/inspect", tags=["admin-hub"])
async def inspect_sheet(
    sheet_id: str = Query(..., description="Google Sheets ID to inspect"),
    _=Security(require_api_key)
):
    """Inspect any Google Sheet shared with the service account."""
    try:
        _get_spreadsheet()
        target = await run_in_threadpool(_gc.open_by_key, sheet_id)
        worksheets = await run_in_threadpool(lambda: target.worksheets())
        result = {
            "sheet_id": sheet_id,
            "title": target.title,
            "url": f"https://docs.google.com/spreadsheets/d/{sheet_id}",
            "tab_count": len(worksheets),
            "tabs": []
        }
        for ws in worksheets:
            tab = {"name": ws.title, "gid": ws.id, "rows_alloc": ws.row_count, "cols_alloc": ws.col_count}
            try:
                vals = await run_in_threadpool(ws.get_all_values)
                tab["rows_used"] = len(vals)
                tab["headers"] = vals[0] if vals else []
                tab["sample"] = vals[1:6] if len(vals) > 1 else []
            except Exception as e:
                tab["error"] = str(e)
            result["tabs"].append(tab)
        return result
    except Exception as e:
        raise HTTPException(500, f"Cannot inspect sheet {sheet_id}: {e}")
