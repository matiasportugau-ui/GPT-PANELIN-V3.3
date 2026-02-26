"""
Wolf API - FastAPI Backend for Panelin Knowledge Base
Implements KB persistence with GCS + Google Sheets integration
v3.0.0 — 2026-02-26
"""

import logging
import os
import json
import hmac
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from google.cloud import storage
from google.api_core import exceptions as gexc
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)

# FastAPI app configuration
app = FastAPI(
        title="Panelin Wolf API",
        description="Complete API for BMC Uruguay — KB persistence, Google Sheets integration",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
)

# --- KB Architecture: Event-Sourced Versioning (optional) ---
try:
        from .kb_routes import router as kb_architecture_router
        app.include_router(kb_architecture_router)
        _KB_ARCHITECTURE_AVAILABLE = True
except Exception as e:
        _KB_ARCHITECTURE_AVAILABLE = False
        logger.warning(f"KB Architecture module not available: {e}")

# --- Google Sheets Integration ---
try:
        from sheets_routes import router as sheets_router
        _SHEETS_AVAILABLE = True
except Exception as e:
        _SHEETS_AVAILABLE = False
        logger.warning(f"Sheets module not available: {e}")

@app.on_event("startup")
async def startup_create_kb_tables():
        if not _KB_ARCHITECTURE_AVAILABLE:
                    return
                kb_db_url = os.environ.get("KB_DATABASE_URL", "")
    if not kb_db_url:
                logger.info("KB_DATABASE_URL not set, skipping KB table creation")
                return
            try:
                        from .kb_database import engine
                        from .kb_models import Base
                        async with engine.begin() as conn:
                                        await conn.run_sync(Base.metadata.create_all)
                                    logger.info("KB Architecture tables verified/created")
except Exception as e:
        logger.warning(f"KB Architecture table creation skipped: {e}")

# Security configuration
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Environment configuration
WOLF_API_KEY = os.environ.get("WOLF_API_KEY", "")
KB_GCS_BUCKET = os.environ.get("KB_GCS_BUCKET", "")
KB_GCS_PREFIX = os.environ.get("KB_GCS_PREFIX", "kb/conversations")
KB_GCS_MODE = os.environ.get("KB_GCS_MODE", "daily_jsonl")
KB_GCS_MAX_RETRIES = int(os.environ.get("KB_GCS_MAX_RETRIES", "5"))

_storage_client: Optional[storage.Client] = None


def _require_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> None:
        if not WOLF_API_KEY:
                    raise HTTPException(
                                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                                    detail="Service not configured: WOLF_API_KEY is missing",
                    )
    if not api_key or not hmac.compare_digest(api_key, WOLF_API_KEY):
                raise HTTPException(
                                status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid or missing X-API-Key",
                )


def _get_storage_client() -> storage.Client:
        global _storage_client
    if _storage_client is None:
                _storage_client = storage.Client()
    return _storage_client


def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()


def _compose_append_jsonl_line(
        bucket_name: str,
        destination_blob_name: str,
        jsonl_line: str,
        tmp_prefix: str,
        max_retries: int,
) -> Dict[str, Any]:
        client = _get_storage_client()
    bucket = client.bucket(bucket_name)
    tmp_name = f"{tmp_prefix}/tmp/{uuid.uuid4().hex}.jsonl"
    tmp_blob = bucket.blob(tmp_name)
    tmp_blob.upload_from_string(jsonl_line, content_type="application/x-ndjson")
    dest_blob = bucket.blob(destination_blob_name)
    last_exc: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
                try:
                                try:
                                                    dest_blob.reload()
                                                    dest_generation = int(dest_blob.generation or 0)
                                                    dest_exists = True
                except gexc.NotFound:
                dest_generation = 0
                dest_exists = False
            if dest_exists:
                                dest_src = bucket.blob(destination_blob_name, generation=dest_generation)
                                sources = [dest_src, tmp_blob]
                                if_generation_match = dest_generation
else:
                sources = [tmp_blob]
                if_generation_match = 0
            dest_blob.content_type = "application/x-ndjson"
            dest_blob.compose(sources, if_generation_match=if_generation_match)
            try:
                                tmp_blob.delete()
except Exception:
                pass
            return {
                                "ok": True,
                                "bucket": bucket_name,
                                "object": destination_blob_name,
                                "tmp_object": tmp_name,
                                "attempts": attempt,
            }
except gexc.PreconditionFailed:
            last_exc = None
            continue
except Exception as exc:
            last_exc = exc
            break
    try:
                tmp_blob.delete()
except Exception:
        pass
    raise last_exc or RuntimeError("Unknown error during GCS compose append")


def _persist_kb_conversation(payload: Dict[str, Any]) -> Dict[str, Any]:
        if not KB_GCS_BUCKET:
                    raise HTTPException(
                                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                                    detail="Service not configured: KB_GCS_BUCKET is missing",
                    )
    prefix_override = payload.pop("_gcs_prefix_override", None)
    effective_prefix = prefix_override if prefix_override else KB_GCS_PREFIX
    jsonl_line = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    if KB_GCS_MODE == "per_event_jsonl":
                ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        obj = f"{effective_prefix}/events/{ts}-{uuid.uuid4().hex}.jsonl"
        client = _get_storage_client()
        bucket = client.bucket(KB_GCS_BUCKET)
        blob = bucket.blob(obj)
        blob.upload_from_string(jsonl_line, content_type="application/x-ndjson")
        return {"ok": True, "bucket": KB_GCS_BUCKET, "object": obj, "mode": KB_GCS_MODE}
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    destination = f"{effective_prefix}/daily/{day}.jsonl"
    result = _compose_append_jsonl_line(
                bucket_name=KB_GCS_BUCKET,
                destination_blob_name=destination,
                jsonl_line=jsonl_line,
                tmp_prefix=effective_prefix,
                max_retries=KB_GCS_MAX_RETRIES,
    )
    result["mode"] = KB_GCS_MODE
    return result


# Register Sheets router with API key auth
if _SHEETS_AVAILABLE:
        app.include_router(sheets_router, dependencies=[Security(_require_api_key)])
    logger.info("Sheets routes registered")


# ============================ API Endpoints ============================

@app.get("/")
async def root():
        return {
                    "name": "Panelin Wolf API",
                    "version": "3.0.0",
                    "status": "operational",
                    "kb_architecture": _KB_ARCHITECTURE_AVAILABLE,
                    "sheets_integration": _SHEETS_AVAILABLE
        }


@app.get("/health")
async def health():
        return {"status": "healthy"}


@app.get("/ready")
async def ready():
        return {"status": "ready", "version": "3.0.0"}


@app.post("/kb/conversations", status_code=200)
async def kb_conversations(
        body: Dict[str, Any],
        _: None = Security(_require_api_key)
) -> Dict[str, Any]:
        envelope = {
                    "received_at": _utc_now_iso(),
                    "type": "kb.conversation",
                    "data": body,
        }
    gcs_result = await run_in_threadpool(_persist_kb_conversation, envelope)
    return {"ok": True, "stored_at": envelope["received_at"], "gcs": gcs_result}


@app.post("/kb/corrections", status_code=200)
async def kb_corrections(
        body: Dict[str, Any],
        _: None = Security(_require_api_key)
) -> Dict[str, Any]:
        required = ("source_file", "field_path", "old_value", "new_value", "reason")
    missing = [f for f in required if not body.get(f)]
    if missing:
                raise HTTPException(
                                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail=f"Missing required fields: {', '.join(missing)}",
                )
    correction_id = f"cor-{uuid.uuid4().hex[:12]}"
    envelope = {
                "received_at": _utc_now_iso(),
                "type": "kb.correction",
                "correction_id": correction_id,
                "data": body,
    }
    gcs_result = await run_in_threadpool(
                _persist_kb_conversation,
                {**envelope, "_gcs_prefix_override": "kb/corrections"},
    )
    return {"ok": True, "correction_id": correction_id, "stored_at": envelope["received_at"], "gcs": gcs_result}


@app.post("/kb/customers", status_code=200)
async def kb_customers_save(
        body: Dict[str, Any],
        _: None = Security(_require_api_key)
) -> Dict[str, Any]:
        if not body.get("name") or not body.get("phone"):
                    raise HTTPException(
                                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail="Missing required fields: name, phone",
                    )
    customer_id = f"cust-{uuid.uuid4().hex[:12]}"
    envelope = {
                "received_at": _utc_now_iso(),
                "type": "kb.customer",
                "customer_id": customer_id,
                "data": body,
    }
    gcs_result = await run_in_threadpool(
                _persist_kb_conversation,
                {**envelope, "_gcs_prefix_override": "kb/customers"},
    )
    return {"ok": True, "customer_id": customer_id, "stored_at": envelope["received_at"], "gcs": gcs_result}


@app.get("/kb/customers", status_code=200)
async def kb_customers_lookup(
        search: str = "",
        _: None = Security(_require_api_key)
) -> Dict[str, Any]:
        if len(search) < 2:
                    raise HTTPException(
                                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail="search query must be at least 2 characters",
                    )
    if not KB_GCS_BUCKET:
                return {"ok": True, "customers": [], "count": 0, "note": "KB_GCS_BUCKET not configured"}

    def _read_customers() -> list:
                client = _get_storage_client()
        prefix = "kb/customers/daily/"
        blobs = sorted(
                        client.list_blobs(KB_GCS_BUCKET, prefix=prefix),
                        key=lambda b: b.name, reverse=True,
        )[:30]
        results = []
        term = search.lower()
        for blob in blobs:
                        try:
                                            lines = blob.download_as_text().splitlines()
                                            for line in lines:
                                                                    if not line.strip():
                                                                                                continue
                                                                                            record = json.loads(line)
                                                                    data = record.get("data", {})
                                                                    if (
                                                                                                term in str(data.get("name", "")).lower()
                                                                                                or term in str(data.get("phone", "")).lower()
                                                                                                or term in str(data.get("address", "")).lower()
                                                                    ):
                                                                                                results.append({
                                                                                                                                "customer_id": record.get("customer_id"),
                                                                                                                                "name": data.get("name"),
                                                                                                                                "phone": data.get("phone"),
                                                                                                                                "address": data.get("address"),
                                                                                                                                "city": data.get("city"),
                                                                                                                                "department": data.get("department"),
                                                                                                                                "notes": data.get("notes"),
                                                                                                                                "last_interaction": data.get("last_interaction"),
                                                                                                                                "stored_at": record.get("received_at"),
                                                                                                    })
        except Exception:
                logger.warning("Skipping malformed record in blob %s", blob.name, exc_info=True)
                continue
        return results

    customers = await run_in_threadpool(_read_customers)
    return {"ok": True, "customers": customers, "count": len(customers)}
