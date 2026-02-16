"""FastAPI Integration for Background Tasks.

Provides REST API endpoints for task management and monitoring.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    from fastapi import FastAPI, HTTPException, Query
    from pydantic import BaseModel
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


if HAS_FASTAPI:
    class TaskSubmitRequest(BaseModel):
        """Request model for submitting a task."""
        task_type: str
        parameters: Dict[str, Any]
        priority: str = "normal"
        max_retries: int = 3
        timeout: Optional[float] = None
    
    class TaskStatusResponse(BaseModel):
        """Response model for task status."""
        id: str
        name: str
        status: str
        created_at: str
        started_at: Optional[str] = None
        completed_at: Optional[str] = None
        retry_count: int
        error: Optional[str] = None
        result: Optional[Any] = None
    
    class TaskStatsResponse(BaseModel):
        """Response model for task statistics."""
        pending: int
        running: int
        completed: int
        failed: int
        retrying: int
        cancelled: int
        total: int
    
    
    def create_task_api(queue, worker) -> FastAPI:
        """Create FastAPI app for task management.
        
        Args:
            queue: TaskQueue instance
            worker: TaskWorker instance
        
        Returns:
            FastAPI application
        """
        app = FastAPI(
            title="Panelin Background Tasks API",
            description="API for managing background tasks",
            version="1.0.0"
        )
        
        @app.get("/")
        async def root():
            """API root endpoint."""
            return {
                "name": "Panelin Background Tasks API",
                "version": "1.0.0",
                "worker_running": worker.is_running(),
                "queue_size": queue.size()
            }
        
        @app.get("/tasks/stats", response_model=TaskStatsResponse)
        async def get_task_stats():
            """Get task statistics."""
            stats = await queue.get_task_stats()
            total = sum(stats.values())
            return TaskStatsResponse(
                pending=stats.get('pending', 0),
                running=stats.get('running', 0),
                completed=stats.get('completed', 0),
                failed=stats.get('failed', 0),
                retrying=stats.get('retrying', 0),
                cancelled=stats.get('cancelled', 0),
                total=total
            )
        
        @app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
        async def get_task_status(task_id: str):
            """Get status of a specific task."""
            task = await queue.get_task(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            
            return TaskStatusResponse(
                id=task.id,
                name=task.name,
                status=task.status.value,
                created_at=task.created_at.isoformat(),
                started_at=task.started_at.isoformat() if task.started_at else None,
                completed_at=task.completed_at.isoformat() if task.completed_at else None,
                retry_count=task.retry_count,
                error=task.error,
                result=task.result
            )
        
        @app.delete("/tasks/{task_id}")
        async def cancel_task(task_id: str):
            """Cancel a pending task."""
            success = await queue.cancel_task(task_id)
            if not success:
                raise HTTPException(
                    status_code=400,
                    detail="Task not found or already running"
                )
            return {"message": "Task cancelled", "task_id": task_id}
        
        @app.get("/tasks", response_model=List[TaskStatusResponse])
        async def list_tasks(
            status: Optional[str] = Query(None, description="Filter by status"),
            limit: int = Query(100, ge=1, le=1000, description="Maximum tasks to return")
        ):
            """List tasks, optionally filtered by status."""
            if status:
                from background_tasks.queue import TaskStatus
                try:
                    task_status = TaskStatus(status)
                    tasks = await queue.get_tasks_by_status(task_status)
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid status: {status}"
                    )
            else:
                # Get all tasks
                tasks = list(queue._tasks.values())
            
            # Limit results
            tasks = tasks[:limit]
            
            return [
                TaskStatusResponse(
                    id=task.id,
                    name=task.name,
                    status=task.status.value,
                    created_at=task.created_at.isoformat(),
                    started_at=task.started_at.isoformat() if task.started_at else None,
                    completed_at=task.completed_at.isoformat() if task.completed_at else None,
                    retry_count=task.retry_count,
                    error=task.error,
                    result=task.result
                )
                for task in tasks
            ]
        
        @app.post("/tasks/pdf")
        async def submit_pdf_task(quotation_data: Dict[str, Any]):
            """Submit a PDF generation task."""
            from background_tasks.tasks import generate_quotation_pdf
            from background_tasks.queue import TaskPriority
            
            task = await queue.enqueue(
                generate_quotation_pdf.__background_task_func__,
                quotation_data,
                name="generate_pdf",
                priority=TaskPriority.HIGH,
                max_retries=2,
                timeout=60.0
            )
            
            return {
                "task_id": task.id,
                "status": task.status.value,
                "message": "PDF generation task submitted"
            }
        
        @app.post("/tasks/cleanup")
        async def cleanup_old_tasks(older_than_hours: int = Query(24, ge=1)):
            """Manually trigger cleanup of old completed tasks."""
            removed_count = await queue.clear_completed(older_than_hours=older_than_hours)
            return {
                "removed_count": removed_count,
                "message": f"Removed {removed_count} old tasks"
            }
        
        return app

else:
    # FastAPI not installed
    def create_task_api(queue, worker):
        """FastAPI not available."""
        raise ImportError(
            "FastAPI is required for task API. Install with: pip install fastapi uvicorn"
        )
