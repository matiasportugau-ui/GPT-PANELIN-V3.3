"""Handlers for Wolf API KB Write tools (v3.4).

Four tools for persisting data to the Knowledge Base via the Wolf API:
- persist_conversation: Save conversation summaries and quotation history
- register_correction: Register KB corrections for continuous improvement
- save_customer: Store customer data for seamless repeat quotations
- lookup_customer: Retrieve existing customer data (no password required)

Write operations (POST) require a KB write password for authorization.
Read operations (GET) do not require a password.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

from mcp_tools.contracts import (
    CONTRACT_VERSION,
    WOLF_KB_WRITE_ERROR_CODES,
    LOOKUP_CUSTOMER_ERROR_CODES,
)

logger = logging.getLogger(__name__)

# Wolf API client — injected via configure_wolf_kb_client()
_wolf_client: Any | None = None

# KB write password — loaded from environment or default
KB_WRITE_PASSWORD = os.getenv("WOLF_KB_WRITE_PASSWORD", "mywolfy")

# Uruguayan phone regex: 09XXXXXXX (9 digits) or +598XXXXXXXX (12 chars)
_PHONE_PATTERN = re.compile(r"^(09\d{7}|\+598\d{8})$")


def configure_wolf_kb_client(client: Any) -> None:
    """Inject the Wolf API client for KB write operations.

    Called once during server startup from mcp/server.py, following the
    same pattern as configure_quotation_store() in quotation.py.
    """
    global _wolf_client  # noqa: PLW0603
    _wolf_client = client
    logger.info("Wolf KB write client configured")


def _validate_password(arguments: dict[str, Any]) -> dict[str, Any] | None:
    """Validate the KB write password. Returns error envelope or None if valid."""
    password = arguments.get("password")
    if not password:
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": WOLF_KB_WRITE_ERROR_CODES["PASSWORD_REQUIRED"],
                "message": "KB write password is required for this operation.",
            },
        }
    if password != KB_WRITE_PASSWORD:
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": WOLF_KB_WRITE_ERROR_CODES["INVALID_PASSWORD"],
                "message": "Invalid KB write password.",
            },
        }
    return None


def _normalize_phone(phone: str) -> str:
    """Strip spaces and dashes from phone number for validation."""
    return re.sub(r"[\s\-]", "", phone)


async def handle_persist_conversation(arguments: dict[str, Any]) -> dict[str, Any]:
    """Save conversation summary and quotation history to KB via Wolf API.

    Returns:
        v1 contract envelope: {ok, contract_version, conversation_id, stored_at}
        or {ok, contract_version, error: {code, message}}
    """
    # Validate password
    error = _validate_password(arguments)
    if error:
        return error

    client_id = arguments.get("client_id")
    summary = arguments.get("summary")

    if not client_id or not summary:
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": WOLF_KB_WRITE_ERROR_CODES["INTERNAL_ERROR"],
                "message": "client_id and summary are required.",
            },
        }

    try:
        if _wolf_client is None:
            raise RuntimeError("Wolf KB client not configured")

        result = _wolf_client.persist_conversation(
            client_id=client_id,
            summary=summary,
            quotation_ref=arguments.get("quotation_ref"),
            products_discussed=arguments.get("products_discussed"),
        )

        if not result.get("success"):
            return {
                "ok": False,
                "contract_version": CONTRACT_VERSION,
                "error": {
                    "code": WOLF_KB_WRITE_ERROR_CODES["WOLF_API_ERROR"],
                    "message": result.get("error", "Wolf API request failed"),
                },
            }

        data = result.get("data", {})
        return {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "conversation_id": data.get("conversation_id", f"conv-{client_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"),
            "stored_at": result.get("timestamp", datetime.now(timezone.utc).isoformat()),
        }
    except Exception as exc:
        logger.exception("persist_conversation failed")
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": WOLF_KB_WRITE_ERROR_CODES["INTERNAL_ERROR"],
                "message": str(exc),
            },
        }


async def handle_register_correction(arguments: dict[str, Any]) -> dict[str, Any]:
    """Register a KB correction detected during conversation via Wolf API.

    Returns:
        v1 contract envelope: {ok, contract_version, correction_id, stored_at}
        or {ok, contract_version, error: {code, message}}
    """
    error = _validate_password(arguments)
    if error:
        return error

    source_file = arguments.get("source_file")
    field_path = arguments.get("field_path")
    old_value = arguments.get("old_value")
    new_value = arguments.get("new_value")
    reason = arguments.get("reason")

    if not all([source_file, field_path, old_value is not None, new_value is not None, reason]):
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": WOLF_KB_WRITE_ERROR_CODES["INTERNAL_ERROR"],
                "message": "source_file, field_path, old_value, new_value, and reason are required.",
            },
        }

    try:
        if _wolf_client is None:
            raise RuntimeError("Wolf KB client not configured")

        result = _wolf_client.register_correction(
            source_file=source_file,
            field_path=field_path,
            old_value=str(old_value),
            new_value=str(new_value),
            reason=reason,
            reported_by=arguments.get("reported_by"),
        )

        if not result.get("success"):
            return {
                "ok": False,
                "contract_version": CONTRACT_VERSION,
                "error": {
                    "code": WOLF_KB_WRITE_ERROR_CODES["WOLF_API_ERROR"],
                    "message": result.get("error", "Wolf API request failed"),
                },
            }

        data = result.get("data", {})
        return {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "correction_id": data.get("correction_id", f"cor-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"),
            "stored_at": result.get("timestamp", datetime.now(timezone.utc).isoformat()),
        }
    except Exception as exc:
        logger.exception("register_correction failed")
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": WOLF_KB_WRITE_ERROR_CODES["INTERNAL_ERROR"],
                "message": str(exc),
            },
        }


async def handle_save_customer(arguments: dict[str, Any]) -> dict[str, Any]:
    """Store or update customer data for future quotations via Wolf API.

    Validates Uruguayan phone format before persisting.

    Returns:
        v1 contract envelope: {ok, contract_version, customer_id, stored_at}
        or {ok, contract_version, error: {code, message}}
    """
    error = _validate_password(arguments)
    if error:
        return error

    name = arguments.get("name")
    phone = arguments.get("phone")

    if not name or not phone:
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": WOLF_KB_WRITE_ERROR_CODES["INTERNAL_ERROR"],
                "message": "name and phone are required.",
            },
        }

    # Validate Uruguayan phone format
    normalized_phone = _normalize_phone(phone)
    if not _PHONE_PATTERN.match(normalized_phone):
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": WOLF_KB_WRITE_ERROR_CODES["INVALID_PHONE"],
                "message": f"Invalid Uruguayan phone format: '{phone}'. Expected 09XXXXXXX or +598XXXXXXXX.",
            },
        }

    try:
        if _wolf_client is None:
            raise RuntimeError("Wolf KB client not configured")

        result = _wolf_client.save_customer(
            name=name,
            phone=normalized_phone,
            address=arguments.get("address"),
            city=arguments.get("city"),
            department=arguments.get("department"),
            notes=arguments.get("notes"),
        )

        if not result.get("success"):
            return {
                "ok": False,
                "contract_version": CONTRACT_VERSION,
                "error": {
                    "code": WOLF_KB_WRITE_ERROR_CODES["WOLF_API_ERROR"],
                    "message": result.get("error", "Wolf API request failed"),
                },
            }

        data = result.get("data", {})
        return {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "customer_id": data.get("customer_id", f"cust-{normalized_phone}"),
            "stored_at": result.get("timestamp", datetime.now(timezone.utc).isoformat()),
        }
    except Exception as exc:
        logger.exception("save_customer failed")
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": WOLF_KB_WRITE_ERROR_CODES["INTERNAL_ERROR"],
                "message": str(exc),
            },
        }


async def handle_lookup_customer(arguments: dict[str, Any]) -> dict[str, Any]:
    """Retrieve existing customer data from KB via Wolf API.

    No password required — this is a read operation.

    Returns:
        v1 contract envelope: {ok, contract_version, customers, count}
        or {ok, contract_version, error: {code, message}}
    """
    search_query = arguments.get("search_query", "")

    if len(search_query) < 2:
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": LOOKUP_CUSTOMER_ERROR_CODES["QUERY_TOO_SHORT"],
                "message": "Search query must be at least 2 characters.",
            },
        }

    try:
        if _wolf_client is None:
            raise RuntimeError("Wolf KB client not configured")

        result = _wolf_client.lookup_customer(search_query=search_query)

        if not result.get("success"):
            return {
                "ok": False,
                "contract_version": CONTRACT_VERSION,
                "error": {
                    "code": LOOKUP_CUSTOMER_ERROR_CODES["WOLF_API_ERROR"],
                    "message": result.get("error", "Wolf API request failed"),
                },
            }

        data = result.get("data", {})
        customers = data if isinstance(data, list) else data.get("customers", [])
        return {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "customers": customers,
            "count": len(customers),
        }
    except Exception as exc:
        logger.exception("lookup_customer failed")
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": LOOKUP_CUSTOMER_ERROR_CODES["INTERNAL_ERROR"],
                "message": str(exc),
            },
        }
