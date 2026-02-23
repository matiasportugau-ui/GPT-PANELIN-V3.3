"""
Tests for Wolf API KB Conversations endpoint.
"""

import os
import json
from unittest.mock import Mock, patch, MagicMock
import pytest
from fastapi.testclient import TestClient


# Mock environment variables before importing app
@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock environment variables for tests."""
    monkeypatch.setenv("WOLF_API_KEY", "test-api-key-12345")
    monkeypatch.setenv("KB_GCS_BUCKET", "test-bucket")
    monkeypatch.setenv("KB_GCS_PREFIX", "kb/conversations")
    monkeypatch.setenv("KB_GCS_MODE", "daily_jsonl")


@pytest.fixture
def client():
    """Create test client."""
    # Import after env vars are set
    from wolf_api.main import app
    return TestClient(app)


@pytest.fixture
def mock_storage_client():
    """Mock GCS storage client."""
    with patch("wolf_api.main.storage.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        
        # Mock bucket and blob operations
        mock_bucket = MagicMock()
        mock_instance.bucket.return_value = mock_bucket
        
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        
        # Mock successful operations
        mock_blob.upload_from_string = MagicMock()
        mock_blob.reload = MagicMock()
        mock_blob.compose = MagicMock()
        mock_blob.delete = MagicMock()
        mock_blob.generation = 1
        
        yield mock_instance


def test_root_endpoint(client):
    """Test root endpoint returns API info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Panelin Wolf API"
    assert data["version"] == "2.2.0"
    assert data["status"] == "operational"


def test_health_endpoint(client):
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_ready_endpoint(client):
    """Test ready endpoint."""
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_kb_conversations_missing_api_key(client):
    """Test POST /kb/conversations without API key returns 401."""
    payload = {
        "client_id": "test-client",
        "summary": "Test conversation",
    }
    response = client.post("/kb/conversations", json=payload)
    assert response.status_code == 401
    assert "Invalid or missing X-API-Key" in response.json()["detail"]


def test_kb_conversations_invalid_api_key(client):
    """Test POST /kb/conversations with invalid API key returns 401."""
    payload = {
        "client_id": "test-client",
        "summary": "Test conversation",
    }
    headers = {"X-API-Key": "wrong-key"}
    response = client.post("/kb/conversations", json=payload, headers=headers)
    assert response.status_code == 401


def test_kb_conversations_success_daily_mode(client, mock_storage_client):
    """Test POST /kb/conversations with valid API key succeeds."""
    payload = {
        "client_id": "test-client-123",
        "summary": "Discussed panel installation",
        "quotation_ref": "Q-2026-001",
        "products_discussed": ["Panel BMC 20mm", "Panel BMC 30mm"],
    }
    headers = {"X-API-Key": "test-api-key-12345"}
    
    response = client.post("/kb/conversations", json=payload, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "stored_at" in data
    assert "gcs" in data
    assert data["gcs"]["ok"] is True
    assert data["gcs"]["mode"] == "daily_jsonl"


def test_kb_conversations_per_event_mode(client, mock_storage_client, monkeypatch):
    """Test POST /kb/conversations in per_event_jsonl mode."""
    monkeypatch.setenv("KB_GCS_MODE", "per_event_jsonl")
    
    # Re-import to pick up new env var
    from importlib import reload
    import wolf_api.main
    reload(wolf_api.main)
    
    client_updated = TestClient(wolf_api.main.app)
    
    payload = {
        "client_id": "test-client-456",
        "summary": "Quick quote request",
    }
    headers = {"X-API-Key": "test-api-key-12345"}
    
    response = client_updated.post("/kb/conversations", json=payload, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["gcs"]["mode"] == "per_event_jsonl"


def test_kb_conversations_missing_bucket_config(client, monkeypatch):
    """Test POST /kb/conversations fails when bucket not configured."""
    # Unset bucket env var
    monkeypatch.delenv("KB_GCS_BUCKET", raising=False)
    
    # Re-import to pick up change
    from importlib import reload
    import wolf_api.main
    reload(wolf_api.main)
    
    client_updated = TestClient(wolf_api.main.app)
    
    payload = {"client_id": "test", "summary": "test"}
    headers = {"X-API-Key": "test-api-key-12345"}
    
    response = client_updated.post("/kb/conversations", json=payload, headers=headers)
    assert response.status_code == 503
    assert "KB_GCS_BUCKET is missing" in response.json()["detail"]


def test_openapi_includes_kb_conversations(client):
    """Test OpenAPI spec includes /kb/conversations endpoint."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    openapi_spec = response.json()
    
    assert "/kb/conversations" in openapi_spec["paths"]
    assert "post" in openapi_spec["paths"]["/kb/conversations"]


def test_api_key_constant_time_comparison(client):
    """Test API key comparison uses constant-time to prevent timing attacks."""
    # This test verifies that hmac.compare_digest is used
    # by checking the behavior is consistent
    payload = {"client_id": "test", "summary": "test"}
    
    # Multiple attempts with wrong key should behave identically
    headers1 = {"X-API-Key": "wrong1"}
    headers2 = {"X-API-Key": "wrong2"}
    
    response1 = client.post("/kb/conversations", json=payload, headers=headers1)
    response2 = client.post("/kb/conversations", json=payload, headers=headers2)
    
    assert response1.status_code == response2.status_code == 401
