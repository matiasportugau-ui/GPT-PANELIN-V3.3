"""Self-healing architecture handlers for change governance.

Provides enterprise-grade product governance through:
- Change validation against the pricing index
- Automatic impact analysis on recent quotations
- Recalculation simulation before commit
- Change report generation
- Commit endpoint for approved corrections

Flow:
    User proposes correction
       ↓
    validate_correction validates against pricing index
       ↓
    Simulates impact on last 50 quotations
       ↓
    Generates change report
       ↓
    commit_correction applies approved change
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Optional

from mcp_tools.contracts import (
    CONTRACT_VERSION,
    VALIDATE_CORRECTION_ERROR_CODES,
    COMMIT_CORRECTION_ERROR_CODES,
)

logger = logging.getLogger(__name__)

KB_ROOT = Path(__file__).resolve().parent.parent.parent
CORRECTIONS_FILE = KB_ROOT / "corrections_log.json"
QUOTATION_MEMORY_FILE = KB_ROOT / "mcp" / "quotation_memory.json"

# Allowed KB files (same whitelist as errors.py)
ALLOWED_KB_FILES = [
    "bromyros_pricing_master.json",
    "bromyros_pricing_gpt_optimized.json",
    "accessories_catalog.json",
    "bom_rules.json",
    "shopify_catalog_v1.json",
    "BMC_Base_Conocimiento_GPT-2.json",
    "perfileria_index.json",
]

# In-memory cache for validated changes pending commit
_pending_changes: dict[str, dict[str, Any]] = {}
_pending_changes_lock = threading.Lock()

MAX_IMPACT_QUOTATIONS = 50


def _generate_change_id(kb_file: str, field: str, proposed_value: str) -> str:
    """Generate a deterministic change ID from the correction parameters."""
    payload = f"{kb_file}:{field}:{proposed_value}:{datetime.now(timezone.utc).isoformat()}"
    return "CHG-" + hashlib.sha256(payload.encode()).hexdigest()[:12].upper()


def _load_kb_file(kb_file: str) -> Any:
    """Load a KB file safely from the allowed whitelist."""
    path = KB_ROOT / kb_file
    if not path.is_file():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _resolve_field(data: Any, field_path: str) -> tuple[bool, Any]:
    """Resolve a dot/bracket-notation field path in a JSON structure.

    Supports paths like:
        - "data.products[0].pricing.web_iva_inc"
        - "items[32].price_usd"

    Returns:
        (found: bool, value: Any)
    """
    import re
    # Split on dots that are not inside square brackets
    parts = re.split(r'\.(?![^\[]*\])', field_path)
    current = data
    for part in parts:
        # Handle array indexing: items[32]
        match = re.match(r'^(.+?)\[(\d+)\]$', part)
        if match:
            key, idx = match.group(1), int(match.group(2))
            if isinstance(current, dict) and key in current:
                current = current[key]
                if isinstance(current, list) and 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return False, None
            else:
                return False, None
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return False, None
    return True, current


def _load_recent_quotations(limit: int = MAX_IMPACT_QUOTATIONS) -> list[dict[str, Any]]:
    """Load recent quotations from the memory store for impact analysis."""
    if not QUOTATION_MEMORY_FILE.is_file():
        return []
    try:
        with open(QUOTATION_MEMORY_FILE, encoding="utf-8") as f:
            data = json.load(f)
        quotations = data if isinstance(data, list) else data.get("quotations", [])
        return quotations[-limit:]
    except (json.JSONDecodeError, OSError):
        return []


def _simulate_price_impact(
    quotations: list[dict[str, Any]],
    field: str,
    current_value: Any,
    proposed_value: Any,
) -> dict[str, Any]:
    """Simulate the impact of a price change on recent quotations.

    Analyzes quotations to find those affected by the change and
    calculates the monetary impact using Decimal arithmetic.
    """
    affected: list[dict[str, Any]] = []
    total_impact = Decimal("0.00")

    # Try to interpret values as numeric for price impact
    try:
        current_num = Decimal(str(current_value))
        proposed_num = Decimal(str(proposed_value))
        price_delta = proposed_num - current_num
        is_numeric = True
    except Exception:
        price_delta = Decimal("0.00")
        is_numeric = False

    for q in quotations:
        quotation_data = q.get("quotation", q)
        q_id = quotation_data.get("quotation_id", quotation_data.get("id", "unknown"))

        # Check if this quotation references the affected product/field
        # Look for matching SKU, product_id, or price references
        matched = False
        line_items = quotation_data.get("line_items", quotation_data.get("items", []))
        q_total = Decimal(str(quotation_data.get("total_usd", quotation_data.get("grand_total_usd", 0))))

        for item in line_items:
            item_price = item.get("unit_price_usd", item.get("price_usd", 0))
            try:
                if is_numeric and Decimal(str(item_price)) == current_num:
                    matched = True
                    qty = Decimal(str(item.get("quantity", item.get("panels_needed", 1))))
                    item_impact = price_delta * qty
                    total_impact += item_impact
                    affected.append({
                        "quotation_id": q_id,
                        "item": item.get("name", item.get("product_name", "unknown")),
                        "original_line_total": str(
                            (current_num * qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                        ),
                        "revised_line_total": str(
                            (proposed_num * qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                        ),
                        "impact_usd": str(
                            item_impact.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                        ),
                    })
                    break
            except Exception:
                continue

        # Also check top-level product references
        if not matched and is_numeric:
            q_price = quotation_data.get("unit_price_per_m2", 0)
            try:
                if Decimal(str(q_price)) == current_num:
                    area = Decimal(str(quotation_data.get("area_m2", 1)))
                    item_impact = price_delta * area
                    total_impact += item_impact
                    affected.append({
                        "quotation_id": q_id,
                        "item": quotation_data.get("product_name", "unknown"),
                        "original_total": str(q_total),
                        "revised_total": str(
                            (q_total + item_impact).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                        ),
                        "impact_usd": str(
                            item_impact.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                        ),
                    })
            except Exception:
                pass

    return {
        "quotations_analyzed": len(quotations),
        "quotations_affected": len(affected),
        "total_impact_usd": str(
            total_impact.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ),
        "affected_quotations": affected,
    }


def _load_corrections() -> dict[str, Any]:
    """Load corrections log."""
    with open(CORRECTIONS_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save_corrections(data: dict[str, Any]) -> None:
    """Save corrections log."""
    with open(CORRECTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _next_correction_id(corrections: list[dict[str, Any]]) -> str:
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
            pass
    return f"COR-{last_num + 1:03d}"


async def handle_validate_correction(
    arguments: dict[str, Any],
    legacy_format: bool = False,
) -> dict[str, Any]:
    """Validate a proposed KB correction with impact analysis.

    Validates the correction against the actual KB data, simulates
    impact on recent quotations, and generates a change report.

    Args:
        arguments: Tool arguments containing kb_file, field,
            current_value, proposed_value
        legacy_format: If True, return legacy format for
            backwards compatibility

    Returns:
        v1 contract envelope with validation result and impact analysis
    """
    kb_file = arguments.get("kb_file", "")
    field = arguments.get("field", "")
    current_value = arguments.get("current_value", "")
    proposed_value = arguments.get("proposed_value")
    source = arguments.get("source", "user_correction")
    notes = arguments.get("notes", "")

    # --- Validate required parameters ---
    if not kb_file or not field or proposed_value is None:
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": VALIDATE_CORRECTION_ERROR_CODES["FIELD_NOT_FOUND"],
                "message": "kb_file, field, and proposed_value are required",
            },
        }

    # --- Validate kb_file against whitelist ---
    kb_file_clean = str(kb_file).replace("/", "").replace("\\", "").replace("..", "")
    if kb_file_clean not in ALLOWED_KB_FILES:
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": VALIDATE_CORRECTION_ERROR_CODES["INVALID_KB_FILE"],
                "message": f"Invalid kb_file. Must be one of: {', '.join(ALLOWED_KB_FILES)}",
            },
        }

    try:
        # --- Step 1: Load KB and validate field ---
        kb_data = _load_kb_file(kb_file_clean)
        if kb_data is None:
            return {
                "ok": False,
                "contract_version": CONTRACT_VERSION,
                "error": {
                    "code": VALIDATE_CORRECTION_ERROR_CODES["INVALID_KB_FILE"],
                    "message": f"KB file '{kb_file_clean}' not found on disk",
                },
            }

        field_exists, actual_value = _resolve_field(kb_data, field)

        # --- Step 2: Check current_value match ---
        value_mismatch = False
        if current_value != "" and field_exists:
            try:
                if str(actual_value) != str(current_value):
                    value_mismatch = True
            except Exception:
                value_mismatch = True

        validation_result = {
            "field_exists": field_exists,
            "current_value": str(actual_value) if field_exists else None,
            "proposed_value": str(proposed_value),
            "value_match": not value_mismatch if field_exists else None,
        }

        if value_mismatch:
            return {
                "ok": False,
                "contract_version": CONTRACT_VERSION,
                "error": {
                    "code": VALIDATE_CORRECTION_ERROR_CODES["VALUE_MISMATCH"],
                    "message": (
                        f"Current value '{actual_value}' does not match "
                        f"expected '{current_value}'"
                    ),
                    "details": validation_result,
                },
            }

        # --- Step 3: Simulate impact on recent quotations ---
        recent_quotations = _load_recent_quotations(MAX_IMPACT_QUOTATIONS)
        impact = _simulate_price_impact(
            recent_quotations,
            field,
            actual_value if field_exists else current_value,
            proposed_value,
        )

        # --- Step 4: Generate change report ---
        change_id = _generate_change_id(kb_file_clean, field, str(proposed_value))
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        severity = "low"
        if impact["quotations_affected"] > 0:
            try:
                abs_impact = abs(Decimal(impact["total_impact_usd"]))
                if abs_impact > Decimal("1000"):
                    severity = "high"
                elif abs_impact > Decimal("100"):
                    severity = "medium"
            except Exception:
                severity = "medium"

        change_report = {
            "change_id": change_id,
            "timestamp": now,
            "severity": severity,
            "summary": (
                f"Change to {kb_file_clean}:{field} — "
                f"from '{actual_value if field_exists else 'N/A'}' "
                f"to '{proposed_value}'. "
                f"{impact['quotations_affected']}/{impact['quotations_analyzed']} "
                f"quotations affected "
                f"(total impact: USD {impact['total_impact_usd']})"
            ),
        }

        # --- Cache the validated change for commit ---
        pending_entry = {
            "change_id": change_id,
            "kb_file": kb_file_clean,
            "field": field,
            "current_value": str(actual_value) if field_exists else str(current_value),
            "proposed_value": str(proposed_value),
            "source": source,
            "notes": notes,
            "validation": validation_result,
            "impact": impact,
            "report": change_report,
            "created_at": now,
        }

        with _pending_changes_lock:
            _pending_changes[change_id] = pending_entry

        return {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "validation": validation_result,
            "impact_analysis": impact,
            "change_report": change_report,
            "change_id": change_id,
        }

    except Exception as e:
        logger.exception("Internal error during correction validation")
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": VALIDATE_CORRECTION_ERROR_CODES["INTERNAL_ERROR"],
                "message": f"Internal error during validation: {e}",
            },
        }


async def handle_commit_correction(
    arguments: dict[str, Any],
    legacy_format: bool = False,
) -> dict[str, Any]:
    """Commit a validated correction to the corrections log.

    Requires a valid change_id from a prior validate_correction call
    and explicit confirmation.

    Args:
        arguments: Tool arguments containing change_id and confirm flag
        legacy_format: If True, return legacy format for
            backwards compatibility

    Returns:
        v1 contract envelope with commit confirmation
    """
    change_id = arguments.get("change_id", "")
    confirm = arguments.get("confirm", False)

    if not change_id:
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": COMMIT_CORRECTION_ERROR_CODES["CHANGE_NOT_FOUND"],
                "message": "change_id is required",
            },
        }

    if not confirm:
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": COMMIT_CORRECTION_ERROR_CODES["CONFIRMATION_REQUIRED"],
                "message": "Set confirm=true to apply this correction",
            },
        }

    # --- Retrieve the validated change ---
    with _pending_changes_lock:
        pending = _pending_changes.pop(change_id, None)

    if pending is None:
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": COMMIT_CORRECTION_ERROR_CODES["CHANGE_NOT_FOUND"],
                "message": (
                    f"Change '{change_id}' not found. "
                    "Run validate_correction first."
                ),
            },
        }

    try:
        # --- Write to corrections log ---
        data = _load_corrections()
        corrections = data.get("corrections", [])

        entry = {
            "id": _next_correction_id(corrections),
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "kb_file": pending["kb_file"],
            "field": pending["field"],
            "wrong_value": pending["current_value"],
            "correct_value": pending["proposed_value"],
            "source": pending["source"],
            "notes": pending["notes"],
            "status": "pending",
            "applied_date": None,
            "change_id": change_id,
            "impact_summary": {
                "quotations_affected": pending["impact"]["quotations_affected"],
                "total_impact_usd": pending["impact"]["total_impact_usd"],
                "severity": pending["report"]["severity"],
            },
        }

        corrections.append(entry)
        data["corrections"] = corrections
        _save_corrections(data)

        return {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "correction": entry,
            "message": (
                f"Correction {entry['id']} committed successfully. "
                f"{pending['impact']['quotations_affected']} quotation(s) affected."
            ),
            "total_pending": sum(
                1 for c in corrections if c.get("status") == "pending"
            ),
        }

    except Exception as e:
        logger.exception("Internal error during correction commit")
        # Re-cache the change so user can retry
        with _pending_changes_lock:
            _pending_changes[change_id] = pending
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": COMMIT_CORRECTION_ERROR_CODES["INTERNAL_ERROR"],
                "message": f"Internal error during commit: {e}",
            },
        }
