"""Test KB Writer Service endpoints and functionality.

This test suite validates:
1. KB entry submission with proper validation
2. Approval/rejection workflow endpoints
3. Pending approvals retrieval
4. Entry detail retrieval
5. Input validation for confidence scores and fields
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Import the router from kb_writer_service
from kb_self_learning.kb_writer_service import router


@pytest.fixture
def app():
    """Create a test FastAPI app with the KB writer router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestKBEntrySubmission:
    """Test KB entry submission endpoint."""

    def test_submit_valid_entry(self, client):
        """Test submitting a valid KB entry returns success."""
        payload = {
            "topic": "Test Topic",
            "content": "This is test content for the KB entry.",
            "confidence_score": 0.85,
            "source": "self_learning",
            "tags": ["test", "example"],
            "metadata": {"test_key": "test_value"}
        }
        response = client.post("/api/v3.4/kb/write-entry", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "entry_id" in data
        assert data["entry_id"].startswith("kb_")
        assert data["message"] == "KB entry submitted for human approval"
        assert data["data"]["status"] == "pending_approval"
        assert data["data"]["requires_approval"] is True

    def test_submit_entry_rejects_invalid_confidence_above_range(self, client):
        """Test that confidence score above 1.0 is rejected."""
        payload = {
            "topic": "Invalid",
            "content": "Entry with invalid confidence score.",
            "confidence_score": 1.5
        }
        response = client.post("/api/v3.4/kb/write-entry", json=payload)
        
        assert response.status_code == 422  # Validation error

    def test_submit_entry_rejects_short_topic(self, client):
        """Test that topic shorter than 2 characters is rejected."""
        payload = {
            "topic": "A",
            "content": "Valid content here."
        }
        response = client.post("/api/v3.4/kb/write-entry", json=payload)
        
        assert response.status_code == 422  # Validation error


class TestKBEntryApproval:
    """Test KB entry approval/rejection endpoint."""

    def test_approve_entry(self, client):
        """Test approving a KB entry."""
        payload = {
            "kb_entry_id": "kb_test_123",
            "approved": True,
            "reviewer_notes": "Looks good",
            "reviewed_by": "reviewer@example.com"
        }
        response = client.post("/api/v3.4/kb/approve-entry", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["entry_id"] == "kb_test_123"


class TestPendingApprovals:
    """Test pending approvals endpoint."""

    def test_get_pending_approvals(self, client):
        """Test retrieving pending approvals."""
        response = client.get("/api/v3.4/kb/pending-approvals")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "pending_entries" in data
        assert "count" in data
