"""
Google Sheets API client with caching, retries, and structured audit logging.

Features:
- ADC (Application Default Credentials) on Cloud Run
- Fallback to base64-encoded service account JSON for local/airgap
- Exponential backoff ONLY on retryable errors (429/5xx) via tenacity
- In-memory snapshot cache with configurable TTL and max size
- Cached credentials and API service object
- Batch operations (batchGet / batchUpdate)
- Audit logging for every API call
"""

from __future__ import annotations

import base64
import json
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import google.auth
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from .audit import audit_sheets_api_call
from .config import Settings

logger = logging.getLogger("panelin.sheets.client")

_DEFAULT_MAX_CACHE_ENTRIES = 256


def _is_retryable_http_error(exc: BaseException) -> bool:
    """Only retry on rate-limit (429) or server errors (5xx)."""
    if not isinstance(exc, HttpError):
        return False
    status = getattr(getattr(exc, "resp", None), "status", None)
    return status in (429, 500, 502, 503, 504)


class SnapshotCache:
    """TTL cache for sheet snapshots with max size eviction (LRU-style)."""

    def __init__(self, ttl_seconds: int = 300, max_entries: int = _DEFAULT_MAX_CACHE_ENTRIES) -> None:
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._store: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            ts, data = entry
            if time.monotonic() - ts > self._ttl:
                del self._store[key]
                return None
            return data

    def put(self, key: str, data: Dict[str, Any]) -> None:
        with self._lock:
            if len(self._store) >= self._max_entries and key not in self._store:
                oldest_key = min(self._store, key=lambda k: self._store[k][0])
                del self._store[oldest_key]
            self._store[key] = (time.monotonic(), data)

    def invalidate(self, spreadsheet_id: str) -> None:
        with self._lock:
            keys_to_remove = [k for k in self._store if k.startswith(spreadsheet_id)]
            for k in keys_to_remove:
                del self._store[k]

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        return len(self._store)


class SheetsClient:
    """High-level Google Sheets API client with cached credentials."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cache = SnapshotCache(
            ttl_seconds=settings.sheets_cache_ttl_seconds,
            max_entries=_DEFAULT_MAX_CACHE_ENTRIES,
        )
        self._lock = threading.Lock()
        self._service = None
        self._creds = None

    def _get_credentials(self):
        if self._creds is not None and not getattr(self._creds, "expired", True):
            return self._creds

        from .config import _env

        b64 = _env("GOOGLE_SA_JSON_B64")
        if b64:
            info = json.loads(base64.b64decode(b64).decode("utf-8"))
            self._creds = service_account.Credentials.from_service_account_info(
                info, scopes=self._settings.sheets_scopes
            )
        else:
            self._creds, _ = google.auth.default(scopes=self._settings.sheets_scopes)
        return self._creds

    def _get_service(self):
        with self._lock:
            if self._service is None:
                creds = self._get_credentials()
                self._service = build("sheets", "v4", credentials=creds, cache_discovery=False)
            return self._service

    def _reset_service(self) -> None:
        """Reset the cached service (e.g., after credential refresh)."""
        with self._lock:
            self._service = None
            self._creds = None

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        retry=retry_if_exception(_is_retryable_http_error),
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
        svc = self._get_service()
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
        retry=retry_if_exception(_is_retryable_http_error),
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
        svc = self._get_service()
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
        svc = self._get_service()
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
