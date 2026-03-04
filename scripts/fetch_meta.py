"""Meta (Facebook/Instagram) unread conversation ingestion."""

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


def _detect_origin(conversation: dict[str, Any]) -> str:
    link = str(conversation.get("link", "")).lower()
    channel = str(conversation.get("platform", "")).lower()
    if "instagram" in link or "instagram" in channel or "ig" in channel:
        return "IG"
    return "CL"


def _extract_cliente(conversation: dict[str, Any], page_name: str) -> str:
    participants = conversation.get("participants", {})
    participants_data = participants.get("data", []) if isinstance(participants, dict) else []
    for participant in participants_data:
        if not isinstance(participant, dict):
            continue
        name = str(participant.get("name", "")).strip()
        if name and name.lower() != page_name.lower():
            return name
    return "Cliente Meta"


def fetch_meta_messages(timeout: int = 30, limit: int = 50) -> list[dict[str, str]]:
    """
    Fetch unread Meta (Facebook/Instagram) conversations from Graph API.

    Returns normalized records with keys:
    cliente, origen, telefono, direccion, consulta, fecha.
    """
    token = os.getenv("META_PAGE_ACCESS_TOKEN", "").strip()
    page_id = os.getenv("META_PAGE_ID", "").strip()
    if not token or not page_id:
        logger.info("ℹ️ Meta token/page id not configured; skipping API fetch.")
        return []

    page_name = os.getenv("META_PAGE_NAME", "Panelin")
    endpoint = os.getenv(
        "META_CONVERSATIONS_ENDPOINT",
        f"https://graph.facebook.com/v20.0/{page_id}/conversations",
    ).strip()

    params = {
        "fields": "participants,snippet,updated_time,unread_count,link",
        "limit": str(limit),
        "access_token": token,
    }
    try:
        response = requests.get(endpoint, params=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        logger.error("❌ Meta fetch failed: %s", exc)
        return []
    except ValueError as exc:
        logger.error("❌ Meta payload is not valid JSON: %s", exc)
        return []

    conversations = payload.get("data", [])
    if not isinstance(conversations, list):
        logger.warning("⚠️ Meta payload format not recognized; skipping.")
        return []

    records: list[dict[str, str]] = []
    for item in conversations:
        if not isinstance(item, dict):
            continue

        unread = item.get("unread_count")
        if isinstance(unread, int) and unread <= 0:
            continue

        snippet = str(item.get("snippet") or "").strip() or "Consulta pendiente en Meta"
        records.append(
            {
                "cliente": _extract_cliente(item, page_name),
                "origen": _detect_origin(item),
                "telefono": "",
                "direccion": "",
                "consulta": snippet,
                "fecha": _safe_date_ddmm(str(item.get("updated_time") or "")),
            }
        )

    logger.info("✅ Meta records fetched: %s", len(records))
    return records
