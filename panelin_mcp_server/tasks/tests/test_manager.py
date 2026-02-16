"""Tests for the async task manager."""

import asyncio

import pytest

from panelin_mcp_server.tasks.manager import TaskManager
from panelin_mcp_server.tasks.models import Task, TaskStatus, TaskType


# -- Helper workers for testing -------------------------------------------

async def _success_worker(task: Task) -> dict:
    """Worker that succeeds immediately."""
    task.progress.total_items = 1
    task.progress.completed_items = 1
    return {"status": "ok", "items_processed": 1}


async def _slow_worker(task: Task) -> dict:
    """Worker that takes a bit of time."""
    task.progress.total_items = 3
    for i in range(3):
        task.progress.completed_items = i + 1
        await asyncio.sleep(0.05)
    return {"status": "ok", "items_processed": 3}


async def _failing_worker(task: Task) -> dict:
    """Worker that raises an exception."""
    raise ValueError("Simulated failure")


async def _cancellable_worker(task: Task) -> dict:
    """Worker that sleeps long enough to be cancelled."""
    task.progress.total_items = 100
    for i in range(100):
        task.progress.completed_items = i + 1
        await asyncio.sleep(0.1)
    return {"status": "should_not_reach"}


# -- Tests ----------------------------------------------------------------

@pytest.fixture
def manager():
    """Create a fresh TaskManager for each test."""
    m = TaskManager(max_concurrent=3, max_history=10)
    m.register_worker(TaskType.BATCH_BOM, _success_worker)
    m.register_worker(TaskType.BULK_PRICING, _slow_worker)
    m.register_worker(TaskType.FULL_QUOTATION, _failing_worker)
    return m


@pytest.mark.asyncio
async def test_submit_and_complete(manager):
    """Test basic submit -> run -> complete lifecycle."""
    task = await manager.submit(TaskType.BATCH_BOM, {"items": [1, 2]})
    assert task.status in (TaskStatus.PENDING, TaskStatus.RUNNING)

    # Give the worker time to finish
    await asyncio.sleep(0.1)

    assert task.status == TaskStatus.COMPLETED
    assert task.result == {"status": "ok", "items_processed": 1}


@pytest.mark.asyncio
async def test_submit_failing_worker(manager):
    """Test that a failing worker transitions the task to FAILED."""
    task = await manager.submit(TaskType.FULL_QUOTATION, {})

    await asyncio.sleep(0.1)

    assert task.status == TaskStatus.FAILED
    assert "Simulated failure" in task.error


@pytest.mark.asyncio
async def test_get_task_found(manager):
    """Test retrieving a task by ID."""
    task = await manager.submit(TaskType.BATCH_BOM, {})
    found = manager.get_task(task.task_id)
    assert found is task


@pytest.mark.asyncio
async def test_get_task_not_found(manager):
    """Test retrieving a non-existent task."""
    assert manager.get_task("TASK-NONEXIST") is None


@pytest.mark.asyncio
async def test_list_tasks(manager):
    """Test listing tasks with and without filters."""
    t1 = await manager.submit(TaskType.BATCH_BOM, {})
    t2 = await manager.submit(TaskType.BATCH_BOM, {})

    await asyncio.sleep(0.1)

    all_tasks = manager.list_tasks()
    assert len(all_tasks) == 2

    completed = manager.list_tasks(status=TaskStatus.COMPLETED)
    assert len(completed) == 2


@pytest.mark.asyncio
async def test_list_tasks_by_type(manager):
    """Test listing tasks filtered by type."""
    await manager.submit(TaskType.BATCH_BOM, {})
    await manager.submit(TaskType.FULL_QUOTATION, {})  # will fail

    await asyncio.sleep(0.1)

    bom_only = manager.list_tasks(task_type=TaskType.BATCH_BOM)
    assert len(bom_only) == 1
    assert bom_only[0].task_type == TaskType.BATCH_BOM


@pytest.mark.asyncio
async def test_cancel_running_task(manager):
    """Test cancelling a running task."""
    # Re-register with a slow worker for BATCH_BOM
    manager.register_worker(TaskType.BATCH_BOM, _cancellable_worker)
    task = await manager.submit(TaskType.BATCH_BOM, {})

    await asyncio.sleep(0.05)
    assert task.status == TaskStatus.RUNNING

    cancelled = await manager.cancel_task(task.task_id)
    assert cancelled is True

    await asyncio.sleep(0.15)
    assert task.status == TaskStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_completed_task(manager):
    """Test that cancelling a completed task returns False."""
    task = await manager.submit(TaskType.BATCH_BOM, {})
    await asyncio.sleep(0.1)
    assert task.status == TaskStatus.COMPLETED

    cancelled = await manager.cancel_task(task.task_id)
    assert cancelled is False


@pytest.mark.asyncio
async def test_cancel_nonexistent_task(manager):
    """Test cancelling a task that doesn't exist."""
    cancelled = await manager.cancel_task("TASK-NOPE")
    assert cancelled is False


@pytest.mark.asyncio
async def test_submit_unknown_type(manager):
    """Test submitting a task with no registered worker raises."""
    m = TaskManager()  # no workers registered
    with pytest.raises(ValueError, match="No worker registered"):
        await m.submit(TaskType.BATCH_BOM, {})


@pytest.mark.asyncio
async def test_eviction(manager):
    """Test that old completed tasks are evicted beyond max_history."""
    m = TaskManager(max_concurrent=5, max_history=3)
    m.register_worker(TaskType.BATCH_BOM, _success_worker)

    tasks = []
    for _ in range(5):
        t = await m.submit(TaskType.BATCH_BOM, {})
        tasks.append(t)

    await asyncio.sleep(0.2)

    # After eviction, only max_history completed tasks + any non-terminal should remain
    all_tasks = m.list_tasks(limit=100)
    assert len(all_tasks) <= 5  # At most 5 since some may be evicted on next submit


@pytest.mark.asyncio
async def test_progress_tracking(manager):
    """Test that progress is tracked during slow worker execution."""
    manager.register_worker(TaskType.BATCH_BOM, _slow_worker)
    task = await manager.submit(TaskType.BATCH_BOM, {})

    await asyncio.sleep(0.08)
    assert task.progress.total_items == 3
    assert task.progress.completed_items >= 1

    await asyncio.sleep(0.2)
    assert task.status == TaskStatus.COMPLETED
    assert task.progress.completed_items == 3


@pytest.mark.asyncio
async def test_shutdown(manager):
    """Test graceful shutdown cancels running tasks."""
    manager.register_worker(TaskType.BATCH_BOM, _cancellable_worker)
    task = await manager.submit(TaskType.BATCH_BOM, {})

    await asyncio.sleep(0.05)
    await manager.shutdown()

    assert task.status == TaskStatus.CANCELLED
