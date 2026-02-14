"""Handler for the report_error MCP tool.

Appends correction entries to corrections_log.json for tracking KB errors.
Each correction gets a unique ID and timestamp.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

KB_ROOT = Path(__file__).resolve().parent.parent.parent
CORRECTIONS_FILE = KB_ROOT / "corrections_log.json"


def _load_corrections() -> dict[str, Any]:
    with open(CORRECTIONS_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save_corrections(data: dict[str, Any]) -> None:
    with open(CORRECTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _next_id(corrections: list[dict[str, Any]]) -> str:
    if not corrections:
        return "COR-001"
    last_num = 0
    for c in corrections:
        cid = c.get("id", "COR-000")
        try:
            num = int(cid.split("-")[1])
            last_num = max(last_num, num)
        except (IndexError, ValueError):
            # Ignore malformed or unexpected ID formats; they don't affect next-ID generation.
            pass
    return f"COR-{last_num + 1:03d}"


async def handle_report_error(arguments: dict[str, Any]) -> dict[str, Any]:
    """Log a KB error correction and return v1 contract envelope."""
    kb_file = arguments.get("kb_file")
    field = arguments.get("field")
    wrong_value = arguments.get("wrong_value")
    correct_value = arguments.get("correct_value")
    source = arguments.get("source", "user_correction")
    notes = arguments.get("notes", "")

    # Validate required parameters
    if (
        kb_file is None
        or field is None
        or wrong_value is None
        or correct_value is None
    ):
        return {
            "ok": False,
            "contract_version": "v1",
            "error": {
                "code": "INVALID_PARAMETERS",
                "message": "kb_file, field, wrong_value, and correct_value are required",
                "details": {
                    "kb_file": kb_file is not None,
                    "field": field is not None,
                    "wrong_value": wrong_value is not None,
                    "correct_value": correct_value is not None
                }
            }
        }

    try:
        data = _load_corrections()
        corrections = data.get("corrections", [])

        entry = {
            "id": _next_id(corrections),
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "kb_file": kb_file,
            "field": field,
            "wrong_value": wrong_value,
            "correct_value": correct_value,
            "source": source,
            "notes": notes,
            "status": "pending",
            "applied_date": None,
        }

        corrections.append(entry)
        data["corrections"] = corrections
        _save_corrections(data)

        return {
            "ok": True,
            "contract_version": "v1",
            "message": f"Correction {entry['id']} logged successfully",
            "correction": entry,
            "total_pending": sum(1 for c in corrections if c.get("status") == "pending"),
        }
    
    except Exception as e:
        return {
            "ok": False,
            "contract_version": "v1",
            "error": {
                "code": "INTERNAL_ERROR",
                "message": f"Failed to log correction: {str(e)}",
                "details": {"exception_type": type(e).__name__}
            }
        }
