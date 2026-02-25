"""
Wolf API - FastAPI Backend for Panelin Knowledge Base
Implements POST /kb/conversations with GCS persistence
Implements Event-Sourced Versioned KB Architecture (kb_routes)
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
    description="Knowledge Base API for Panelin GPT Assistant",
    version="2.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# --- KB Architecture: Event-Sourced Versioning ---
try:
    from .kb_routes import router as kb_architecture_router
    app.include_router(kb_architecture_router)
    _KB_ARCHITECTURE_AVAILABLE = True
except Exception as e:
    _KB_ARCHITECTURE_AVAILABLE = False
    logger.warning(f"KB Architecture module not available: {e}")


@app.on_event("startup")
async def startup_create_kb_tables():
    """Create KB Architecture tables on startup if DB is available."""
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
KB_GCS_MODE = os.environ.get("KB_GCS_MODE", "daily_jsonl")  # daily_jsonl | per_event_jsonl
KB_GCS_MAX_RETRIES = int(os.environ.get("KB_GCS_MAX_RETRIES", "5"))

# Global storage client (initialized lazily)
_storage_client: Optional[storage.Client] = None


def _require_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> None:
    """Validate API key from X-API-Key header."""
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
    """Get or create GCS client (uses ADC from service account)."""
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client()
    return _storage_client


def _utc_now_iso() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def _compose_append_jsonl_line(
    bucket_name: str,
    destination_blob_name: str,
    jsonl_line: str,
    tmp_prefix: str,
    max_retries: int,
) -> Dict[str, Any]:
    """
    Append one JSONL line to destination_blob_name using GCS compose.
    
    This implements atomic append by:
    1. Uploading the new line to a temporary object
    2. Composing [destination, tmp] into destination with if_generation_match
    3. Retrying on 412 Precondition Failed (concurrent modifications)
    
    Args:
        bucket_name: GCS bucket name
        destination_blob_name: Target object name
        jsonl_line: JSONL line to append (must end with newline)
        tmp_prefix: Prefix for temporary objects
        max_retries: Maximum number of retry attempts
    
    Returns:
        Dict with operation result metadata
    
    Raises:
        Exception: If operation fails after all retries
    """
    client = _get_storage_client()
    bucket = client.bucket(bucket_name)

    # 1) Upload tmp object (unique per request)
    tmp_name = f"{tmp_prefix}/tmp/{uuid.uuid4().hex}.jsonl"
    tmp_blob = bucket.blob(tmp_name)
    tmp_blob.upload_from_string(jsonl_line, content_type="application/x-ndjson")

    dest_blob = bucket.blob(destination_blob_name)

    last_exc: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            # 2) Determine whether destination exists and its generation
            try:
                dest_blob.reload()  # metadata fetch
                dest_generation = int(dest_blob.generation or 0)
                dest_exists = True
            except gexc.NotFound:
                dest_generation = 0
                dest_exists = False

            # 3) Compose with correct precondition
            if dest_exists:
                # Use a source blob handle for current destination
                dest_src = bucket.blob(destination_blob_name, generation=dest_generation)
                sources = [dest_src, tmp_blob]
                if_generation_match = dest_generation
            else:
                sources = [tmp_blob]
                if_generation_match = 0  # only if no live object exists

            dest_blob.content_type = "application/x-ndjson"
            dest_blob.compose(sources, if_generation_match=if_generation_match)

            # 4) Cleanup tmp (best-effort)
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

        except gexc.PreconditionFailed as exc:
            # 412: generation mismatch -> race; retry
            last_exc = exc
            continue
        except Exception as exc:
            last_exc = exc
            break

    # Cleanup tmp on failure (best-effort)
    try:
        tmp_blob.delete()
    except Exception:
        pass

    raise last_exc or RuntimeError("Unknown error during GCS compose append")


def _persist_kb_conversation(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Persist conversation data to GCS.
    
    Supports two modes:
    - daily_jsonl: Append to daily file using compose (default)
    - per_event_jsonl: Create separate file per event
    
    Args:
        payload: Conversation data to persist
    
    Returns:
        Dict with persistence result metadata
    
    Raises:
        HTTPException: If KB_GCS_BUCKET not configured or GCS operation fails
    """
    if not KB_GCS_BUCKET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not configured: KB_GCS_BUCKET is missing",
        )

    # Allow callers to override the GCS prefix (e.g. for corrections/customers)
    prefix_override = payload.pop("_gcs_prefix_override", None)
    effective_prefix = prefix_override if prefix_override else KB_GCS_PREFIX

    # Ensure JSONL is one line + newline
    jsonl_line = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"

    if KB_GCS_MODE == "per_event_jsonl":
        # One object per event (still a valid JSONL line file)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        obj = f"{effective_prefix}/events/{ts}-{uuid.uuid4().hex}.jsonl"
        client = _get_storage_client()
        bucket = client.bucket(KB_GCS_BUCKET)
        blob = bucket.blob(obj)
        blob.upload_from_string(jsonl_line, content_type="application/x-ndjson")
        return {"ok": True, "bucket": KB_GCS_BUCKET, "object": obj, "mode": KB_GCS_MODE}

    # Default: daily JSONL append via compose
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


# ============================
# API Endpoints
# ============================

@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "Panelin Wolf API",
        "version": "2.2.0",
        "status": "operational",
        "kb_architecture": _KB_ARCHITECTURE_AVAILABLE
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/ready")
async def ready():
    """Readiness check endpoint."""
    return {"status": "ready"}


@app.post("/kb/conversations", status_code=200, operation_id="persist_conversation")
async def kb_conversations(
    body: Dict[str, Any],
    _: None = Security(_require_api_key)
) -> Dict[str, Any]:
    """
    Persist conversation data to Knowledge Base.
    
    Requires X-API-Key header for authentication.
    Data is stored in GCS as JSONL format.
    
    Request body should contain:
    - client_id: str
    - summary: str
    - quotation_ref: str (optional)
    - products_discussed: list (optional)
    - date: str (ISO format, optional - will be added if missing)
    
    Returns:
        Dict with persistence confirmation and GCS metadata
    """
    # Add server-side metadata
    envelope = {
        "received_at": _utc_now_iso(),
        "type": "kb.conversation",
        "data": body,
    }
    
    # Persist to GCS
    gcs_result = await run_in_threadpool(_persist_kb_conversation, envelope)
    
    return {
        "ok": True,
        "stored_at": envelope["received_at"],
        "gcs": gcs_result,
    }


@app.post("/kb/corrections", status_code=200)
async def kb_corrections(
    body: Dict[str, Any],
    _: None = Security(_require_api_key)
) -> Dict[str, Any]:
    """
    Persist a KB correction to the Knowledge Base.

    Requires X-API-Key header for authentication.
    Data is stored in GCS as JSONL format.

    Request body should contain:
    - source_file: str — KB file where the error was found
    - field_path: str — JSON path to the incorrect field
    - old_value: str — current incorrect value
    - new_value: str — corrected value
    - reason: str — explanation of the correction
    - reported_by: str (optional) — who reported the correction

    Returns:
        Dict with correction_id, stored_at and GCS metadata
    """
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
        _persist_kb_conversation,  # reuse same GCS append helper
        {**envelope, "_gcs_prefix_override": "kb/corrections"},
    )

    return {
        "ok": True,
        "correction_id": correction_id,
        "stored_at": envelope["received_at"],
        "gcs": gcs_result,
    }


@app.post("/kb/customers", status_code=200)
async def kb_customers_save(
    body: Dict[str, Any],
    _: None = Security(_require_api_key)
) -> Dict[str, Any]:
    """
    Store or update customer data in the Knowledge Base.

    Requires X-API-Key header for authentication.
    Data is stored in GCS as JSONL format.

    Request body should contain:
    - name: str — customer full name
    - phone: str — Uruguayan phone (09XXXXXXX or +598XXXXXXXX)
    - address: str (optional)
    - city: str (optional)
    - department: str (optional)
    - notes: str (optional)

    Returns:
        Dict with customer_id, stored_at and GCS metadata
    """
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

    return {
        "ok": True,
        "customer_id": customer_id,
        "stored_at": envelope["received_at"],
        "gcs": gcs_result,
    }


@app.get("/kb/customers", status_code=200)
async def kb_customers_lookup(
    search: str = "",
    _: None = Security(_require_api_key)
) -> Dict[str, Any]:
    """
    Look up customer data from the Knowledge Base.

    Requires X-API-Key header for authentication.
    Returns a list of matching customers (GCS-backed JSONL store).

    Query parameters:
    - search: str — search term (name, phone, or address fragment)

    Returns:
        Dict with customers list and count
    """
    if len(search) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="search query must be at least 2 characters",
        )

    # GCS JSONL lookup: read today's and recent customer files and filter
    if not KB_GCS_BUCKET:
        return {"ok": True, "customers": [], "count": 0, "note": "KB_GCS_BUCKET not configured"}

    def _read_customers() -> list:
        client = _get_storage_client()
        # Limit scan to the most recent 30 daily files to avoid unbounded reads
        prefix = "kb/customers/daily/"
        blobs = sorted(
            client.list_blobs(KB_GCS_BUCKET, prefix=prefix),
            key=lambda b: b.name,
            reverse=True,
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
