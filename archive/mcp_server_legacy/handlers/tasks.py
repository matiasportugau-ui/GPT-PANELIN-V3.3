"""MCP tool handlers for background task operations.

Provides the handler functions that the MCP server dispatches to when
clients invoke the background-task tools:

- ``handle_batch_bom_calculate``: Submit batch BOM background task
- ``handle_bulk_price_check``: Submit bulk pricing background task
- ``handle_full_quotation``: Submit full quotation background task
- ``handle_task_status``: Query task progress/state
- ``handle_task_result``: Retrieve completed task result
- ``handle_task_list``: List recent tasks with optional filters
- ``handle_task_cancel``: Cancel a pending/running task
"""

from __future__ import annotations

from typing import Any

from ..tasks.manager import get_task_manager
from ..tasks.models import TaskStatus, TaskType


async def handle_batch_bom_calculate(arguments: dict[str, Any]) -> dict[str, Any]:
    """Submit a batch BOM calculation as a background task."""
    items = arguments.get("items", [])
    if not items:
        return {"error": "At least one item is required in 'items' array"}

    if len(items) > 50:
        return {"error": f"Maximum 50 items per batch, got {len(items)}"}

    manager = get_task_manager()
    task = await manager.submit(
        task_type=TaskType.BATCH_BOM,
        arguments={"items": items},
    )

    return {
        "message": f"Batch BOM task submitted with {len(items)} item(s)",
        "task_id": task.task_id,
        "status": task.status.value,
        "hint": f"Use task_status with task_id='{task.task_id}' to check progress, "
                f"then task_result to retrieve the output when completed.",
    }


async def handle_bulk_price_check(arguments: dict[str, Any]) -> dict[str, Any]:
    """Submit a bulk pricing lookup as a background task."""
    queries = arguments.get("queries", [])
    if not queries:
        return {"error": "At least one query is required in 'queries' array"}

    if len(queries) > 50:
        return {"error": f"Maximum 50 queries per batch, got {len(queries)}"}

    manager = get_task_manager()
    task = await manager.submit(
        task_type=TaskType.BULK_PRICING,
        arguments={"queries": queries},
    )

    return {
        "message": f"Bulk pricing task submitted with {len(queries)} query/queries",
        "task_id": task.task_id,
        "status": task.status.value,
        "hint": f"Use task_status with task_id='{task.task_id}' to check progress, "
                f"then task_result to retrieve the output when completed.",
    }


async def handle_full_quotation(arguments: dict[str, Any]) -> dict[str, Any]:
    """Submit a full quotation generation as a background task."""
    required = ["product_family", "thickness_mm", "usage", "length_m", "width_m"]
    missing = [k for k in required if not arguments.get(k)]
    if missing:
        return {"error": f"Missing required fields: {', '.join(missing)}"}

    manager = get_task_manager()
    task = await manager.submit(
        task_type=TaskType.FULL_QUOTATION,
        arguments=arguments,
    )

    product_desc = (
        f"{arguments.get('product_family', '?')} "
        f"{arguments.get('core_type', 'EPS')} "
        f"{arguments.get('thickness_mm', '?')}mm"
    )

    return {
        "message": f"Full quotation task submitted for {product_desc}",
        "task_id": task.task_id,
        "status": task.status.value,
        "product": product_desc,
        "hint": f"Use task_status with task_id='{task.task_id}' to check progress, "
                f"then task_result to retrieve the complete quotation.",
    }


async def handle_task_status(arguments: dict[str, Any]) -> dict[str, Any]:
    """Check the status of a background task."""
    task_id = arguments.get("task_id", "")
    if not task_id:
        return {"error": "task_id is required"}

    manager = get_task_manager()
    task = manager.get_task(task_id)

    if task is None:
        return {
            "error": f"Task '{task_id}' not found",
            "hint": "Use task_list to see available tasks",
        }

    return task.to_summary()


async def handle_task_result(arguments: dict[str, Any]) -> dict[str, Any]:
    """Retrieve the full result of a completed background task."""
    task_id = arguments.get("task_id", "")
    if not task_id:
        return {"error": "task_id is required"}

    manager = get_task_manager()
    task = manager.get_task(task_id)

    if task is None:
        return {
            "error": f"Task '{task_id}' not found",
            "hint": "Use task_list to see available tasks",
        }

    if task.status == TaskStatus.RUNNING:
        return {
            "error": f"Task '{task_id}' is still running",
            "progress": task.progress.to_dict(),
            "hint": "Use task_status to poll until completed",
        }

    if task.status == TaskStatus.PENDING:
        return {
            "error": f"Task '{task_id}' is still pending (waiting to start)",
            "hint": "Use task_status to poll until completed",
        }

    if task.status == TaskStatus.CANCELLED:
        return {
            "error": f"Task '{task_id}' was cancelled",
            "cancelled_at": task.completed_at,
        }

    if task.status == TaskStatus.FAILED:
        return {
            "error": f"Task '{task_id}' failed: {task.error}",
            "failed_at": task.completed_at,
        }

    # TaskStatus.COMPLETED
    return task.to_full_dict()


async def handle_task_list(arguments: dict[str, Any]) -> dict[str, Any]:
    """List recent background tasks."""
    manager = get_task_manager()

    # Parse optional filters
    status_str = arguments.get("status")
    type_str = arguments.get("task_type")
    limit_raw = arguments.get("limit", 20)

    # Validate and clamp limit to reasonable bounds
    try:
        limit = int(limit_raw)
        limit = max(1, min(limit, 100))  # Clamp between 1 and 100
    except (TypeError, ValueError):
        return {"error": "limit must be a valid integer"}

    # Validate status string length before enum conversion
    if status_str and len(str(status_str)) > 50:
        return {"error": "status parameter too long (max 50 characters)"}

    status_filter: TaskStatus | None = None
    if status_str:
        try:
            status_filter = TaskStatus(status_str)
        except ValueError:
            return {"error": f"Invalid status: '{status_str}'. Valid: pending, running, completed, failed, cancelled"}

    # Validate task_type string length before enum conversion
    if type_str and len(str(type_str)) > 50:
        return {"error": "task_type parameter too long (max 50 characters)"}

    type_filter: TaskType | None = None
    if type_str:
        try:
            type_filter = TaskType(type_str)
        except ValueError:
            return {"error": f"Invalid task_type: '{type_str}'. Valid: batch_bom_calculate, bulk_price_check, full_quotation"}

    tasks = manager.list_tasks(status=status_filter, task_type=type_filter, limit=limit)

    return {
        "total": len(tasks),
        "tasks": [t.to_summary() for t in tasks],
    }


async def handle_task_cancel(arguments: dict[str, Any]) -> dict[str, Any]:
    """Cancel a pending or running background task."""
    task_id = arguments.get("task_id", "")
    if not task_id:
        return {"error": "task_id is required"}

    manager = get_task_manager()
    task = manager.get_task(task_id)

    if task is None:
        return {"error": f"Task '{task_id}' not found"}

    cancelled = await manager.cancel_task(task_id)

    if cancelled:
        return {
            "message": f"Task '{task_id}' has been cancelled",
            "task_id": task_id,
            "status": "cancelled",
        }
    else:
        return {
            "error": f"Task '{task_id}' cannot be cancelled (status: {task.status.value})",
            "task_id": task_id,
            "current_status": task.status.value,
        }
