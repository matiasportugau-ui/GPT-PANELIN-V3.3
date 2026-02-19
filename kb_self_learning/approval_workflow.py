"""
GPT Panel v3.4 - Knowledge Base Approval Workflow
Manages the human approval process for KB entries
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ApprovalStatus(str, Enum):
      PENDING = "pending_approval"
      APPROVED = "approved"
      REJECTED = "rejected"
      NEEDS_REVISION = "needs_revision"

class ApprovalWorkflow:
      """Manages the approval workflow for KB entries"""

    def __init__(self):
              self.pending_queue = {}
              self.approval_history = []

    def submit_for_approval(self, entry_id: str, entry_data: dict, submitter: str) -> dict:
              """Submit an entry to the approval queue"""
              try:
                            workflow_data = {
                                              "entry_id": entry_id,
                                              "entry_data": entry_data,
                                              "status": ApprovalStatus.PENDING,
                                              "submitted_at": datetime.utcnow().isoformat(),
                                              "submitted_by": submitter,
                                              "approvals": [],
                                              "rejections": []
                            }
                            self.pending_queue[entry_id] = workflow_data
                            logger.info(f"Entry {entry_id} submitted for approval by {submitter}")
                            return {"status": "submitted", "entry_id": entry_id}
except Exception as e:
            logger.error(f"Error submitting entry for approval: {str(e)}")
            raise

    def approve_entry(self, entry_id: str, reviewer: str, notes: Optional[str] = None) -> dict:
              """Approve an entry"""
              try:
                            if entry_id not in self.pending_queue:
                                              raise ValueError(f"Entry {entry_id} not found")

                            workflow_data = self.pending_queue[entry_id]
                            workflow_data["approvals"].append({
                                "reviewer": reviewer,
                                "approved_at": datetime.utcnow().isoformat(),
                                "notes": notes
                            })
                            workflow_data["status"] = ApprovalStatus.APPROVED
                            workflow_data["approved_at"] = datetime.utcnow().isoformat()

            self.approval_history.append(workflow_data)
            del self.pending_queue[entry_id]

            logger.info(f"Entry {entry_id} approved by {reviewer}")
            return {"status": "approved", "entry_id": entry_id}
except Exception as e:
            logger.error(f"Error approving entry: {str(e)}")
            raise

    def reject_entry(self, entry_id: str, reviewer: str, reason: str) -> dict:
              """Reject an entry"""
              try:
                            if entry_id not in self.pending_queue:
                                              raise ValueError(f"Entry {entry_id} not found")

                            workflow_data = self.pending_queue[entry_id]
                            workflow_data["rejections"].append({
                                "reviewer": reviewer,
                                "rejected_at": datetime.utcnow().isoformat(),
                                "reason": reason
                            })
                            workflow_data["status"] = ApprovalStatus.REJECTED
                            workflow_data["rejected_at"] = datetime.utcnow().isoformat()

            self.approval_history.append(workflow_data)
            del self.pending_queue[entry_id]

            logger.info(f"Entry {entry_id} rejected by {reviewer}: {reason}")
            return {"status": "rejected", "entry_id": entry_id, "reason": reason}
except Exception as e:
            logger.error(f"Error rejecting entry: {str(e)}")
            raise

    def request_revision(self, entry_id: str, reviewer: str, revision_notes: str) -> dict:
              """Request revision for an entry"""
              try:
                            if entry_id not in self.pending_queue:
                                              raise ValueError(f"Entry {entry_id} not found")

                            workflow_data = self.pending_queue[entry_id]
                            workflow_data["status"] = ApprovalStatus.NEEDS_REVISION
                            workflow_data["revision_requested_at"] = datetime.utcnow().isoformat()
                            workflow_data["revision_notes"] = revision_notes
                            workflow_data["revision_requested_by"] = reviewer

            logger.info(f"Entry {entry_id} marked for revision by {reviewer}")
            return {"status": "revision_requested", "entry_id": entry_id}
except Exception as e:
            logger.error(f"Error requesting revision: {str(e)}")
            raise

    def get_pending_entries(self) -> List[dict]:
              """Get all pending entries"""
              return list(self.pending_queue.values())

    def get_entry_status(self, entry_id: str) -> dict:
              """Get status of a specific entry"""
              if entry_id in self.pending_queue:
                            return {"status": "in_queue", "data": self.pending_queue[entry_id]}

              for hist in self.approval_history:
                            if hist["entry_id"] == entry_id:
                                              return {"status": "processed", "data": hist}

                        raise ValueError(f"Entry {entry_id} not found")

    def get_approval_stats(self) -> dict:
              """Get approval workflow statistics"""
        approved = sum(1 for h in self.approval_history if h["status"] == ApprovalStatus.APPROVED)
        rejected = sum(1 for h in self.approval_history if h["status"] == ApprovalStatus.REJECTED)
        pending = len(self.pending_queue)

        return {
                      "approved": approved,
                      "rejected": rejected,
                      "pending": pending,
                      "total_processed": len(self.approval_history),
                      "approval_rate": approved / len(self.approval_history) if self.approval_history else 0
        }

# Global workflow instance
approval_workflow = ApprovalWorkflow()

# Router for approval endpoints
router = APIRouter(prefix="/api/v3.4/approval", tags=["approval_workflow"])

@router.get("/pending")
async def get_pending_approvals():
      """Get all pending KB entries waiting for approval"""
    try:
              pending = approval_workflow.get_pending_entries()
        return {
                      "status": "success",
                      "pending_count": len(pending),
                      "entries": pending
        }
except Exception as e:
        logger.error(f"Error getting pending approvals: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/approve/{entry_id}")
async def approve_kb_entry(entry_id: str, reviewer: str, notes: Optional[str] = None):
      """Approve a KB entry"""
    try:
              result = approval_workflow.approve_entry(entry_id, reviewer, notes)
        return result
except Exception as e:
        logger.error(f"Error approving entry: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reject/{entry_id}")
async def reject_kb_entry(entry_id: str, reviewer: str, reason: str):
      """Reject a KB entry"""
    try:
              result = approval_workflow.reject_entry(entry_id, reviewer, reason)
        return result
except Exception as e:
        logger.error(f"Error rejecting entry: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_approval_stats():
      """Get approval workflow statistics"""
    try:
              stats = approval_workflow.get_approval_stats()
        return {"status": "success", "stats": stats}
except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
