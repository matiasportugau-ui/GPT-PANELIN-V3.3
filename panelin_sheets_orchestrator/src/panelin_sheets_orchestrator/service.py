"""
Panelin Sheets Orchestrator – FastAPI service.

Endpoints:
  GET  /healthz              – Health check.
  POST /v1/fill              – AI-planned write to a Google Sheet (allowlist-validated, idempotent).
  POST /v1/queue/process     – Process PENDING jobs from a queue sheet.
  POST /v1/read              – Read ranges from a Google Sheet.
  POST /v1/validate          – Validate dimensions, autoportancia, and compute BOM.
  GET  /v1/templates         – List available templates.
  GET  /v1/templates/{id}    – Get a specific template.
  GET  /v1/jobs/{job_id}     – Get job status (idempotency lookup).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Path
from google.cloud import firestore

from .audit import (
    audit_fill_request,
    audit_fill_result,
    audit_queue_batch,
    audit_validation_failure,
)
from .config import Settings, load_settings
from .models import (
    FillRequest,
    FillResponse,
    JobStatusResponse,
    QueueProcessRequest,
    QueueProcessResponse,
    ReadRequest,
    ReadResponse,
    TemplateInfo,
    TemplateListResponse,
    ValidateRequest,
    ValidateResponse,
)
from .openai_planner import build_write_plan
from .sheets_client import SheetsClient
from .validators import (
    compute_bom_summary,
    validate_write_plan_values,
)

logger = logging.getLogger("panelin.sheets.service")

# ---------------------------------------------------------------------------
# Settings (module-level, reloadable for tests)
# ---------------------------------------------------------------------------

SETTINGS: Settings = load_settings()

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
# Sheets client (lazy singleton)
# ---------------------------------------------------------------------------

_sheets_client: Optional[SheetsClient] = None


def get_sheets_client() -> SheetsClient:
    global _sheets_client
    if _sheets_client is None:
        _sheets_client = SheetsClient(SETTINGS)
    return _sheets_client


# ---------------------------------------------------------------------------
# Idempotency (Firestore or in-memory)
# ---------------------------------------------------------------------------


class IdempotencyStore:
    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def get_done(self, job_id: str) -> Optional[Dict[str, Any]]:
        d = self.get(job_id)
        return d if d and d.get("status") == "DONE" else None

    def start(self, job_id: str, payload_hash: str) -> None:
        raise NotImplementedError

    def done(self, job_id: str, result: Dict[str, Any]) -> None:
        raise NotImplementedError

    def fail(self, job_id: str, error: str) -> None:
        raise NotImplementedError


class MemoryIdempotencyStore(IdempotencyStore):
    def __init__(self) -> None:
        self._db: Dict[str, Dict[str, Any]] = {}

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._db.get(job_id)

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

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        doc = self.col.document(job_id).get()
        if not doc.exists:
            return None
        return doc.to_dict()

    def start(self, job_id: str, payload_hash: str) -> None:
        ref = self.col.document(job_id)

        @self.client.transaction()
        def txn_body(txn):
            snap = ref.get(transaction=txn)
            if snap.exists:
                return
            txn.set(ref, {"status": "RUNNING", "payload_hash": payload_hash})

        txn_body  # noqa: B018

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


def list_templates() -> List[Dict[str, Any]]:
    templates_dir = SETTINGS.templates_dir
    if not os.path.isdir(templates_dir):
        return []
    result = []
    for fname in sorted(os.listdir(templates_dir)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(templates_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            result.append(data)
        except Exception:
            logger.warning("Failed to load template %s", fpath, exc_info=True)
    return result


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
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Panelin Sheets Orchestrator",
    version="0.2.0",
    description=(
        "Microservicio Cloud Run para automatizar el llenado de planillas "
        "Google Sheets en Panelin v3.3, usando OpenAI Structured Outputs "
        "con validación de allowlist y reglas de negocio."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── Health ─────────────────────────────────────────────────────────────


@app.get("/healthz")
def healthz():
    return {
        "ok": True,
        "env": SETTINGS.env,
        "version": SETTINGS.service_version,
    }


# ── POST /v1/fill ──────────────────────────────────────────────────────


@app.post("/v1/fill", response_model=FillResponse)
def fill(
    req: FillRequest, _auth: None = Depends(require_api_key)
):
    audit_fill_request(
        job_id=req.job_id,
        template_id=req.template_id,
        spreadsheet_id=req.spreadsheet_id,
        dry_run=req.dry_run,
        payload_keys=list(req.payload.keys()),
    )

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
        hints: Dict[str, Any] = mapping.get("hints", {})

        sheets = get_sheets_client()
        snapshot = (
            sheets.batch_get(req.spreadsheet_id, read_ranges, job_id=req.job_id)
            if read_ranges
            else {"valueRanges": []}
        )

        bom_data = None
        payload_data = req.payload
        if all(k in payload_data for k in ("product_family", "thickness_mm", "length_m", "width_m")):
            bom_result = compute_bom_summary(
                product_family=str(payload_data["product_family"]),
                thickness_mm=int(payload_data["thickness_mm"]),
                length_m=float(payload_data["length_m"]),
                width_m=float(payload_data["width_m"]),
                usage=str(payload_data.get("usage", "techo")),
                structure=str(payload_data.get("structure", "metal")),
                safety_margin=SETTINGS.default_safety_margin,
            )
            bom_data = bom_result.details
            if not bom_result.valid:
                for err in bom_result.errors:
                    audit_validation_failure(job_id=req.job_id, rule="bom", detail=err)

        plan = build_write_plan(
            settings=SETTINGS,
            job_id=req.job_id,
            mapping=mapping,
            sheet_snapshot=snapshot,
            payload=payload_data,
            bom_summary=bom_data,
        )

        writes = [w.model_dump() for w in plan.writes]
        validate_write_ranges(writes, allowlist)

        value_validation = validate_write_plan_values(writes, hints)
        if not value_validation.valid:
            for err in value_validation.errors:
                audit_validation_failure(job_id=req.job_id, rule="value", detail=err)
            IDEM_STORE.fail(req.job_id, "; ".join(value_validation.errors))
            raise HTTPException(
                status_code=400,
                detail=f"Validación de valores falló: {'; '.join(value_validation.errors)}",
            )

        validation_info = None
        if value_validation.warnings or (bom_data and not all(
            k in bom_data for k in ("panels_needed",)
        )):
            validation_info = {
                "value_warnings": value_validation.warnings,
                "bom": bom_data,
            }

        if req.dry_run:
            IDEM_STORE.done(req.job_id, {"total_updated_cells": 0, "dry_run": True})
            resp = FillResponse(
                job_id=req.job_id,
                status="DRY_RUN",
                applied=False,
                writes_count=len(writes),
                total_updated_cells=0,
                notes=plan.notes,
                write_plan=plan,
                validation=validation_info,
            )
            audit_fill_result(
                job_id=req.job_id,
                status="DRY_RUN",
                writes_count=len(writes),
                total_updated_cells=0,
                notes=plan.notes,
            )
            return resp

        result = sheets.batch_update(
            req.spreadsheet_id, writes, job_id=req.job_id
        )
        total_cells = int(result.get("totalUpdatedCells", 0))

        IDEM_STORE.done(req.job_id, {"total_updated_cells": total_cells})
        audit_fill_result(
            job_id=req.job_id,
            status="DONE",
            writes_count=len(writes),
            total_updated_cells=total_cells,
            notes=plan.notes,
        )
        return FillResponse(
            job_id=req.job_id,
            status="DONE",
            applied=True,
            writes_count=len(writes),
            total_updated_cells=total_cells,
            notes=plan.notes,
            validation=validation_info,
        )

    except HTTPException:
        raise
    except Exception as e:
        IDEM_STORE.fail(req.job_id, str(e))
        logger.exception("fill failed for job %s", req.job_id)
        raise HTTPException(status_code=500, detail=f"fill_failed: {e}")


# ── POST /v1/queue/process ─────────────────────────────────────────────


@app.post("/v1/queue/process", response_model=QueueProcessResponse)
def process_queue(
    req: QueueProcessRequest, _auth: None = Depends(require_api_key)
):
    t0 = time.monotonic()

    with open(SETTINGS.queue_template_path, "r", encoding="utf-8") as f:
        qcfg = json.load(f)["queue"]

    q_spreadsheet_id: str = qcfg["spreadsheet_id"]
    sheet_name: str = qcfg["sheet_name"]
    start_row = int(qcfg.get("start_row", 2))
    read_range = f"{sheet_name}!A{start_row}:F"

    sheets = get_sheets_client()
    batch = sheets.batch_get(
        q_spreadsheet_id, [read_range], job_id="queue-batch", use_cache=False
    )
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
        sheets.batch_update(q_spreadsheet_id, status_writes, job_id="queue-batch")

    elapsed = round((time.monotonic() - t0) * 1000, 2)
    audit_queue_batch(
        processed=processed,
        succeeded=succeeded,
        failed=failed,
        duration_ms=elapsed,
    )

    return QueueProcessResponse(
        processed=processed,
        succeeded=succeeded,
        failed=failed,
        duration_ms=elapsed,
    )


# ── POST /v1/read ──────────────────────────────────────────────────────


@app.post("/v1/read", response_model=ReadResponse)
def read_ranges(
    req: ReadRequest, _auth: None = Depends(require_api_key)
):
    """Read specified ranges from a Google Sheet."""
    sheets = get_sheets_client()
    result = sheets.batch_get(
        req.spreadsheet_id, req.ranges, job_id="read-request"
    )
    return ReadResponse(
        spreadsheet_id=req.spreadsheet_id,
        value_ranges=result.get("valueRanges", []),
    )


# ── POST /v1/validate ──────────────────────────────────────────────────


@app.post("/v1/validate", response_model=ValidateResponse)
def validate(
    req: ValidateRequest, _auth: None = Depends(require_api_key)
):
    """
    Validate product dimensions, autoportancia, and compute BOM quantities.
    Does not require a spreadsheet or OpenAI – pure deterministic calculation.
    """
    result = compute_bom_summary(
        product_family=req.product_family,
        thickness_mm=req.thickness_mm,
        length_m=req.length_m,
        width_m=req.width_m,
        usage=req.usage,
        structure=req.structure,
        safety_margin=req.safety_margin,
    )

    return ValidateResponse(
        valid=result.valid,
        errors=result.errors,
        warnings=result.warnings,
        bom_summary=result.details,
    )


# ── GET /v1/templates ──────────────────────────────────────────────────


@app.get("/v1/templates", response_model=TemplateListResponse)
def get_templates(_auth: None = Depends(require_api_key)):
    """List all available sheet templates."""
    templates = list_templates()
    items = [
        TemplateInfo(
            template_id=t.get("template_id", ""),
            sheet_name=t.get("sheet_name", ""),
            writes_allowlist=t.get("writes_allowlist", []),
            read_ranges=t.get("read_ranges", []),
            hints=t.get("hints", {}),
        )
        for t in templates
    ]
    return TemplateListResponse(templates=items, count=len(items))


@app.get("/v1/templates/{template_id}", response_model=TemplateInfo)
def get_template(
    template_id: str = Path(...), _auth: None = Depends(require_api_key)
):
    """Get a specific template by ID."""
    t = load_template(template_id)
    return TemplateInfo(
        template_id=t.get("template_id", template_id),
        sheet_name=t.get("sheet_name", ""),
        writes_allowlist=t.get("writes_allowlist", []),
        read_ranges=t.get("read_ranges", []),
        hints=t.get("hints", {}),
    )


# ── GET /v1/jobs/{job_id} ─────────────────────────────────────────────


@app.get("/v1/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: str = Path(...), _auth: None = Depends(require_api_key)
):
    """Query the status of a fill job (idempotency store lookup)."""
    record = IDEM_STORE.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} no encontrado.")

    return JobStatusResponse(
        job_id=job_id,
        status=record.get("status", "UNKNOWN"),
        payload_hash=record.get("payload_hash"),
        total_updated_cells=record.get("total_updated_cells"),
        error=record.get("error"),
    )
