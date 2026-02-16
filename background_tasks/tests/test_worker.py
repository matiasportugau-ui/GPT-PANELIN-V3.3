"""Tests for Task Worker."""

import asyncio
import pytest
import tempfile
from pathlib import Path

from background_tasks.queue import TaskQueue, TaskStatus, TaskPriority
from background_tasks.worker import TaskWorker


class TestTaskWorker:
    """Tests for TaskWorker class."""
    
    @pytest.fixture
    async def setup(self):
        """Setup queue and worker for testing."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            storage_path = Path(f.name)
        
        queue = TaskQueue(storage_path=storage_path)
        worker = TaskWorker(queue, worker_id="test-worker", max_concurrent_tasks=2)
        
        yield queue, worker
        
        # Cleanup
        await worker.stop()
        await queue.close()
        if storage_path.exists():
            storage_path.unlink()
    
    @pytest.mark.asyncio
    async def test_worker_starts_and_stops(self, setup):
        """Test worker lifecycle."""
        queue, worker = setup
        
        # Start worker
        worker_task = asyncio.create_task(worker.start())
        await asyncio.sleep(0.1)
        
        assert worker.is_running() is True
        
        # Stop worker
        await worker.stop()
        assert worker.is_running() is False
    
    @pytest.mark.asyncio
    async def test_worker_processes_task(self, setup):
        """Test that worker processes a task successfully."""
        queue, worker = setup
        
        # Define test function
        async def test_func(value):
            await asyncio.sleep(0.1)
            return value * 2
        
        # Enqueue task
        task = await queue.enqueue(test_func, 5, name="multiply")
        
        # Start worker
        worker_task = asyncio.create_task(worker.start())
        
        # Wait for task to complete
        for _ in range(50):  # Max 5 seconds
            await asyncio.sleep(0.1)
            updated_task = await queue.get_task(task.id)
            if updated_task.status == TaskStatus.COMPLETED:
                break
        
        # Stop worker
        await worker.stop()
        
        # Check result
        final_task = await queue.get_task(task.id)
        assert final_task.status == TaskStatus.COMPLETED
        assert final_task.result == 10
    
    @pytest.mark.asyncio
    async def test_worker_handles_sync_function(self, setup):
        """Test that worker can handle synchronous functions."""
        queue, worker = setup
        
        # Define sync function
        def sync_func(value):
            return value + 10
        
        # Enqueue task
        task = await queue.enqueue(sync_func, 5, name="add")
        
        # Start worker
        worker_task = asyncio.create_task(worker.start())
        
        # Wait for task to complete
        for _ in range(50):
            await asyncio.sleep(0.1)
            updated_task = await queue.get_task(task.id)
            if updated_task.status == TaskStatus.COMPLETED:
                break
        
        # Stop worker
        await worker.stop()
        
        # Check result
        final_task = await queue.get_task(task.id)
        assert final_task.status == TaskStatus.COMPLETED
        assert final_task.result == 15
    
    @pytest.mark.asyncio
    async def test_worker_retries_on_failure(self, setup):
        """Test that worker retries failed tasks."""
        queue, worker = setup
        
        # Counter to track attempts
        attempt_count = {'count': 0}
        
        async def failing_func():
            attempt_count['count'] += 1
            if attempt_count['count'] < 3:
                raise ValueError("Intentional failure")
            return "success"
        
        # Enqueue task with retries
        task = await queue.enqueue(
            failing_func,
            name="retry_test",
            max_retries=3
        )
        
        # Start worker
        worker_task = asyncio.create_task(worker.start())
        
        # Wait for task to complete
        for _ in range(100):  # Allow time for retries
            await asyncio.sleep(0.1)
            updated_task = await queue.get_task(task.id)
            if updated_task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                break
        
        # Stop worker
        await worker.stop()
        
        # Check that task succeeded after retries
        final_task = await queue.get_task(task.id)
        assert final_task.status == TaskStatus.COMPLETED
        assert final_task.result == "success"
        assert final_task.retry_count >= 2
    
    @pytest.mark.asyncio
    async def test_worker_fails_after_max_retries(self, setup):
        """Test that task fails after exceeding max retries."""
        queue, worker = setup
        
        async def always_failing_func():
            raise ValueError("Always fails")
        
        # Enqueue task with limited retries
        task = await queue.enqueue(
            always_failing_func,
            name="fail_test",
            max_retries=2
        )
        
        # Start worker
        worker_task = asyncio.create_task(worker.start())
        
        # Wait for task to fail
        for _ in range(100):
            await asyncio.sleep(0.1)
            updated_task = await queue.get_task(task.id)
            if updated_task.status == TaskStatus.FAILED:
                break
        
        # Stop worker
        await worker.stop()
        
        # Check that task failed
        final_task = await queue.get_task(task.id)
        assert final_task.status == TaskStatus.FAILED
        assert final_task.retry_count > 2
        assert "ValueError" in final_task.error
    
    @pytest.mark.asyncio
    async def test_worker_respects_timeout(self, setup):
        """Test that worker enforces task timeouts."""
        queue, worker = setup
        
        async def slow_func():
            await asyncio.sleep(10)  # Takes too long
            return "done"
        
        # Enqueue task with short timeout
        task = await queue.enqueue(
            slow_func,
            name="timeout_test",
            timeout=0.5,
            max_retries=0  # Don't retry
        )
        
        # Start worker
        worker_task = asyncio.create_task(worker.start())
        
        # Wait for task to timeout
        for _ in range(50):
            await asyncio.sleep(0.1)
            updated_task = await queue.get_task(task.id)
            if updated_task.status == TaskStatus.FAILED:
                break
        
        # Stop worker
        await worker.stop()
        
        # Check that task failed due to timeout
        final_task = await queue.get_task(task.id)
        assert final_task.status == TaskStatus.FAILED
        assert "TimeoutError" in final_task.error or "asyncio.exceptions.TimeoutError" in final_task.error


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
