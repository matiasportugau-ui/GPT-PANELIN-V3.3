"""MercadoLibre unread message ingestion for morning audit."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

import requests
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)

DEFAULT_ML_UNREAD_ENDPOINT = (
    "https://api.mercadolibre.com/messages/packs/search?tags=unread"
)


def _safe_date_ddmm(value: str | None) -> str:
    if not value:
        return datetime.now().strftime("%d-%m")
    try:
        return date_parser.parse(value).strftime("%d-%m")
    except (ValueError, TypeError):
        return datetime.now().strftime("%d-%m")


def _extract_cliente(item: dict[str, Any]) -> str:
    buyer = item.get("buyer") or {}
    sender = item.get("sender") or item.get("from") or {}
    if isinstance(buyer, dict):
        nickname = buyer.get("nickname") or buyer.get("name")
        if nickname:
            return str(nickname)
    if isinstance(sender, dict):
        name = sender.get("name") or sender.get("nickname")
        if name:
            return str(name)
    return str(item.get("resource") or "Cliente ML")


def _extract_consulta(item: dict[str, Any]) -> str:
    for field in ("snippet", "subject", "text", "message"):
        value = item.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "Consulta pendiente en MercadoLibre"


def fetch_mercadolibre_messages(timeout: int = 30) -> list[dict[str, str]]:
    """
    Fetch unread MercadoLibre records.

    Returns normalized records with keys:
    cliente, origen, telefono, direccion, consulta, fecha.
    """
    token = os.getenv("ML_ACCESS_TOKEN", "").strip()
    if not token:
        logger.info("ℹ️ MercadoLibre token not configured; skipping API fetch.")
        return []

    endpoint = os.getenv("ML_UNREAD_ENDPOINT", DEFAULT_ML_UNREAD_ENDPOINT).strip()
    user_id = os.getenv("ML_USER_ID", "").strip()
    if "{user_id}" in endpoint and user_id:
        endpoint = endpoint.format(user_id=user_id)

    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(endpoint, headers=headers, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        logger.error("❌ MercadoLibre fetch failed: %s", exc)
        return []
    except ValueError as exc:
        logger.error("❌ MercadoLibre payload is not valid JSON: %s", exc)
        return []

    candidates = (
        payload.get("results")
        or payload.get("messages")
        or payload.get("packs")
        or payload.get("data")
        or []
    )
    if not isinstance(candidates, list):
        logger.warning("⚠️ MercadoLibre payload format not recognized; skipping.")
        return []

    records: list[dict[str, str]] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue

        records.append(
            {
                "cliente": _extract_cliente(item),
                "origen": "ML",
                "telefono": "",
                "direccion": "",
                "consulta": _extract_consulta(item),
                "fecha": _safe_date_ddmm(
                    str(item.get("date_created") or item.get("updated_at") or "")
                ),
            }
        )

    logger.info("✅ MercadoLibre records fetched: %s", len(records))
    return records
