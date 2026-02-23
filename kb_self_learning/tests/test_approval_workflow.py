"""Test Approval Workflow functionality.

This test suite validates:
1. Workflow state management (submit, approve, reject)
2. Entry status tracking
3. Approval statistics calculation
4. Revision request workflow
5. API endpoints for approval operations
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Import the workflow class and router
from kb_self_learning.approval_workflow import (
    ApprovalWorkflow,
    ApprovalStatus,
    router
)


@pytest.fixture
def workflow():
    """Create a fresh approval workflow instance."""
    return ApprovalWorkflow()


@pytest.fixture
def app():
    """Create a test FastAPI app with the approval router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestApprovalWorkflowCore:
    """Test core approval workflow functionality."""

    def test_submit_entry_for_approval(self, workflow):
        """Test submitting an entry to the approval queue."""
        entry_data = {
            "topic": "Test Topic",
            "content": "Test content",
            "confidence_score": 0.85
        }
        result = workflow.submit_for_approval(
            "test_entry_1",
            entry_data,
            "test_submitter"
        )
        
        assert result["status"] == "submitted"
        assert result["entry_id"] == "test_entry_1"
        assert "test_entry_1" in workflow.pending_queue
        
        queued_entry = workflow.pending_queue["test_entry_1"]
        assert queued_entry["status"] == ApprovalStatus.PENDING
        assert queued_entry["submitted_by"] == "test_submitter"

    def test_approve_entry(self, workflow):
        """Test approving a pending entry."""
        # First submit an entry
        entry_data = {"topic": "Test", "content": "Content"}
        workflow.submit_for_approval("entry_1", entry_data, "submitter")
        
        # Then approve it
        result = workflow.approve_entry("entry_1", "reviewer", "Approved")
        
        assert result["status"] == "approved"
        assert result["entry_id"] == "entry_1"
        assert "entry_1" not in workflow.pending_queue
        assert len(workflow.approval_history) == 1
        
        history_entry = workflow.approval_history[0]
        assert history_entry["status"] == ApprovalStatus.APPROVED
        assert len(history_entry["approvals"]) == 1

    def test_reject_entry(self, workflow):
        """Test rejecting a pending entry."""
        # First submit an entry
        entry_data = {"topic": "Test", "content": "Content"}
        workflow.submit_for_approval("entry_2", entry_data, "submitter")
        
        # Then reject it
        result = workflow.reject_entry("entry_2", "reviewer", "Not good enough")
        
        assert result["status"] == "rejected"
        assert result["entry_id"] == "entry_2"
        assert "entry_2" not in workflow.pending_queue
        assert len(workflow.approval_history) == 1
        
        history_entry = workflow.approval_history[0]
        assert history_entry["status"] == ApprovalStatus.REJECTED
        assert len(history_entry["rejections"]) == 1

    def test_request_revision(self, workflow):
        """Test requesting revision for an entry."""
        # Submit an entry
        entry_data = {"topic": "Test", "content": "Content"}
        workflow.submit_for_approval("entry_3", entry_data, "submitter")
        
        # Request revision
        result = workflow.request_revision("entry_3", "reviewer", "Needs more detail")
        
        assert result["status"] == "revision_requested"
        assert result["entry_id"] == "entry_3"
        assert "entry_3" in workflow.pending_queue  # Still in queue
        
        queued_entry = workflow.pending_queue["entry_3"]
        assert queued_entry["status"] == ApprovalStatus.NEEDS_REVISION

    def test_approve_nonexistent_entry_raises_error(self, workflow):
        """Test that approving non-existent entry raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            workflow.approve_entry("nonexistent", "reviewer", "notes")

    def test_get_pending_entries(self, workflow):
        """Test retrieving all pending entries."""
        # Submit multiple entries
        workflow.submit_for_approval("e1", {"topic": "T1"}, "sub1")
        workflow.submit_for_approval("e2", {"topic": "T2"}, "sub2")
        
        pending = workflow.get_pending_entries()
        
        assert len(pending) == 2
        entry_ids = [e["entry_id"] for e in pending]
        assert "e1" in entry_ids
        assert "e2" in entry_ids

    def test_get_entry_status_in_queue(self, workflow):
        """Test getting status of entry in queue."""
        workflow.submit_for_approval("e1", {"topic": "T1"}, "sub1")
        
        status = workflow.get_entry_status("e1")
        
        assert status["status"] == "in_queue"
        assert "data" in status

    def test_get_entry_status_processed(self, workflow):
        """Test getting status of processed entry."""
        workflow.submit_for_approval("e1", {"topic": "T1"}, "sub1")
        workflow.approve_entry("e1", "reviewer", "Good")
        
        status = workflow.get_entry_status("e1")
        
        assert status["status"] == "processed"
        assert status["data"]["status"] == ApprovalStatus.APPROVED


class TestApprovalStatistics:
    """Test approval statistics calculation."""

    def test_approval_stats_empty_workflow(self, workflow):
        """Test stats for empty workflow."""
        stats = workflow.get_approval_stats()
        
        assert stats["approved"] == 0
        assert stats["rejected"] == 0
        assert stats["pending"] == 0
        assert stats["total_processed"] == 0
        assert stats["approval_rate"] == 0

    def test_approval_stats_with_data(self, workflow):
        """Test stats calculation with mixed approvals/rejections."""
        # Submit and approve 2 entries
        workflow.submit_for_approval("e1", {"t": "1"}, "s")
        workflow.approve_entry("e1", "r", "ok")
        workflow.submit_for_approval("e2", {"t": "2"}, "s")
        workflow.approve_entry("e2", "r", "ok")
        
        # Submit and reject 1 entry
        workflow.submit_for_approval("e3", {"t": "3"}, "s")
        workflow.reject_entry("e3", "r", "bad")
        
        # Submit 1 pending entry
        workflow.submit_for_approval("e4", {"t": "4"}, "s")
        
        stats = workflow.get_approval_stats()
        
        assert stats["approved"] == 2
        assert stats["rejected"] == 1
        assert stats["pending"] == 1
        assert stats["total_processed"] == 3
        assert stats["approval_rate"] == pytest.approx(2/3, rel=0.01)

    def test_approval_rate_avoids_division_by_zero(self, workflow):
        """Test that approval rate handles case with no decided entries."""
        # Submit but don't approve/reject
        workflow.submit_for_approval("e1", {"t": "1"}, "s")
        
        stats = workflow.get_approval_stats()
        
        assert stats["approval_rate"] == 0  # No decided entries yet


class TestApprovalEndpoints:
    """Test approval workflow API endpoints."""

    def test_get_pending_endpoint(self, client):
        """Test the GET /pending endpoint."""
        response = client.get("/api/v3.4/approval/pending")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "pending_count" in data
        assert "entries" in data

    def test_get_stats_endpoint(self, client):
        """Test the GET /stats endpoint."""
        response = client.get("/api/v3.4/approval/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "stats" in data
        assert "approved" in data["stats"]
        assert "rejected" in data["stats"]
        assert "pending" in data["stats"]
