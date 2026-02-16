"""Decorators for Background Tasks.

Provides convenient decorators to mark functions as background or scheduled tasks.
"""

import functools
from typing import Any, Callable, Optional

from .queue import TaskPriority, TaskQueue


# Global queue instance (will be set by application)
_global_queue: Optional[TaskQueue] = None


def set_global_queue(queue: TaskQueue) -> None:
    """Set the global task queue instance.
    
    Args:
        queue: TaskQueue instance to use globally
    """
    global _global_queue
    _global_queue = queue


def get_global_queue() -> TaskQueue:
    """Get the global task queue instance.
    
    Returns:
        Global TaskQueue instance
    
    Raises:
        RuntimeError: If global queue not initialized
    """
    if _global_queue is None:
        raise RuntimeError(
            "Global task queue not initialized. "
            "Call set_global_queue() before using decorators."
        )
    return _global_queue


def background_task(
    name: Optional[str] = None,
    priority: TaskPriority = TaskPriority.NORMAL,
    max_retries: int = 3,
    timeout: Optional[float] = None
):
    """Decorator to mark a function as a background task.
    
    Usage:
        @background_task(name="generate_pdf", priority=TaskPriority.HIGH)
        async def generate_quotation_pdf(quotation_id: str) -> str:
            # Implementation
            return pdf_path
        
        # Call will return a Task object instead of executing directly
        task = generate_quotation_pdf(quotation_id="12345")
    
    Args:
        name: Task name (defaults to function name)
        priority: Task priority level
        max_retries: Maximum retry attempts
        timeout: Execution timeout in seconds
    
    Returns:
        Decorated function that returns Task when called
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            queue = get_global_queue()
            task = await queue.enqueue(
                func,
                *args,
                name=name or func.__name__,
                priority=priority,
                max_retries=max_retries,
                timeout=timeout,
                **kwargs
            )
            return task
        
        # Store original function for direct calls if needed
        wrapper.__background_task_func__ = func
        return wrapper
    
    return decorator


def scheduled_task(
    interval_seconds: Optional[float] = None,
    daily_at: Optional[tuple] = None,
    priority: TaskPriority = TaskPriority.NORMAL
):
    """Decorator to mark a function as a scheduled task.
    
    Usage:
        # Run every 300 seconds
        @scheduled_task(interval_seconds=300)
        async def cleanup_old_tasks():
            # Implementation
            pass
        
        # Run daily at 02:00 UTC
        @scheduled_task(daily_at=(2, 0))
        async def daily_report():
            # Implementation
            pass
    
    Args:
        interval_seconds: Interval between runs in seconds
        daily_at: Tuple of (hour, minute) for daily execution
        priority: Task priority level
    
    Returns:
        Decorated function (original function is returned, scheduling done separately)
    """
    def decorator(func: Callable) -> Callable:
        # Store scheduling metadata on function
        func.__scheduled_task__ = {
            'interval_seconds': interval_seconds,
            'daily_at': daily_at,
            'priority': priority
        }
        return func
    
    return decorator


def register_scheduled_tasks(scheduler, module) -> None:
    """Register all scheduled tasks from a module.
    
    Args:
        scheduler: TaskScheduler instance
        module: Python module containing scheduled tasks
    """
    import inspect
    
    for name, obj in inspect.getmembers(module):
        if inspect.isfunction(obj) and hasattr(obj, '__scheduled_task__'):
            config = obj.__scheduled_task__
            
            if config.get('interval_seconds'):
                scheduler.schedule_interval(
                    obj,
                    interval_seconds=config['interval_seconds'],
                    name=name,
                    priority=config.get('priority', TaskPriority.NORMAL)
                )
            elif config.get('daily_at'):
                hour, minute = config['daily_at']
                scheduler.schedule_daily(
                    obj,
                    hour=hour,
                    minute=minute,
                    name=name,
                    priority=config.get('priority', TaskPriority.NORMAL)
                )
