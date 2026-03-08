"""Async task manager for background processing.

Manages task lifecycle, dispatches workers, and provides thread-safe
access to task state. Uses asyncio for concurrency within the MCP
server event loop.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Callable, Awaitable

from .models import Task, TaskProgress, TaskStatus, TaskType

logger = logging.getLogger(__name__)

# Type alias for worker coroutines
WorkerFn = Callable[[Task], Awaitable[dict[str, Any]]]


class TaskManager:
    """In-process async task manager.

    Stores tasks in memory and dispatches background workers via
    ``asyncio.create_task``.  Designed for single-process deployments
    (suitable for the Panelin MCP server's scale).
    """

    def __init__(self, max_concurrent: int = 5, max_history: int = 100) -> None:
        self._tasks: dict[str, Task] = {}
        self._workers: dict[TaskType, WorkerFn] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._max_history = max_history
        self._running_tasks: dict[str, asyncio.Task[None]] = {}

    # ------------------------------------------------------------------
    # Worker registration
    # ------------------------------------------------------------------

    def register_worker(self, task_type: TaskType, worker: WorkerFn) -> None:
        """Register an async worker function for a task type."""
        self._workers[task_type] = worker
        logger.info("Registered worker for task type: %s", task_type.value)

    # ------------------------------------------------------------------
    # Task submission
    # ------------------------------------------------------------------

    async def submit(
        self,
        task_type: TaskType,
        arguments: dict[str, Any],
    ) -> Task:
        """Submit a new background task and start processing it.

        Returns the ``Task`` object immediately (status=pending).
        The task is dispatched asynchronously and its status can be
        polled via ``get_task``.
        """
        worker = self._workers.get(task_type)
        if worker is None:
            raise ValueError(f"No worker registered for task type: {task_type.value}")

        task_id = f"TASK-{uuid.uuid4().hex[:8].upper()}"
        task = Task(
            task_id=task_id,
            task_type=task_type,
            arguments=arguments,
        )
        self._tasks[task_id] = task

        # Evict oldest completed tasks if history limit exceeded
        self._evict_old_tasks()

        # Dispatch the worker coroutine
        asyncio_task = asyncio.create_task(self._run_worker(task, worker))
        self._running_tasks[task_id] = asyncio_task

        logger.info("Submitted task %s (type=%s)", task_id, task_type.value)
        return task

    # ------------------------------------------------------------------
    # Task queries
    # ------------------------------------------------------------------

    def get_task(self, task_id: str) -> Task | None:
        """Retrieve a task by ID, or None if not found."""
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        *,
        status: TaskStatus | None = None,
        task_type: TaskType | None = None,
        limit: int = 20,
    ) -> list[Task]:
        """List tasks, optionally filtered by status and/or type."""
        tasks = list(self._tasks.values())

        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        if task_type is not None:
            tasks = [t for t in tasks if t.task_type == task_type]

        # Most recent first
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks[:limit]

    # ------------------------------------------------------------------
    # Task cancellation
    # ------------------------------------------------------------------

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task. Returns True if cancelled."""
        task = self._tasks.get(task_id)
        if task is None:
            return False

        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            return False  # Already terminal

        # Cancel the asyncio task if running
        asyncio_task = self._running_tasks.get(task_id)
        if asyncio_task is not None and not asyncio_task.done():
            asyncio_task.cancel()

        task.mark_cancelled()
        logger.info("Cancelled task %s", task_id)
        return True

    # ------------------------------------------------------------------
    # Internal worker execution
    # ------------------------------------------------------------------

    async def _run_worker(self, task: Task, worker: WorkerFn) -> None:
        """Execute the worker within the concurrency semaphore."""
        async with self._semaphore:
            task.mark_running()
            logger.info("Running task %s", task.task_id)

            try:
                result = await worker(task)
                task.mark_completed(result)
                logger.info("Task %s completed successfully", task.task_id)
            except asyncio.CancelledError:
                task.mark_cancelled()
                logger.info("Task %s was cancelled", task.task_id)
            except Exception as exc:
                task.mark_failed(str(exc))
                logger.error("Task %s failed: %s", task.task_id, exc, exc_info=True)
            finally:
                self._running_tasks.pop(task.task_id, None)

    # ------------------------------------------------------------------
    # History management
    # ------------------------------------------------------------------

    def _evict_old_tasks(self) -> None:
        """Remove oldest completed/failed/cancelled tasks beyond max_history."""
        terminal = [
            t for t in self._tasks.values()
            if t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
        ]
        if len(terminal) <= self._max_history:
            return

        terminal.sort(key=lambda t: t.created_at)
        to_evict = terminal[: len(terminal) - self._max_history]
        for t in to_evict:
            self._tasks.pop(t.task_id, None)

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    async def shutdown(self) -> None:
        """Cancel all running tasks and clean up."""
        for task_id, asyncio_task in list(self._running_tasks.items()):
            if not asyncio_task.done():
                asyncio_task.cancel()
        # Wait briefly for cancellation
        if self._running_tasks:
            await asyncio.gather(*self._running_tasks.values(), return_exceptions=True)
        self._running_tasks.clear()
        logger.info("Task manager shut down")


# Singleton instance used by the MCP server
_manager: TaskManager | None = None


def get_task_manager() -> TaskManager:
    """Return the singleton TaskManager, creating it on first access."""
    global _manager
    if _manager is None:
        _manager = TaskManager()
    return _manager
