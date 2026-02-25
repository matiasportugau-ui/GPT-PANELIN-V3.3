"""Tests for configuration module."""

from __future__ import annotations

import os

from panelin_sheets_orchestrator.config import Settings, load_settings


class TestSettings:
    def test_defaults(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
        s = load_settings()
        assert s.env == "test"
        assert s.idempotency_backend == "memory"
        assert s.iva_rate == 0.22
        assert s.iva_included is True
        assert s.currency == "USD"
        assert s.default_safety_margin == 0.15

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
        monkeypatch.setenv("IVA_RATE", "0.10")
        s = load_settings()
        assert s.openai_model == "gpt-4o"
        assert s.iva_rate == 0.10

    def test_sheets_scopes_parsing(self, monkeypatch):
        monkeypatch.setenv(
            "SHEETS_SCOPES",
            "https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive.readonly",
        )
        s = load_settings()
        assert len(s.sheets_scopes) == 2

    def test_frozen(self):
        s = load_settings()
        with __import__("pytest").raises(AttributeError):
            s.env = "prod"  # type: ignore
