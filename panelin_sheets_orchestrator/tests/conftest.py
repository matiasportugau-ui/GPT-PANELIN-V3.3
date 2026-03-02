"""Shared fixtures for Panelin Sheets Orchestrator tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

TEMPLATES_DIR = str(Path(__file__).resolve().parent.parent / "templates" / "sheets")
QUEUE_TEMPLATE = str(Path(__file__).resolve().parent.parent / "templates" / "queue" / "queue_v1.example.json")

os.environ.setdefault("IDEMPOTENCY_BACKEND", "memory")
os.environ.setdefault("PANELIN_ORCH_API_KEY", "test-key-123")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("TEMPLATES_DIR", TEMPLATES_DIR)
os.environ.setdefault("QUEUE_TEMPLATE_PATH", QUEUE_TEMPLATE)


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch):
    monkeypatch.setenv("IDEMPOTENCY_BACKEND", "memory")
    monkeypatch.setenv("PANELIN_ORCH_API_KEY", "test-key-123")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("TEMPLATES_DIR", TEMPLATES_DIR)
    monkeypatch.setenv("QUEUE_TEMPLATE_PATH", QUEUE_TEMPLATE)


@pytest.fixture()
def api_key_header():
    return {"X-API-Key": "test-key-123"}
