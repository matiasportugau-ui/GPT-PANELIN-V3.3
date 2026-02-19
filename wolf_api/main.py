"""
Wolf API - FastAPI Backend for Panelin Knowledge Base
Implements POST /kb/conversations with GCS persistence
"""

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

# FastAPI app configuration
app = FastAPI(
    title="Panelin Wolf API",
    description="Knowledge Base API for Panelin GPT Assistant",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

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

    # Ensure JSONL is one line + newline
    jsonl_line = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"

    if KB_GCS_MODE == "per_event_jsonl":
        # One object per event (still a valid JSONL line file)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        obj = f"{KB_GCS_PREFIX}/events/{ts}-{uuid.uuid4().hex}.jsonl"
        client = _get_storage_client()
        bucket = client.bucket(KB_GCS_BUCKET)
        blob = bucket.blob(obj)
        blob.upload_from_string(jsonl_line, content_type="application/x-ndjson")
        return {"ok": True, "bucket": KB_GCS_BUCKET, "object": obj, "mode": KB_GCS_MODE}

    # Default: daily JSONL append via compose
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    destination = f"{KB_GCS_PREFIX}/daily/{day}.jsonl"
    result = _compose_append_jsonl_line(
        bucket_name=KB_GCS_BUCKET,
        destination_blob_name=destination,
        jsonl_line=jsonl_line,
        tmp_prefix=KB_GCS_PREFIX,
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
        "version": "2.1.0",
        "status": "operational"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/ready")
async def ready():
    """Readiness check endpoint."""
    return {"status": "ready"}


@app.post("/kb/conversations", status_code=200)
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


# Additional placeholder endpoints for future KB write operations
# (register_correction, save_customer, lookup_customer)
# These can be implemented following the same pattern as kb_conversations
