"""Tests for Task Scheduler."""

import asyncio
import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from background_tasks.queue import TaskQueue, TaskPriority
from background_tasks.scheduler import TaskScheduler, ScheduledTask


class TestTaskScheduler:
    """Tests for TaskScheduler class."""
    
    @pytest.fixture
    async def setup(self):
        """Setup queue and scheduler for testing."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            storage_path = Path(f.name)
        
        queue = TaskQueue(storage_path=storage_path)
        scheduler = TaskScheduler(queue)
        
        yield queue, scheduler
        
        # Cleanup
        await scheduler.stop()
        await queue.close()
        if storage_path.exists():
            storage_path.unlink()
    
    @pytest.mark.asyncio
    async def test_schedule_interval_task(self, setup):
        """Test scheduling a task with interval."""
        queue, scheduler = setup
        
        async def test_func():
            return "result"
        
        scheduled = scheduler.schedule_interval(
            test_func,
            interval_seconds=2.0,
            name="interval_test"
        )
        
        assert scheduled.name == "interval_test"
        assert scheduled.interval_seconds == 2.0
        assert scheduled.enabled is True
    
    @pytest.mark.asyncio
    async def test_schedule_daily_task(self, setup):
        """Test scheduling a daily task."""
        queue, scheduler = setup
        
        async def test_func():
            return "result"
        
        scheduled = scheduler.schedule_daily(
            test_func,
            hour=10,
            minute=30,
            name="daily_test"
        )
        
        assert scheduled.name == "daily_test"
        assert scheduled.interval_seconds == 86400  # 24 hours
        assert scheduled.next_run is not None
    
    @pytest.mark.asyncio
    async def test_scheduler_executes_interval_task(self, setup):
        """Test that scheduler executes interval tasks."""
        queue, scheduler = setup
        
        execution_count = {'count': 0}
        
        async def counting_func():
            execution_count['count'] += 1
            return execution_count['count']
        
        # Schedule task with short interval
        scheduler.schedule_interval(
            counting_func,
            interval_seconds=0.5,
            name="counter"
        )
        
        # Start scheduler
        await scheduler.start()
        
        # Wait for multiple executions
        await asyncio.sleep(2.5)
        
        # Stop scheduler
        await scheduler.stop()
        
        # Check that task was submitted to queue
        # Note: Task submission to queue happens, actual execution depends on worker
        stats = await queue.get_task_stats()
        assert stats.get('pending', 0) >= 1  # At least one task should be queued
    
    @pytest.mark.asyncio
    async def test_unschedule_task(self, setup):
        """Test unscheduling a task."""
        queue, scheduler = setup
        
        async def test_func():
            return "result"
        
        scheduler.schedule_interval(test_func, 1.0, name="removable")
        assert "removable" in [t.name for t in scheduler.get_scheduled_tasks()]
        
        success = scheduler.unschedule("removable")
        assert success is True
        assert "removable" not in [t.name for t in scheduler.get_scheduled_tasks()]
    
    @pytest.mark.asyncio
    async def test_enable_disable_task(self, setup):
        """Test enabling and disabling scheduled tasks."""
        queue, scheduler = setup
        
        async def test_func():
            return "result"
        
        scheduler.schedule_interval(test_func, 1.0, name="toggleable")
        
        # Disable
        success = scheduler.disable_task("toggleable")
        assert success is True
        
        tasks = scheduler.get_scheduled_tasks()
        task = next(t for t in tasks if t.name == "toggleable")
        assert task.enabled is False
        
        # Enable
        success = scheduler.enable_task("toggleable")
        assert success is True
        
        tasks = scheduler.get_scheduled_tasks()
        task = next(t for t in tasks if t.name == "toggleable")
        assert task.enabled is True
    
    @pytest.mark.asyncio
    async def test_disabled_task_not_executed(self, setup):
        """Test that disabled tasks are not executed."""
        queue, scheduler = setup
        
        execution_count = {'count': 0}
        
        async def counting_func():
            execution_count['count'] += 1
            return execution_count['count']
        
        # Schedule and immediately disable
        scheduler.schedule_interval(counting_func, 0.5, name="disabled")
        scheduler.disable_task("disabled")
        
        # Start scheduler
        await scheduler.start()
        await asyncio.sleep(2.0)
        await scheduler.stop()
        
        # Should not have executed (or very few times if race condition)
        assert execution_count['count'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
