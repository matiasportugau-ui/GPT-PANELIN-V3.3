"""Shared test fixtures for KB Architecture tests.

Uses SQLite in-memory via aiosqlite for fast unit tests.
Mocks google.cloud.storage to avoid dependency on GCP libraries in test env.
"""

from __future__ import annotations

import os
import sys
from types import ModuleType
from unittest.mock import MagicMock

# Ensure test env vars are set before importing app modules
os.environ.setdefault("WOLF_API_KEY", "test-api-key-12345")
os.environ.setdefault("KB_WRITE_PASSWORD", "test-password")
os.environ.setdefault("KB_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

# Mock google.cloud.storage so wolf_api.main can import without GCP deps
if "google" not in sys.modules:
    _mock_google = ModuleType("google")
    _mock_google_cloud = ModuleType("google.cloud")
    _mock_google_cloud_storage = MagicMock()
    _mock_google_api_core = ModuleType("google.api_core")
    _mock_google_api_core_exc = MagicMock()
    sys.modules["google"] = _mock_google
    sys.modules["google.cloud"] = _mock_google_cloud
    sys.modules["google.cloud.storage"] = _mock_google_cloud_storage
    sys.modules["google.api_core"] = _mock_google_api_core
    sys.modules["google.api_core.exceptions"] = _mock_google_api_core_exc
    _mock_google.cloud = _mock_google_cloud  # type: ignore
    _mock_google_cloud.storage = _mock_google_cloud_storage  # type: ignore
    _mock_google.api_core = _mock_google_api_core  # type: ignore
    _mock_google_api_core.exceptions = _mock_google_api_core_exc  # type: ignore

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from wolf_api.kb_models import Base
from wolf_api.kb_database import get_db_session


@pytest_asyncio.fixture
async def test_engine():
    """Create an in-memory SQLite async engine."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine):
    """Create a test database session."""
    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(test_engine):
    """Async test client for the Wolf API with KB Architecture routes."""
    # Import app here to avoid import order issues
    from wolf_api.main import app

    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def api_headers():
    """Headers with valid API key."""
    return {"X-API-Key": "test-api-key-12345"}


@pytest.fixture
def sample_modules():
    """Sample module data for creating versions."""
    return [
        {
            "module_name": "core_engine",
            "module_data": {
                "redondeo_estructural": {"method": "ceil"},
                "optimizacion_constructiva": {"enabled": True},
                "escenarios": {"default": "standard"},
            },
        },
        {
            "module_name": "consumibles_margin",
            "module_data": {
                "sellador": {"margin_pct": 15},
                "fijaciones": {"margin_pct": 12},
            },
        },
        {
            "module_name": "ml_conversion_engine",
            "module_data": {
                "modes": {"aggressive": True, "conservative": False},
                "priority_order": ["price", "availability", "lead_time"],
            },
        },
    ]


@pytest.fixture
def create_version_payload(sample_modules):
    """Payload for POST /api/kb/architecture."""
    return {
        "version_type": "full_snapshot",
        "description": "Test KB architecture v1.0",
        "author": "test_user",
        "modules": sample_modules,
        "password": "test-password",
        "metadata": {"environment": "test"},
    }
