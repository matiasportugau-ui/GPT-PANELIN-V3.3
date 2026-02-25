"""
Panelin Sheets Orchestrator – FastAPI service.

Endpoints:
  POST /v1/fill          – AI-planned write to a Google Sheet (allowlist-validated, idempotent).
  POST /v1/queue/process – Process PENDING jobs from a queue sheet.
  GET  /healthz          – Health check.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import google.auth
from google.cloud import firestore
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from fastapi import Depends, FastAPI, Header, HTTPException
from openai import OpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .models import (
    FillRequest,
    FillResponse,
    QueueProcessRequest,
    QueueProcessResponse,
    WritePlan,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config (env-driven)
# ---------------------------------------------------------------------------

def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name, default)
    return v if v not in ("", None) else None


@dataclass(frozen=True)
class Settings:
    env: str
    gcp_project_id: str
    log_level: str

    openai_model: str
    openai_api_key: Optional[str]
    openai_safety_identifier_prefix: str

    panelin_orch_api_key: Optional[str]
    api_key_header_name: str

    sheets_scopes: List[str]

    idempotency_backend: str
    firestore_collection: str
    firestore_database: str

    templates_dir: str
    queue_template_path: str


def load_settings() -> Settings:
    scopes_raw = _env(
        "SHEETS_SCOPES", "https://www.googleapis.com/auth/spreadsheets"
    ) or ""
    scopes = [s.strip() for s in scopes_raw.split(",") if s.strip()]

    return Settings(
        env=_env("ENV", "dev") or "dev",
        gcp_project_id=_env("GCP_PROJECT_ID", "") or "",
        log_level=_env("LOG_LEVEL", "INFO") or "INFO",
        openai_model=_env("OPENAI_MODEL", "gpt-4o-mini") or "gpt-4o-mini",
        openai_api_key=_env("OPENAI_API_KEY"),
        openai_safety_identifier_prefix=_env(
            "OPENAI_SAFETY_IDENTIFIER_PREFIX", "panelin-"
        )
        or "panelin-",
        panelin_orch_api_key=_env("PANELIN_ORCH_API_KEY"),
        api_key_header_name=_env("API_KEY_HEADER_NAME", "X-API-Key") or "X-API-Key",
        sheets_scopes=scopes,
        idempotency_backend=_env("IDEMPOTENCY_BACKEND", "memory") or "memory",
        firestore_collection=_env("FIRESTORE_COLLECTION", "panelin_sheet_jobs")
        or "panelin_sheet_jobs",
        firestore_database=_env("FIRESTORE_DATABASE", "(default)") or "(default)",
        templates_dir=_env("TEMPLATES_DIR", "templates/sheets") or "templates/sheets",
        queue_template_path=_env(
            "QUEUE_TEMPLATE_PATH", "templates/queue/queue_v1.example.json"
        )
        or "templates/queue/queue_v1.example.json",
    )


SETTINGS = load_settings()

# ---------------------------------------------------------------------------
# Auth: inbound API key
# ---------------------------------------------------------------------------


def require_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> None:
    expected = SETTINGS.panelin_orch_api_key
    if not expected:
        raise HTTPException(
            status_code=500, detail="PANELIN_ORCH_API_KEY no configurado."
        )
    if not x_api_key or not hmac.compare_digest(
        x_api_key.encode("utf-8"), expected.encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")


# ---------------------------------------------------------------------------
# Google Auth – ADC (Cloud Run) + fallback JSON_B64 (local/airgap)
# ---------------------------------------------------------------------------


def get_google_credentials(scopes: List[str]):
    b64 = _env("GOOGLE_SA_JSON_B64")
    if b64:
        info = json.loads(base64.b64decode(b64).decode("utf-8"))
        return service_account.Credentials.from_service_account_info(
            info, scopes=scopes
        )
    creds, _ = google.auth.default(scopes=scopes)
    return creds


def sheets_service():
    creds = get_google_credentials(SETTINGS.sheets_scopes)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


# ---------------------------------------------------------------------------
# Sheets API helpers (retries on transient errors)
# ---------------------------------------------------------------------------


def _is_retryable_http_error(exc: BaseException) -> bool:
    if not isinstance(exc, HttpError):
        return False
    status = getattr(getattr(exc, "resp", None), "status", None)
    return status in (429, 500, 502, 503, 504)


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=20),
    retry=retry_if_exception_type(HttpError),
    reraise=True,
)
def sheets_batch_get(
    spreadsheet_id: str, ranges: List[str]
) -> Dict[str, Any]:
    svc = sheets_service()
    return (
        svc.spreadsheets()
        .values()
        .batchGet(spreadsheetId=spreadsheet_id, ranges=ranges)
        .execute()
    )


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=20),
    retry=retry_if_exception_type(HttpError),
    reraise=True,
)
def sheets_batch_update(
    spreadsheet_id: str,
    data: List[Dict[str, Any]],
    value_input_option: str = "USER_ENTERED",
) -> Dict[str, Any]:
    svc = sheets_service()
    body = {
        "valueInputOption": value_input_option,
        "data": data,
        "includeValuesInResponse": False,
    }
    return (
        svc.spreadsheets()
        .values()
        .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
        .execute()
    )


# ---------------------------------------------------------------------------
# Idempotency (Firestore or in-memory)
# ---------------------------------------------------------------------------


class IdempotencyStore:
    def get_done(self, job_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def start(self, job_id: str, payload_hash: str) -> None:
        raise NotImplementedError

    def done(self, job_id: str, result: Dict[str, Any]) -> None:
        raise NotImplementedError

    def fail(self, job_id: str, error: str) -> None:
        raise NotImplementedError


class MemoryIdempotencyStore(IdempotencyStore):
    def __init__(self) -> None:
        self._db: Dict[str, Dict[str, Any]] = {}

    def get_done(self, job_id: str) -> Optional[Dict[str, Any]]:
        d = self._db.get(job_id)
        return d if d and d.get("status") == "DONE" else None

    def start(self, job_id: str, payload_hash: str) -> None:
        if job_id in self._db:
            return
        self._db[job_id] = {"status": "RUNNING", "payload_hash": payload_hash}

    def done(self, job_id: str, result: Dict[str, Any]) -> None:
        self._db[job_id] = {"status": "DONE", **result}

    def fail(self, job_id: str, error: str) -> None:
        self._db[job_id] = {"status": "ERROR", "error": error}


class FirestoreIdempotencyStore(IdempotencyStore):
    def __init__(
        self,
        project_id: str,
        collection: str,
        database: str = "(default)",
    ) -> None:
        self.client = firestore.Client(project=project_id, database=database)
        self.col = self.client.collection(collection)

    def get_done(self, job_id: str) -> Optional[Dict[str, Any]]:
        doc = self.col.document(job_id).get()
        if not doc.exists:
            return None
        d = doc.to_dict() or {}
        return d if d.get("status") == "DONE" else None

    def start(self, job_id: str, payload_hash: str) -> None:
        ref = self.col.document(job_id)

        @self.client.transaction()
        def txn_body(txn):
            snap = ref.get(transaction=txn)
            if snap.exists:
                return
            txn.set(ref, {"status": "RUNNING", "payload_hash": payload_hash})

        txn_body  # noqa: B018 – executed by decorator

    def done(self, job_id: str, result: Dict[str, Any]) -> None:
        self.col.document(job_id).set({"status": "DONE", **result}, merge=True)

    def fail(self, job_id: str, error: str) -> None:
        self.col.document(job_id).set(
            {"status": "ERROR", "error": error}, merge=True
        )


def _build_idempotency_store() -> IdempotencyStore:
    if SETTINGS.idempotency_backend == "firestore":
        return FirestoreIdempotencyStore(
            project_id=SETTINGS.gcp_project_id,
            collection=SETTINGS.firestore_collection,
            database=SETTINGS.firestore_database,
        )
    return MemoryIdempotencyStore()


IDEM_STORE: IdempotencyStore = _build_idempotency_store()

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


def load_template(template_id: str) -> Dict[str, Any]:
    path = os.path.join(SETTINGS.templates_dir, f"{template_id}.json")
    if not os.path.exists(path):
        raise HTTPException(
            status_code=400, detail=f"Template no encontrado: {template_id}"
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_write_ranges(
    writes: List[Dict[str, Any]], allowlist: List[str]
) -> None:
    allowed = set(allowlist)
    for w in writes:
        r = w.get("range")
        if r not in allowed:
            raise HTTPException(
                status_code=400, detail=f"Rango no permitido: {r}"
            )


def payload_hash(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------------------
# OpenAI: build write plan (Structured Outputs)
# ---------------------------------------------------------------------------

WRITEPLAN_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "job_id": {"type": "string"},
        "version": {"type": "string"},
        "writes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "range": {"type": "string"},
                    "values": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
                "required": ["range", "values"],
            },
        },
        "computed": {"type": "object"},
        "notes": {"type": "string"},
    },
    "required": ["job_id", "version", "writes", "computed", "notes"],
}


def build_write_plan(
    *,
    job_id: str,
    mapping: Dict[str, Any],
    sheet_snapshot: Dict[str, Any],
    payload: Dict[str, Any],
) -> WritePlan:
    if not SETTINGS.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY no configurado (usar Secret Manager en Cloud Run)."
        )

    client = OpenAI(api_key=SETTINGS.openai_api_key)

    template_context = {
        "template_id": mapping.get("template_id"),
        "sheet_name": mapping.get("sheet_name"),
        "writes_allowlist": mapping.get("writes_allowlist", []),
        "hints": mapping.get("hints", {}),
    }

    prompt_user = {
        "job_id": job_id,
        "template": template_context,
        "sheet_snapshot": sheet_snapshot,
        "payload": payload,
    }

    safety_id = SETTINGS.openai_safety_identifier_prefix + job_id[:32]

    resp = client.responses.create(
        model=SETTINGS.openai_model,
        input=[
            {
                "role": "system",
                "content": (
                    "Generá un plan de escritura para Google Sheets.\n"
                    "Reglas:\n"
                    "- SOLO podés usar rangos en writes_allowlist.\n"
                    "- NO inventes rangos.\n"
                    "- NO escribas fórmulas; solo valores.\n"
                    "- Si falta info, devolvé writes vacío y explicá en notes.\n"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(prompt_user, ensure_ascii=False),
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "panelin_sheet_writeplan",
                "schema": WRITEPLAN_SCHEMA,
                "strict": True,
            }
        },
    )

    out_text = getattr(resp, "output_text", None)
    if not out_text:
        raise RuntimeError(
            "OpenAI no devolvió output_text. Revisar versión del SDK."
        )
    data = json.loads(out_text)
    return WritePlan.model_validate(data)


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Panelin Sheets Orchestrator",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.get("/healthz")
def healthz():
    return {"ok": True, "env": SETTINGS.env}


@app.post("/v1/fill", response_model=FillResponse)
def fill(
    req: FillRequest, _auth: None = Depends(require_api_key)
):
    done = IDEM_STORE.get_done(req.job_id)
    if done:
        return FillResponse(
            job_id=req.job_id,
            status="DONE",
            applied=False,
            total_updated_cells=int(done.get("total_updated_cells", 0)),
            notes="Idempotencia: job_id ya aplicado.",
        )

    p_hash = payload_hash(req.payload)
    IDEM_STORE.start(req.job_id, p_hash)

    try:
        mapping = load_template(req.template_id)
        allowlist: List[str] = mapping.get("writes_allowlist", [])
        read_ranges: List[str] = mapping.get("read_ranges", [])

        snapshot = (
            sheets_batch_get(req.spreadsheet_id, read_ranges)
            if read_ranges
            else {"valueRanges": []}
        )

        plan = build_write_plan(
            job_id=req.job_id,
            mapping=mapping,
            sheet_snapshot=snapshot,
            payload=req.payload,
        )

        writes = [w.model_dump() for w in plan.writes]
        validate_write_ranges(writes, allowlist)

        if req.dry_run:
            IDEM_STORE.done(req.job_id, {"total_updated_cells": 0, "dry_run": True})
            return FillResponse(
                job_id=req.job_id,
                status="DRY_RUN",
                applied=False,
                writes_count=len(writes),
                total_updated_cells=0,
                notes=plan.notes,
                write_plan=plan,
            )

        result = sheets_batch_update(req.spreadsheet_id, writes)
        total_cells = int(result.get("totalUpdatedCells", 0))

        IDEM_STORE.done(req.job_id, {"total_updated_cells": total_cells})
        return FillResponse(
            job_id=req.job_id,
            status="DONE",
            applied=True,
            writes_count=len(writes),
            total_updated_cells=total_cells,
            notes=plan.notes,
        )

    except HTTPException:
        raise
    except Exception as e:
        IDEM_STORE.fail(req.job_id, str(e))
        raise HTTPException(status_code=500, detail=f"fill_failed: {e}")


@app.post("/v1/queue/process", response_model=QueueProcessResponse)
def process_queue(
    req: QueueProcessRequest, _auth: None = Depends(require_api_key)
):
    with open(SETTINGS.queue_template_path, "r", encoding="utf-8") as f:
        qcfg = json.load(f)["queue"]

    q_spreadsheet_id: str = qcfg["spreadsheet_id"]
    sheet_name: str = qcfg["sheet_name"]
    start_row = int(qcfg.get("start_row", 2))
    read_range = f"{sheet_name}!A{start_row}:F"

    batch = sheets_batch_get(q_spreadsheet_id, [read_range])
    rows = (batch.get("valueRanges") or [{}])[0].get("values") or []

    processed = succeeded = failed = 0
    status_writes: List[Dict[str, Any]] = []

    for idx, row in enumerate(rows):
        if processed >= req.limit:
            break

        job_id = row[0] if len(row) > 0 else ""
        status = row[1] if len(row) > 1 else ""
        template_id = row[2] if len(row) > 2 else ""
        target_sid = row[3] if len(row) > 3 else ""
        payload_json = row[4] if len(row) > 4 else ""

        if not job_id or status != qcfg["status_values"]["pending"]:
            continue

        processed += 1
        absolute_row = start_row + idx
        status_writes.append(
            {
                "range": f"{sheet_name}!B{absolute_row}",
                "values": [[qcfg["status_values"]["running"]]],
            }
        )

        try:
            payload_data = json.loads(payload_json) if payload_json else {}
            fill_req = FillRequest(
                job_id=job_id,
                template_id=template_id,
                spreadsheet_id=target_sid,
                payload=payload_data,
                dry_run=False,
            )
            fill(fill_req, _auth=None)
            succeeded += 1
            status_writes.append(
                {
                    "range": f"{sheet_name}!B{absolute_row}",
                    "values": [[qcfg["status_values"]["done"]]],
                }
            )
            status_writes.append(
                {
                    "range": f"{sheet_name}!F{absolute_row}",
                    "values": [
                        [json.dumps({"ok": True}, ensure_ascii=False)]
                    ],
                }
            )
        except Exception as e:
            failed += 1
            logger.exception("Queue job %s failed", job_id)
            status_writes.append(
                {
                    "range": f"{sheet_name}!B{absolute_row}",
                    "values": [[qcfg["status_values"]["error"]]],
                }
            )
            status_writes.append(
                {
                    "range": f"{sheet_name}!F{absolute_row}",
                    "values": [
                        [
                            json.dumps(
                                {"ok": False, "error": str(e)},
                                ensure_ascii=False,
                            )
                        ]
                    ],
                }
            )

    if status_writes:
        sheets_batch_update(q_spreadsheet_id, status_writes)

    return QueueProcessResponse(
        processed=processed, succeeded=succeeded, failed=failed
    )
