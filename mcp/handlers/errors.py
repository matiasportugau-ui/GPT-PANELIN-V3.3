"""Handler for the report_error MCP tool.

Appends correction entries to corrections_log.json for tracking KB errors.
Each correction gets a unique ID and timestamp.
Enhanced for verbal interaction scenarios with better validation and error messages.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp_tools.contracts import CONTRACT_VERSION

logger = logging.getLogger(__name__)

KB_ROOT = Path(__file__).resolve().parent.parent.parent
CORRECTIONS_FILE = KB_ROOT / "corrections_log.json"

# Allowed KB files (same whitelist as governance.py)
ALLOWED_KB_FILES = [
    "bromyros_pricing_master.json",
    "bromyros_pricing_gpt_optimized.json",
    "accessories_catalog.json",
    "bom_rules.json",
    "shopify_catalog_v1.json",
    "BMC_Base_Conocimiento_GPT-2.json",
    "perfileria_index.json",
]

# Valid correction sources
VALID_SOURCES = [
    "user_correction",
    "validation_check",
    "audit",
    "web_verification",
    "conversation",
]


def _load_corrections() -> dict[str, Any]:
    """Load corrections log safely."""
    try:
        with open(CORRECTIONS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # Initialize empty corrections log if it doesn't exist
        return {"version": "1.0", "corrections": []}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse corrections_log.json: {e}")
        raise


def _save_corrections(data: dict[str, Any]) -> None:
    """Save corrections log safely."""
    with open(CORRECTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _next_id(corrections: list[dict[str, Any]]) -> str:
    """Generate the next correction ID."""
    if not corrections:
        return "COR-001"
    last_num = 0
    for c in corrections:
        cid = c.get("id", "COR-000")
        try:
            num = int(cid.split("-")[1])
            last_num = max(last_num, num)
        except (IndexError, ValueError):
            # Ignore malformed or unexpected ID formats
            pass
    return f"COR-{last_num + 1:03d}"


async def handle_report_error(
    arguments: dict[str, Any],
    legacy_format: bool = False,
) -> dict[str, Any]:
    """Log a KB error correction with enhanced validation.

    Args:
        arguments: Tool arguments containing kb_file, field, wrong_value,
            correct_value, source, and notes
        legacy_format: If True, return legacy format for
            backwards compatibility

    Returns:
        v1 contract envelope with correction details
    """
    kb_file = arguments.get("kb_file")
    field = arguments.get("field")
    wrong_value = arguments.get("wrong_value")
    correct_value = arguments.get("correct_value")
    source = arguments.get("source", "user_correction")
    notes = arguments.get("notes", "")

    # Validate required fields
    if kb_file is None or field is None or wrong_value is None or correct_value is None:
        if legacy_format:
            return {"error": "kb_file, field, wrong_value, and correct_value are required"}
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": "MISSING_REQUIRED_FIELDS",
                "message": "kb_file, field, wrong_value, and correct_value are required",
                "details": {
                    "missing_fields": [
                        name
                        for name, value in {
                            "kb_file": kb_file,
                            "field": field,
                            "wrong_value": wrong_value,
                            "correct_value": correct_value,
                        }.items()
                        if value is None
                    ],
                },
            },
        }

    # Validate kb_file against whitelist
    kb_file_clean = str(kb_file).replace("/", "").replace("\\", "").replace("..", "")
    if kb_file_clean not in ALLOWED_KB_FILES:
        if legacy_format:
            return {"error": f"Invalid kb_file. Must be one of: {', '.join(ALLOWED_KB_FILES)}"}
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": "INVALID_KB_FILE",
                "message": f"Invalid kb_file. Must be one of: {', '.join(ALLOWED_KB_FILES)}",
                "details": {
                    "provided": kb_file,
                    "allowed": ALLOWED_KB_FILES,
                },
            },
        }

    # Validate source value
    if source not in VALID_SOURCES:
        logger.warning(f"Invalid source '{source}', defaulting to 'user_correction'")
        source = "user_correction"

    # Validate field format (basic check)
    if not isinstance(field, str) or len(field) == 0:
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": "INVALID_FIELD",
                "message": "field must be a non-empty string",
            },
        }

    try:
        data = _load_corrections()
        corrections = data.get("corrections", [])

        entry = {
            "id": _next_id(corrections),
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "kb_file": kb_file_clean,
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

        if legacy_format:
            return {
                "message": f"Correction {entry['id']} logged successfully",
                "correction": entry,
                "total_pending": sum(1 for c in corrections if c.get("status") == "pending"),
            }

        return {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "correction": entry,
            "message": f"Correction {entry['id']} logged successfully. Error reported during conversation and queued for review.",
            "total_pending": sum(1 for c in corrections if c.get("status") == "pending"),
        }

    except Exception as e:
        logger.exception("Internal error reporting error")
        if legacy_format:
            return {"error": f"Failed to log correction: {e}"}
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": f"Internal error reporting error: {e}",
            },
        }
