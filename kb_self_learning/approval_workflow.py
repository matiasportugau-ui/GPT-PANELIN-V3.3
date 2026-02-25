"""
GPT Panel v3.4 - Knowledge Base Approval Workflow
===================================================

Manages the human approval process for KB entries.
Persists state to a JSONL file for durability across restarts.

Fixes applied:
- File-based persistence instead of in-memory dicts
- API key authentication on mutation endpoints
- Proper error handling for missing entries
"""

import json
import logging
import os
import hmac
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from enum import Enum

logger = logging.getLogger(__name__)

STORAGE_DIR = Path(os.environ.get("KB_STORAGE_DIR", "kb_self_learning/data"))
WORKFLOW_FILE = STORAGE_DIR / "approval_workflow.jsonl"
API_KEY_ENV = "KB_SELF_LEARNING_API_KEY"


def _ensure_storage():
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def _verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    expected = os.environ.get(API_KEY_ENV, "")
    if not expected:
        logger.warning("KB_SELF_LEARNING_API_KEY not set; auth disabled in dev mode")
        return True
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    if not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True


def _append_event(event: dict):
    _ensure_storage()
    with open(WORKFLOW_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _load_events() -> list[dict]:
    if not WORKFLOW_FILE.exists():
        return []
    events = []
    with open(WORKFLOW_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return events


def _rebuild_state() -> tuple[dict, list]:
    """Rebuild pending queue and history from event log."""
    events = _load_events()
    pending = {}
    history = []

    for ev in events:
        etype = ev.get("event_type")
        eid = ev.get("entry_id")

        if etype == "submitted":
            pending[eid] = ev
        elif etype in ("approved", "rejected"):
            if eid in pending:
                merged = {**pending.pop(eid), **ev}
                history.append(merged)
            else:
                history.append(ev)
        elif etype == "revision_requested" and eid in pending:
            pending[eid].update(ev)

    return pending, history


class ApprovalStatus(str, Enum):
    PENDING = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


router = APIRouter(prefix="/api/v3.4/approval", tags=["approval_workflow"])


@router.post("/submit/{entry_id}")
async def submit_for_approval(
    entry_id: str,
    submitter: str,
    entry_data: dict = None,
    _auth=Depends(_verify_api_key),
):
    """Submit an entry to the approval queue."""
    try:
        event = {
            "event_type": "submitted",
            "entry_id": entry_id,
            "entry_data": entry_data or {},
            "status": ApprovalStatus.PENDING,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "submitted_by": submitter,
        }
        _append_event(event)
        logger.info(f"Entry {entry_id} submitted for approval by {submitter}")
        return {"status": "submitted", "entry_id": entry_id}
    except Exception as e:
        logger.error(f"Error submitting entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve/{entry_id}")
async def approve_kb_entry(
    entry_id: str,
    reviewer: str,
    notes: Optional[str] = None,
    _auth=Depends(_verify_api_key),
):
    """Approve a KB entry."""
    try:
        pending, _ = _rebuild_state()
        if entry_id not in pending:
            raise HTTPException(status_code=404, detail=f"Entry {entry_id} not in pending queue")

        event = {
            "event_type": "approved",
            "entry_id": entry_id,
            "status": ApprovalStatus.APPROVED,
            "reviewer": reviewer,
            "notes": notes,
            "approved_at": datetime.now(timezone.utc).isoformat(),
        }
        _append_event(event)
        logger.info(f"Entry {entry_id} approved by {reviewer}")
        return {"status": "approved", "entry_id": entry_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reject/{entry_id}")
async def reject_kb_entry(
    entry_id: str,
    reviewer: str,
    reason: str,
    _auth=Depends(_verify_api_key),
):
    """Reject a KB entry."""
    try:
        pending, _ = _rebuild_state()
        if entry_id not in pending:
            raise HTTPException(status_code=404, detail=f"Entry {entry_id} not in pending queue")

        event = {
            "event_type": "rejected",
            "entry_id": entry_id,
            "status": ApprovalStatus.REJECTED,
            "reviewer": reviewer,
            "reason": reason,
            "rejected_at": datetime.now(timezone.utc).isoformat(),
        }
        _append_event(event)
        logger.info(f"Entry {entry_id} rejected by {reviewer}: {reason}")
        return {"status": "rejected", "entry_id": entry_id, "reason": reason}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/revision/{entry_id}")
async def request_revision(
    entry_id: str,
    reviewer: str,
    revision_notes: str,
    _auth=Depends(_verify_api_key),
):
    """Request revision for an entry."""
    try:
        pending, _ = _rebuild_state()
        if entry_id not in pending:
            raise HTTPException(status_code=404, detail=f"Entry {entry_id} not in pending queue")

        event = {
            "event_type": "revision_requested",
            "entry_id": entry_id,
            "status": ApprovalStatus.NEEDS_REVISION,
            "reviewer": reviewer,
            "revision_notes": revision_notes,
            "requested_at": datetime.now(timezone.utc).isoformat(),
        }
        _append_event(event)
        logger.info(f"Entry {entry_id} marked for revision by {reviewer}")
        return {"status": "revision_requested", "entry_id": entry_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error requesting revision: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending")
async def get_pending_approvals():
    """Get all pending KB entries waiting for approval."""
    try:
        pending, _ = _rebuild_state()
        entries = list(pending.values())
        return {
            "status": "success",
            "pending_count": len(entries),
            "entries": entries,
        }
    except Exception as e:
        logger.error(f"Error getting pending approvals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entry/{entry_id}")
async def get_entry_status(entry_id: str):
    """Get status of a specific entry."""
    try:
        pending, history = _rebuild_state()

        if entry_id in pending:
            return {"status": "in_queue", "data": pending[entry_id]}

        for h in history:
            if h.get("entry_id") == entry_id:
                return {"status": "processed", "data": h}

        raise HTTPException(status_code=404, detail=f"Entry {entry_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting entry status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_approval_stats():
    """Get approval workflow statistics."""
    try:
        pending, history = _rebuild_state()
        approved = sum(1 for h in history if h.get("status") == ApprovalStatus.APPROVED)
        rejected = sum(1 for h in history if h.get("status") == ApprovalStatus.REJECTED)
        decided = approved + rejected

        return {
            "status": "success",
            "stats": {
                "approved": approved,
                "rejected": rejected,
                "pending": len(pending),
                "total_processed": len(history),
                "approval_rate": round(approved / decided, 3) if decided else 0,
            },
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
