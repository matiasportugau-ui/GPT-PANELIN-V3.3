"""
Centralized configuration for Panelin Sheets Orchestrator.

All settings are driven by environment variables with sensible defaults.
On Cloud Run, secrets are injected via Secret Manager → env vars.
Locally, use a .env file (loaded by scripts/local_run.sh).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name, default)
    return v if v not in ("", None) else None


@dataclass(frozen=True)
class Settings:
    # Runtime
    env: str = "dev"
    gcp_project_id: str = ""
    log_level: str = "INFO"
    service_version: str = "0.2.0"

    # OpenAI
    openai_model: str = "gpt-4o-mini"
    openai_api_key: Optional[str] = None
    openai_safety_identifier_prefix: str = "panelin-"
    openai_max_tokens: int = 4096
    openai_temperature: float = 0.1

    # Inbound auth
    panelin_orch_api_key: Optional[str] = None
    api_key_header_name: str = "X-API-Key"

    # Google Sheets
    sheets_scopes: List[str] = field(default_factory=lambda: ["https://www.googleapis.com/auth/spreadsheets"])
    sheets_cache_ttl_seconds: int = 300
    sheets_max_retries: int = 5
    sheets_batch_delay_ms: int = 100

    # Idempotency
    idempotency_backend: str = "memory"
    firestore_collection: str = "panelin_sheet_jobs"
    firestore_database: str = "(default)"

    # Paths
    templates_dir: str = "templates/sheets"
    queue_template_path: str = "templates/queue/queue_v1.example.json"

    # Business rules
    iva_rate: float = 0.22
    iva_included: bool = True
    default_safety_margin: float = 0.15
    currency: str = "USD"


def load_settings() -> Settings:
    scopes_raw = _env(
        "SHEETS_SCOPES", "https://www.googleapis.com/auth/spreadsheets"
    ) or ""
    scopes = [s.strip() for s in scopes_raw.split(",") if s.strip()]

    return Settings(
        env=_env("ENV", "dev") or "dev",
        gcp_project_id=_env("GCP_PROJECT_ID", "") or "",
        log_level=_env("LOG_LEVEL", "INFO") or "INFO",
        service_version=_env("SERVICE_VERSION", "0.2.0") or "0.2.0",
        openai_model=_env("OPENAI_MODEL", "gpt-4o-mini") or "gpt-4o-mini",
        openai_api_key=_env("OPENAI_API_KEY"),
        openai_safety_identifier_prefix=_env("OPENAI_SAFETY_IDENTIFIER_PREFIX", "panelin-") or "panelin-",
        openai_max_tokens=int(_env("OPENAI_MAX_TOKENS", "4096") or "4096"),
        openai_temperature=float(_env("OPENAI_TEMPERATURE", "0.1") or "0.1"),
        panelin_orch_api_key=_env("PANELIN_ORCH_API_KEY"),
        api_key_header_name=_env("API_KEY_HEADER_NAME", "X-API-Key") or "X-API-Key",
        sheets_scopes=scopes,
        sheets_cache_ttl_seconds=int(_env("SHEETS_CACHE_TTL_SECONDS", "300") or "300"),
        sheets_max_retries=int(_env("SHEETS_MAX_RETRIES", "5") or "5"),
        sheets_batch_delay_ms=int(_env("SHEETS_BATCH_DELAY_MS", "100") or "100"),
        idempotency_backend=_env("IDEMPOTENCY_BACKEND", "memory") or "memory",
        firestore_collection=_env("FIRESTORE_COLLECTION", "panelin_sheet_jobs") or "panelin_sheet_jobs",
        firestore_database=_env("FIRESTORE_DATABASE", "(default)") or "(default)",
        templates_dir=_env("TEMPLATES_DIR", "templates/sheets") or "templates/sheets",
        queue_template_path=_env("QUEUE_TEMPLATE_PATH", "templates/queue/queue_v1.example.json") or "templates/queue/queue_v1.example.json",
        iva_rate=float(_env("IVA_RATE", "0.22") or "0.22"),
        iva_included=(_env("IVA_INCLUDED", "true") or "true").lower() == "true",
        default_safety_margin=float(_env("DEFAULT_SAFETY_MARGIN", "0.15") or "0.15"),
        currency=_env("CURRENCY", "USD") or "USD",
    )
