"""Tests for Task Queue."""

import asyncio
import json
import pytest
import tempfile
from pathlib import Path

from background_tasks.queue import Task, TaskQueue, TaskStatus, TaskPriority


class TestTask:
    """Tests for Task class."""
    
    def test_task_creation(self):
        """Test creating a task."""
        task = Task(name="test_task")
        assert task.id is not None
        assert task.name == "test_task"
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.NORMAL
    
    def test_task_to_dict(self):
        """Test task serialization to dict."""
        task = Task(name="test_task", priority=TaskPriority.HIGH)
        data = task.to_dict()
        
        assert data['name'] == "test_task"
        assert data['priority'] == TaskPriority.HIGH.value
        assert data['status'] == TaskStatus.PENDING.value
        assert 'func' not in data  # Function should not be serialized
    
    def test_task_from_dict(self):
        """Test task deserialization from dict."""
        data = {
            'id': 'test-123',
            'name': 'test_task',
            'priority': TaskPriority.HIGH.value,
            'status': TaskStatus.COMPLETED.value,
            'created_at': '2026-02-13T10:00:00'
        }
        
        task = Task.from_dict(data)
        assert task.id == 'test-123'
        assert task.name == 'test_task'
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.COMPLETED


class TestTaskQueue:
    """Tests for TaskQueue class."""
    
    @pytest.fixture
    async def queue(self):
        """Create a task queue for testing."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            storage_path = Path(f.name)
        
        queue = TaskQueue(storage_path=storage_path)
        yield queue
        
        # Cleanup
        await queue.close()
        if storage_path.exists():
            storage_path.unlink()
    
    @pytest.mark.asyncio
    async def test_enqueue_task(self, queue):
        """Test enqueueing a task."""
        async def test_func():
            return "result"
        
        task = await queue.enqueue(test_func, name="test")
        
        assert task.id is not None
        assert task.name == "test"
        assert task.status == TaskStatus.PENDING
        assert queue.size() == 1
    
    @pytest.mark.asyncio
    async def test_dequeue_task(self, queue):
        """Test dequeueing a task."""
        async def test_func():
            return "result"
        
        enqueued_task = await queue.enqueue(test_func, name="test")
        dequeued_task = await queue.dequeue()
        
        assert dequeued_task is not None
        assert dequeued_task.id == enqueued_task.id
    
    @pytest.mark.asyncio
    async def test_priority_ordering(self, queue):
        """Test that higher priority tasks are dequeued first."""
        async def test_func():
            return "result"
        
        low_task = await queue.enqueue(test_func, name="low", priority=TaskPriority.LOW)
        high_task = await queue.enqueue(test_func, name="high", priority=TaskPriority.HIGH)
        normal_task = await queue.enqueue(test_func, name="normal", priority=TaskPriority.NORMAL)
        
        first = await queue.dequeue()
        second = await queue.dequeue()
        third = await queue.dequeue()
        
        assert first.id == high_task.id
        assert second.id == normal_task.id
        assert third.id == low_task.id
    
    @pytest.mark.asyncio
    async def test_get_task_by_id(self, queue):
        """Test retrieving a task by ID."""
        async def test_func():
            return "result"
        
        task = await queue.enqueue(test_func, name="test")
        retrieved = await queue.get_task(task.id)
        
        assert retrieved is not None
        assert retrieved.id == task.id
        assert retrieved.name == "test"
    
    @pytest.mark.asyncio
    async def test_update_task(self, queue):
        """Test updating a task."""
        async def test_func():
            return "result"
        
        task = await queue.enqueue(test_func, name="test")
        task.status = TaskStatus.RUNNING
        task.result = "test result"
        
        await queue.update_task(task)
        retrieved = await queue.get_task(task.id)
        
        assert retrieved.status == TaskStatus.RUNNING
        assert retrieved.result == "test result"
    
    @pytest.mark.asyncio
    async def test_cancel_task(self, queue):
        """Test cancelling a task."""
        async def test_func():
            return "result"
        
        task = await queue.enqueue(test_func, name="test")
        success = await queue.cancel_task(task.id)
        
        assert success is True
        
        retrieved = await queue.get_task(task.id)
        assert retrieved.status == TaskStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_get_tasks_by_status(self, queue):
        """Test filtering tasks by status."""
        async def test_func():
            return "result"
        
        task1 = await queue.enqueue(test_func, name="task1")
        task2 = await queue.enqueue(test_func, name="task2")
        
        task1.status = TaskStatus.COMPLETED
        await queue.update_task(task1)
        
        completed_tasks = await queue.get_tasks_by_status(TaskStatus.COMPLETED)
        pending_tasks = await queue.get_tasks_by_status(TaskStatus.PENDING)
        
        assert len(completed_tasks) == 1
        assert completed_tasks[0].id == task1.id
        assert len(pending_tasks) == 1
        assert pending_tasks[0].id == task2.id
    
    @pytest.mark.asyncio
    async def test_get_task_stats(self, queue):
        """Test task statistics."""
        async def test_func():
            return "result"
        
        task1 = await queue.enqueue(test_func, name="task1")
        task2 = await queue.enqueue(test_func, name="task2")
        task3 = await queue.enqueue(test_func, name="task3")
        
        task1.status = TaskStatus.COMPLETED
        await queue.update_task(task1)
        
        task2.status = TaskStatus.FAILED
        await queue.update_task(task2)
        
        stats = await queue.get_task_stats()
        
        assert stats.get('completed', 0) == 1
        assert stats.get('failed', 0) == 1
        assert stats.get('pending', 0) == 1
    
    @pytest.mark.asyncio
    async def test_persistence(self):
        """Test that task state persists across queue instances."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            storage_path = Path(f.name)
        
        try:
            # Create queue and add tasks
            async def test_func():
                return "result"
            
            queue1 = TaskQueue(storage_path=storage_path)
            task = await queue1.enqueue(test_func, name="persistent_task")
            task_id = task.id
            await queue1.close()
            
            # Create new queue instance with same storage
            queue2 = TaskQueue(storage_path=storage_path)
            retrieved = await queue2.get_task(task_id)
            
            assert retrieved is not None
            assert retrieved.name == "persistent_task"
            await queue2.close()
        
        finally:
            if storage_path.exists():
                storage_path.unlink()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
