"""MCP handlers for KB Architecture versioning tools.

Two tools:
- kb_get_active_architecture: Read active version (no password)
- kb_create_architecture: Create new version (password required)

These handlers proxy requests to the Wolf API KB Architecture endpoints.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from mcp_tools.contracts import (
    CONTRACT_VERSION,
    KB_ARCHITECTURE_ERROR_CODES,
)

logger = logging.getLogger(__name__)

KB_ARCHITECTURE_API_URL = os.getenv(
    "KB_ARCHITECTURE_API_URL",
    os.getenv("WOLF_API_URL", "https://panelin-api-642127786762.us-central1.run.app"),
)
_API_KEY = os.getenv("WOLF_API_KEY", "")


def _headers() -> dict[str, str]:
    """Build request headers with API key."""
    h = {"Content-Type": "application/json"}
    if _API_KEY:
        h["X-API-Key"] = _API_KEY
    return h


async def handle_kb_get_active_architecture(
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Retrieve active KB architecture version via the Wolf API.

    No password required — this is a read operation.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{KB_ARCHITECTURE_API_URL}/api/kb/architecture/active",
                headers=_headers(),
            )

        if resp.status_code == 404:
            return {
                "ok": False,
                "contract_version": CONTRACT_VERSION,
                "error": {
                    "code": KB_ARCHITECTURE_ERROR_CODES["KB_VERSION_NOT_FOUND"],
                    "message": "No active KB version found.",
                },
            }

        if resp.status_code != 200:
            return {
                "ok": False,
                "contract_version": CONTRACT_VERSION,
                "error": {
                    "code": KB_ARCHITECTURE_ERROR_CODES["INTERNAL_ERROR"],
                    "message": f"Wolf API returned {resp.status_code}: {resp.text[:200]}",
                },
            }

        data = resp.json()
        version = data.get("version", {})

        # Optionally strip module data for lighter responses
        include_data = arguments.get("include_module_data", True)
        if not include_data and "modules" in version:
            for mod in version["modules"]:
                mod["module_data"] = "(omitted)"

        return {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "version": version,
        }

    except Exception as exc:
        logger.exception("kb_get_active_architecture failed")
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": KB_ARCHITECTURE_ERROR_CODES["INTERNAL_ERROR"],
                "message": str(exc),
            },
        }


async def handle_kb_create_architecture(
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Create a new KB architecture version via the Wolf API.

    Requires KB write password.
    """
    password = arguments.get("password")
    if not password:
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": KB_ARCHITECTURE_ERROR_CODES["PASSWORD_REQUIRED"],
                "message": "KB write password is required for this operation.",
            },
        }

    description = arguments.get("description")
    author = arguments.get("author")
    modules_dict = arguments.get("modules", {})

    if not description or not author or not modules_dict:
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": KB_ARCHITECTURE_ERROR_CODES["INTERNAL_ERROR"],
                "message": "description, author, and modules are required.",
            },
        }

    # Convert modules from {name: data} dict to list format expected by API
    modules_list = [
        {"module_name": name, "module_data": data}
        for name, data in modules_dict.items()
    ]

    payload = {
        "version_type": arguments.get("version_type", "full_snapshot"),
        "description": description,
        "author": author,
        "modules": modules_list,
        "password": password,
        "metadata": arguments.get("metadata", {}),
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{KB_ARCHITECTURE_API_URL}/api/kb/architecture",
                headers=_headers(),
                json=payload,
            )

        if resp.status_code == 403:
            return {
                "ok": False,
                "contract_version": CONTRACT_VERSION,
                "error": {
                    "code": KB_ARCHITECTURE_ERROR_CODES["INVALID_PASSWORD"],
                    "message": "Invalid KB write password.",
                },
            }

        if resp.status_code not in (200, 201):
            return {
                "ok": False,
                "contract_version": CONTRACT_VERSION,
                "error": {
                    "code": KB_ARCHITECTURE_ERROR_CODES["INTERNAL_ERROR"],
                    "message": f"Wolf API returned {resp.status_code}: {resp.text[:200]}",
                },
            }

        data = resp.json()
        return {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "version": data.get("version", {}),
        }

    except Exception as exc:
        logger.exception("kb_create_architecture failed")
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": KB_ARCHITECTURE_ERROR_CODES["INTERNAL_ERROR"],
                "message": str(exc),
            },
        }
