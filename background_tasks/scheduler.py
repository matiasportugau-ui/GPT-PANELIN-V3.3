"""Task Scheduler Implementation.

Provides scheduling functionality for periodic and cron-like tasks.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional

from .queue import TaskQueue, TaskPriority

logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    """Represents a scheduled task."""
    
    name: str
    func: Callable
    interval_seconds: Optional[float] = None
    cron_expr: Optional[str] = None
    priority: TaskPriority = TaskPriority.NORMAL
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    error_count: int = 0


class TaskScheduler:
    """Scheduler for periodic and cron-like tasks."""
    
    def __init__(self, queue: TaskQueue):
        """Initialize task scheduler.
        
        Args:
            queue: TaskQueue to submit scheduled tasks to
        """
        self.queue = queue
        self._scheduled_tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
    
    def schedule_interval(
        self,
        func: Callable,
        interval_seconds: float,
        name: Optional[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        *args,
        **kwargs
    ) -> ScheduledTask:
        """Schedule a task to run at fixed intervals.
        
        Args:
            func: Function to execute
            interval_seconds: Interval between executions in seconds
            name: Task name (defaults to function name)
            priority: Task priority
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
        
        Returns:
            ScheduledTask object
        """
        task_name = name or func.__name__
        
        scheduled_task = ScheduledTask(
            name=task_name,
            func=func,
            interval_seconds=interval_seconds,
            priority=priority,
            args=args,
            kwargs=kwargs,
            next_run=datetime.utcnow() + timedelta(seconds=interval_seconds)
        )
        
        self._scheduled_tasks[task_name] = scheduled_task
        logger.info(f"Scheduled interval task: {task_name} (every {interval_seconds}s)")
        
        return scheduled_task
    
    def schedule_daily(
        self,
        func: Callable,
        hour: int = 0,
        minute: int = 0,
        name: Optional[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        *args,
        **kwargs
    ) -> ScheduledTask:
        """Schedule a task to run daily at a specific time.
        
        Args:
            func: Function to execute
            hour: Hour to run (0-23)
            minute: Minute to run (0-59)
            name: Task name (defaults to function name)
            priority: Task priority
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
        
        Returns:
            ScheduledTask object
        """
        task_name = name or func.__name__
        
        # Calculate next run time
        now = datetime.utcnow()
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if next_run <= now:
            # If time has passed today, schedule for tomorrow
            next_run += timedelta(days=1)
        
        scheduled_task = ScheduledTask(
            name=task_name,
            func=func,
            interval_seconds=86400,  # 24 hours
            priority=priority,
            args=args,
            kwargs=kwargs,
            next_run=next_run
        )
        
        self._scheduled_tasks[task_name] = scheduled_task
        logger.info(
            f"Scheduled daily task: {task_name} "
            f"at {hour:02d}:{minute:02d} UTC (next run: {next_run})"
        )
        
        return scheduled_task
    
    def unschedule(self, task_name: str) -> bool:
        """Remove a scheduled task.
        
        Args:
            task_name: Name of task to remove
        
        Returns:
            True if task was removed, False if not found
        """
        if task_name in self._scheduled_tasks:
            del self._scheduled_tasks[task_name]
            logger.info(f"Unscheduled task: {task_name}")
            return True
        return False
    
    def enable_task(self, task_name: str) -> bool:
        """Enable a scheduled task.
        
        Args:
            task_name: Name of task to enable
        
        Returns:
            True if task was enabled, False if not found
        """
        task = self._scheduled_tasks.get(task_name)
        if task:
            task.enabled = True
            logger.info(f"Enabled scheduled task: {task_name}")
            return True
        return False
    
    def disable_task(self, task_name: str) -> bool:
        """Disable a scheduled task.
        
        Args:
            task_name: Name of task to disable
        
        Returns:
            True if task was disabled, False if not found
        """
        task = self._scheduled_tasks.get(task_name)
        if task:
            task.enabled = False
            logger.info(f"Disabled scheduled task: {task_name}")
            return True
        return False
    
    def get_scheduled_tasks(self) -> List[ScheduledTask]:
        """Get all scheduled tasks.
        
        Returns:
            List of scheduled tasks
        """
        return list(self._scheduled_tasks.values())
    
    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler is already running")
            return
        
        self._running = True
        self._scheduler_task = asyncio.create_task(self._run_scheduler())
        logger.info("Task scheduler started")
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            return
        
        logger.info("Stopping task scheduler...")
        self._running = False
        
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Task scheduler stopped")
    
    async def _run_scheduler(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                now = datetime.utcnow()
                
                for task_name, scheduled_task in self._scheduled_tasks.items():
                    if not scheduled_task.enabled:
                        continue
                    
                    # Check if task should run
                    if scheduled_task.next_run and now >= scheduled_task.next_run:
                        try:
                            # Submit task to queue
                            await self.queue.enqueue(
                                scheduled_task.func,
                                *scheduled_task.args,
                                name=f"scheduled:{task_name}",
                                priority=scheduled_task.priority,
                                **scheduled_task.kwargs
                            )
                            
                            # Update scheduled task
                            scheduled_task.last_run = now
                            scheduled_task.run_count += 1
                            
                            # Calculate next run time
                            if scheduled_task.interval_seconds:
                                scheduled_task.next_run = (
                                    now + timedelta(seconds=scheduled_task.interval_seconds)
                                )
                            
                            logger.info(
                                f"Submitted scheduled task {task_name} "
                                f"(run #{scheduled_task.run_count})"
                            )
                        
                        except Exception as e:
                            scheduled_task.error_count += 1
                            logger.error(
                                f"Error submitting scheduled task {task_name}: {e}"
                            )
                
                # Sleep for 1 second before next check
                await asyncio.sleep(1)
            
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(5)
    
    def is_running(self) -> bool:
        """Check if scheduler is running.
        
        Returns:
            True if scheduler is running
        """
        return self._running
