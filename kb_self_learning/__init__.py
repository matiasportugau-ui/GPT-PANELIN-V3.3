"""
GPT Panel v3.4 - Knowledge Base Self-Learning Module
=====================================================

Provides KB entry submission with human approval workflow.
Registers FastAPI routers for /api/v3.4/kb and /api/v3.4/approval endpoints.

Usage:
    from kb_self_learning import register_routers
    register_routers(app)
"""

from .kb_writer_service import router as kb_router
from .approval_workflow import router as approval_router


def register_routers(app):
    """Register all kb_self_learning routers with a FastAPI app."""
    app.include_router(kb_router)
    app.include_router(approval_router)
