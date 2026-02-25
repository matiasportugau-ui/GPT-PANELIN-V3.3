"""
GPT Panel v3.4 - Knowledge Base Self-Learning Writer Service
=============================================================

Allows the model to write new entries to KB with human approval workflow.
Persists entries to a JSONL file for durability across restarts.

Fixes applied:
- File-based persistence (JSONL) instead of in-memory only
- API key authentication on mutation endpoints
- Proper entry retrieval from persistent storage
"""

import json
import logging
import os
import hmac
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

STORAGE_DIR = Path(os.environ.get("KB_STORAGE_DIR", "kb_self_learning/data"))
ENTRIES_FILE = STORAGE_DIR / "kb_entries.jsonl"
API_KEY_ENV = "KB_SELF_LEARNING_API_KEY"


def _ensure_storage():
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def _verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    """Dependency: verify API key for mutation endpoints."""
    expected = os.environ.get(API_KEY_ENV, "")
    if not expected:
        logger.warning("KB_SELF_LEARNING_API_KEY not set; auth disabled in dev mode")
        return True
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    if not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True


def _append_entry(entry_data: dict):
    """Append an entry to the JSONL storage file."""
    _ensure_storage()
    with open(ENTRIES_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry_data, ensure_ascii=False) + "\n")


def _load_all_entries() -> list[dict]:
    """Load all entries from JSONL storage."""
    if not ENTRIES_FILE.exists():
        return []
    entries = []
    with open(ENTRIES_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(f"Skipping malformed JSONL line: {line[:80]}")
    return entries


def _update_entry(entry_id: str, updates: dict):
    """Update an entry in-place by rewriting the JSONL file."""
    entries = _load_all_entries()
    updated = False
    for entry in entries:
        if entry.get("id") == entry_id:
            entry.update(updates)
            updated = True
            break
    if updated:
        _ensure_storage()
        with open(ENTRIES_FILE, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return updated


class KBEntry(BaseModel):
    topic: str = Field(..., min_length=2)
    content: str = Field(..., min_length=10)
    confidence_score: float = Field(default=0.85, ge=0.0, le=1.0)
    source: str = "self_learning"
    tags: List[str] = []
    metadata: dict = {}


class ApprovalRequest(BaseModel):
    kb_entry_id: str
    approved: bool
    reviewer_notes: Optional[str] = None
    reviewed_by: str


router = APIRouter(prefix="/api/v3.4/kb", tags=["kb_self_learning"])


@router.post("/write-entry", response_model=dict)
async def submit_kb_entry(entry: KBEntry, _auth=Depends(_verify_api_key)):
    """
    Submit a new KB entry for approval.
    Persists to JSONL file for durability.
    """
    try:
        entry_id = f"kb_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}"

        kb_data = {
            "id": entry_id,
            "topic": entry.topic,
            "content": entry.content,
            "confidence_score": entry.confidence_score,
            "source": entry.source,
            "tags": entry.tags,
            "metadata": entry.metadata,
            "status": "pending_approval",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "requires_approval": True,
        }

        _append_entry(kb_data)
        logger.info(f"KB entry submitted and persisted: {entry_id}")

        return {
            "status": "success",
            "entry_id": entry_id,
            "message": "KB entry submitted for human approval",
            "data": kb_data,
        }
    except Exception as e:
        logger.error(f"Error submitting KB entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve-entry")
async def approve_kb_entry(approval: ApprovalRequest, _auth=Depends(_verify_api_key)):
    """Approve or reject a KB entry. Persists decision to storage."""
    try:
        updates = {
            "reviewed_by": approval.reviewed_by,
            "reviewer_notes": approval.reviewer_notes,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }

        if approval.approved:
            updates["status"] = "approved"
            updates["approved_at"] = updates["reviewed_at"]
        else:
            updates["status"] = "rejected"
            updates["rejected_at"] = updates["reviewed_at"]

        found = _update_entry(approval.kb_entry_id, updates)
        if not found:
            raise HTTPException(status_code=404, detail=f"Entry {approval.kb_entry_id} not found")

        status = "approved" if approval.approved else "rejected"
        logger.info(f"KB entry {status}: {approval.kb_entry_id} by {approval.reviewed_by}")

        return {
            "status": status,
            "entry_id": approval.kb_entry_id,
            "message": f"Entry {status}" + (f": {approval.reviewer_notes}" if approval.reviewer_notes else ""),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving KB entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending-approvals")
async def get_pending_approvals():
    """Get all KB entries pending human approval (from persistent storage)."""
    try:
        entries = _load_all_entries()
        pending = [e for e in entries if e.get("status") == "pending_approval"]
        return {
            "status": "success",
            "pending_entries": pending,
            "count": len(pending),
        }
    except Exception as e:
        logger.error(f"Error fetching pending approvals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entry/{entry_id}")
async def get_kb_entry(entry_id: str):
    """Retrieve a specific KB entry from persistent storage."""
    try:
        entries = _load_all_entries()
        for entry in entries:
            if entry.get("id") == entry_id:
                return {"status": "success", "entry_id": entry_id, "data": entry}
        raise HTTPException(status_code=404, detail=f"Entry {entry_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving KB entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entries")
async def list_entries(status: Optional[str] = None, limit: int = 100):
    """List KB entries with optional status filter."""
    try:
        entries = _load_all_entries()
        if status:
            entries = [e for e in entries if e.get("status") == status]
        return {
            "status": "success",
            "entries": entries[-limit:],
            "total": len(entries),
        }
    except Exception as e:
        logger.error(f"Error listing entries: {e}")
        raise HTTPException(status_code=500, detail=str(e))
