"""WhatsApp conversation ingestion for morning audit."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

import requests
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


def _safe_date_ddmm(value: str | None) -> str:
    if not value:
        return datetime.now().strftime("%d-%m")
    try:
        return date_parser.parse(value).strftime("%d-%m")
    except (ValueError, TypeError):
        return datetime.now().strftime("%d-%m")


def fetch_whatsapp_messages(timeout: int = 30) -> list[dict[str, str]]:
    """
    Fetch unread WhatsApp records from a configurable API endpoint.

    Expected response format (flexible):
    {
      "data": [
        {
          "cliente": "...",
          "telefono": "...",
          "direccion": "...",
          "consulta": "...",
          "fecha": "2026-03-04T10:30:00Z"
        }
      ]
    }
    """
    endpoint = os.getenv("WHATSAPP_AUDIT_ENDPOINT", "").strip()
    token = os.getenv("WHATSAPP_AUDIT_TOKEN", "").strip()
    if not endpoint:
        logger.info("ℹ️ WhatsApp audit endpoint not configured; skipping API fetch.")
        return []

    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.get(endpoint, headers=headers, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        logger.error("❌ WhatsApp fetch failed: %s", exc)
        return []
    except ValueError as exc:
        logger.error("❌ WhatsApp payload is not valid JSON: %s", exc)
        return []

    candidates = payload.get("data") or payload.get("results") or payload.get("messages") or []
    if not isinstance(candidates, list):
        logger.warning("⚠️ WhatsApp payload format not recognized; skipping.")
        return []

    records: list[dict[str, str]] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        records.append(
            {
                "cliente": str(item.get("cliente") or item.get("name") or item.get("from") or "Cliente WhatsApp"),
                "origen": "WA",
                "telefono": str(item.get("telefono") or item.get("phone") or ""),
                "direccion": str(item.get("direccion") or item.get("address") or ""),
                "consulta": str(item.get("consulta") or item.get("message") or "Consulta WhatsApp"),
                "fecha": _safe_date_ddmm(str(item.get("fecha") or item.get("timestamp") or "")),
            }
        )

    logger.info("✅ WhatsApp records fetched: %s", len(records))
    return records
