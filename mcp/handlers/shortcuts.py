"""Handler for the shortcut MCP tools.

Provides CRUD management and execution of shortcuts (atajos).
Shortcuts are named command templates that can be triggered via
``/shortcut-name`` in chat or scheduled to run at specific times.

Tools:
- ``shortcut_execute``: Run a shortcut by name, returning its prompt and config.
- ``shortcut_manage``: Create, update, delete, and list shortcuts.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

KB_ROOT = Path(__file__).resolve().parent.parent.parent
SHORTCUTS_FILE = KB_ROOT / "shortcuts.json"


def _load_shortcuts() -> Dict[str, Any]:
    """Load shortcuts from persistent storage."""
    if not SHORTCUTS_FILE.exists():
        return {"version": "1.0.0", "shortcuts": []}
    with open(SHORTCUTS_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save_shortcuts(data: Dict[str, Any]) -> None:
    """Save shortcuts to persistent storage."""
    with open(SHORTCUTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _find_shortcut(shortcuts: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    """Find a shortcut by name (case-insensitive, strips leading /)."""
    lookup = name.lstrip("/").lower()
    for s in shortcuts:
        if s.get("name", "").lower() == lookup:
            return s
    return None


# ── shortcut_execute ────────────────────────────────────────────────

async def handle_shortcut_execute(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a shortcut by name, returning its prompt and configuration.

    The caller (LLM or automation) is expected to carry out the
    instructions contained in the returned ``prompt`` field.
    """
    name = arguments.get("name", "").strip()
    if not name:
        return {
            "ok": False,
            "error": {"code": "MISSING_NAME", "message": "Shortcut name is required"},
        }

    data = _load_shortcuts()
    shortcut = _find_shortcut(data["shortcuts"], name)

    if shortcut is None:
        available = [s["name"] for s in data["shortcuts"]]
        return {
            "ok": False,
            "error": {
                "code": "NOT_FOUND",
                "message": f"Shortcut '/{name.lstrip('/')}' not found",
                "available_shortcuts": available,
            },
        }

    if not shortcut.get("enabled", True):
        return {
            "ok": False,
            "error": {
                "code": "DISABLED",
                "message": f"Shortcut '/{shortcut['name']}' is currently disabled",
            },
        }

    logger.info("Executing shortcut: /%s", shortcut["name"])

    return {
        "ok": True,
        "shortcut": {
            "name": shortcut["name"],
            "prompt": shortcut["prompt"],
            "start_url": shortcut.get("start_url"),
            "model": shortcut.get("model"),
            "tags": shortcut.get("tags", []),
        },
        "hint": (
            "Execute the instructions in the 'prompt' field. "
            "If 'start_url' is provided, navigate there first."
        ),
    }


# ── shortcut_manage ─────────────────────────────────────────────────

async def handle_shortcut_manage(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Manage shortcuts: list, create, update, delete, enable, disable."""
    action = arguments.get("action", "list").lower()

    dispatch = {
        "list": _action_list,
        "create": _action_create,
        "update": _action_update,
        "delete": _action_delete,
        "enable": _action_enable,
        "disable": _action_disable,
    }

    handler = dispatch.get(action)
    if handler is None:
        return {
            "ok": False,
            "error": {
                "code": "INVALID_ACTION",
                "message": f"Unknown action '{action}'. "
                           f"Valid: {', '.join(dispatch)}",
            },
        }

    return await handler(arguments)


# ── Action helpers ──────────────────────────────────────────────────

async def _action_list(arguments: Dict[str, Any]) -> Dict[str, Any]:
    data = _load_shortcuts()
    shortcuts = data["shortcuts"]

    tag_filter = arguments.get("tag")
    if tag_filter:
        shortcuts = [
            s for s in shortcuts
            if tag_filter.lower() in [t.lower() for t in s.get("tags", [])]
        ]

    summaries = [
        {
            "name": s["name"],
            "enabled": s.get("enabled", True),
            "start_url": s.get("start_url"),
            "model": s.get("model"),
            "schedule": s.get("schedule"),
            "tags": s.get("tags", []),
        }
        for s in shortcuts
    ]

    return {"ok": True, "total": len(summaries), "shortcuts": summaries}


async def _action_create(arguments: Dict[str, Any]) -> Dict[str, Any]:
    name = arguments.get("name", "").strip().lstrip("/")
    prompt = arguments.get("prompt", "").strip()

    if not name:
        return {
            "ok": False,
            "error": {"code": "MISSING_NAME", "message": "name is required"},
        }
    if not prompt:
        return {
            "ok": False,
            "error": {"code": "MISSING_PROMPT", "message": "prompt is required"},
        }

    data = _load_shortcuts()
    if _find_shortcut(data["shortcuts"], name):
        return {
            "ok": False,
            "error": {
                "code": "DUPLICATE",
                "message": f"Shortcut '/{name}' already exists. Use 'update' to modify.",
            },
        }

    shortcut: Dict[str, Any] = {
        "id": name,
        "name": name,
        "prompt": prompt,
        "start_url": arguments.get("start_url"),
        "model": arguments.get("model"),
        "schedule": arguments.get("schedule"),
        "enabled": True,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tags": arguments.get("tags", []),
    }

    data["shortcuts"].append(shortcut)
    _save_shortcuts(data)

    logger.info("Created shortcut: /%s", name)
    return {"ok": True, "message": f"Shortcut '/{name}' created", "shortcut": shortcut}


async def _action_update(arguments: Dict[str, Any]) -> Dict[str, Any]:
    name = arguments.get("name", "").strip().lstrip("/")
    if not name:
        return {
            "ok": False,
            "error": {"code": "MISSING_NAME", "message": "name is required"},
        }

    data = _load_shortcuts()
    shortcut = _find_shortcut(data["shortcuts"], name)
    if shortcut is None:
        return {
            "ok": False,
            "error": {"code": "NOT_FOUND", "message": f"Shortcut '/{name}' not found"},
        }

    updatable = ("prompt", "start_url", "model", "schedule", "tags")
    for field in updatable:
        if field in arguments:
            shortcut[field] = arguments[field]

    _save_shortcuts(data)

    logger.info("Updated shortcut: /%s", name)
    return {"ok": True, "message": f"Shortcut '/{name}' updated", "shortcut": shortcut}


async def _action_delete(arguments: Dict[str, Any]) -> Dict[str, Any]:
    name = arguments.get("name", "").strip().lstrip("/")
    if not name:
        return {
            "ok": False,
            "error": {"code": "MISSING_NAME", "message": "name is required"},
        }

    data = _load_shortcuts()
    lookup = name.lower()
    original_len = len(data["shortcuts"])
    data["shortcuts"] = [
        s for s in data["shortcuts"] if s.get("name", "").lower() != lookup
    ]

    if len(data["shortcuts"]) == original_len:
        return {
            "ok": False,
            "error": {"code": "NOT_FOUND", "message": f"Shortcut '/{name}' not found"},
        }

    _save_shortcuts(data)

    logger.info("Deleted shortcut: /%s", name)
    return {"ok": True, "message": f"Shortcut '/{name}' deleted"}


async def _action_enable(arguments: Dict[str, Any]) -> Dict[str, Any]:
    return await _toggle_enabled(arguments, enabled=True)


async def _action_disable(arguments: Dict[str, Any]) -> Dict[str, Any]:
    return await _toggle_enabled(arguments, enabled=False)


async def _toggle_enabled(arguments: Dict[str, Any], *, enabled: bool) -> Dict[str, Any]:
    name = arguments.get("name", "").strip().lstrip("/")
    if not name:
        return {
            "ok": False,
            "error": {"code": "MISSING_NAME", "message": "name is required"},
        }

    data = _load_shortcuts()
    shortcut = _find_shortcut(data["shortcuts"], name)
    if shortcut is None:
        return {
            "ok": False,
            "error": {"code": "NOT_FOUND", "message": f"Shortcut '/{name}' not found"},
        }

    shortcut["enabled"] = enabled
    _save_shortcuts(data)

    state = "enabled" if enabled else "disabled"
    logger.info("%s shortcut: /%s", state.capitalize(), name)
    return {"ok": True, "message": f"Shortcut '/{name}' {state}"}
