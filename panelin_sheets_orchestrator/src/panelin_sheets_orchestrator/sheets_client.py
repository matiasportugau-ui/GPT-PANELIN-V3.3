"""
Google Sheets API client with caching, retries, and structured audit logging.

Features:
- ADC (Application Default Credentials) on Cloud Run
- Fallback to base64-encoded service account JSON for local/airgap
- Exponential backoff on 429/5xx via tenacity
- In-memory snapshot cache with configurable TTL
- Batch operations (batchGet / batchUpdate)
- Audit logging for every API call
"""

from __future__ import annotations

import base64
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import google.auth
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .audit import audit_sheets_api_call
from .config import Settings

logger = logging.getLogger("panelin.sheets.client")


def _is_retryable(exc: BaseException) -> bool:
    if not isinstance(exc, HttpError):
        return False
    status = getattr(getattr(exc, "resp", None), "status", None)
    return status in (429, 500, 502, 503, 504)


class SnapshotCache:
    """Simple TTL cache for sheet snapshots to avoid redundant reads."""

    def __init__(self, ttl_seconds: int = 300) -> None:
        self._ttl = ttl_seconds
        self._store: Dict[str, Tuple[float, Dict[str, Any]]] = {}

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, data = entry
        if time.monotonic() - ts > self._ttl:
            del self._store[key]
            return None
        return data

    def put(self, key: str, data: Dict[str, Any]) -> None:
        self._store[key] = (time.monotonic(), data)

    def invalidate(self, spreadsheet_id: str) -> None:
        keys_to_remove = [k for k in self._store if k.startswith(spreadsheet_id)]
        for k in keys_to_remove:
            del self._store[k]

    def clear(self) -> None:
        self._store.clear()


class SheetsClient:
    """High-level Google Sheets API client."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cache = SnapshotCache(ttl_seconds=settings.sheets_cache_ttl_seconds)
        self._max_retries = settings.sheets_max_retries

    def _get_credentials(self):
        from .config import _env

        b64 = _env("GOOGLE_SA_JSON_B64")
        if b64:
            info = json.loads(base64.b64decode(b64).decode("utf-8"))
            return service_account.Credentials.from_service_account_info(
                info, scopes=self._settings.sheets_scopes
            )
        creds, _ = google.auth.default(scopes=self._settings.sheets_scopes)
        return creds

    def _build_service(self):
        creds = self._get_credentials()
        return build("sheets", "v4", credentials=creds, cache_discovery=False)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        retry=retry_if_exception_type(HttpError),
        reraise=True,
    )
    def batch_get(
        self,
        spreadsheet_id: str,
        ranges: List[str],
        *,
        job_id: str = "",
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        cache_key = f"{spreadsheet_id}|{'|'.join(sorted(ranges))}"
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit for %s", cache_key)
                return cached

        t0 = time.monotonic()
        svc = self._build_service()
        result = (
            svc.spreadsheets()
            .values()
            .batchGet(spreadsheetId=spreadsheet_id, ranges=ranges)
            .execute()
        )
        elapsed = round((time.monotonic() - t0) * 1000, 2)

        audit_sheets_api_call(
            job_id=job_id,
            operation="batchGet",
            spreadsheet_id=spreadsheet_id,
            ranges_count=len(ranges),
            duration_ms=elapsed,
        )

        self._cache.put(cache_key, result)
        return result

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        retry=retry_if_exception_type(HttpError),
        reraise=True,
    )
    def batch_update(
        self,
        spreadsheet_id: str,
        data: List[Dict[str, Any]],
        *,
        job_id: str = "",
        value_input_option: str = "USER_ENTERED",
    ) -> Dict[str, Any]:
        t0 = time.monotonic()
        svc = self._build_service()
        body = {
            "valueInputOption": value_input_option,
            "data": data,
            "includeValuesInResponse": False,
        }
        result = (
            svc.spreadsheets()
            .values()
            .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
            .execute()
        )
        elapsed = round((time.monotonic() - t0) * 1000, 2)

        audit_sheets_api_call(
            job_id=job_id,
            operation="batchUpdate",
            spreadsheet_id=spreadsheet_id,
            ranges_count=len(data),
            duration_ms=elapsed,
        )

        self._cache.invalidate(spreadsheet_id)
        return result

    def read_single_range(
        self,
        spreadsheet_id: str,
        range_str: str,
        *,
        job_id: str = "",
    ) -> List[List[Any]]:
        """Read a single range and return just the values (2D list)."""
        result = self.batch_get(
            spreadsheet_id, [range_str], job_id=job_id
        )
        value_ranges = result.get("valueRanges", [])
        if not value_ranges:
            return []
        return value_ranges[0].get("values", [])

    def get_spreadsheet_metadata(
        self,
        spreadsheet_id: str,
        *,
        job_id: str = "",
    ) -> Dict[str, Any]:
        """Fetch spreadsheet metadata (title, sheets list, locale)."""
        t0 = time.monotonic()
        svc = self._build_service()
        result = (
            svc.spreadsheets()
            .get(
                spreadsheetId=spreadsheet_id,
                fields="spreadsheetId,properties.title,properties.locale,sheets.properties",
            )
            .execute()
        )
        elapsed = round((time.monotonic() - t0) * 1000, 2)

        audit_sheets_api_call(
            job_id=job_id,
            operation="get_metadata",
            spreadsheet_id=spreadsheet_id,
            ranges_count=0,
            duration_ms=elapsed,
        )

        return result

    def clear(self) -> None:
        """Clear the internal cache."""
        self._cache.clear()
