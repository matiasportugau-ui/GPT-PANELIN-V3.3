"""Background Task Processing System for Panelin GPT.

This module provides async task queue infrastructure for long-running operations:
- PDF generation
- Large quotation calculations
- Data synchronization
- Scheduled periodic tasks

Features:
- Async task execution with queue management
- Task status tracking and persistence
- Automatic retry logic with exponential backoff
- Scheduled task execution
- Task result storage
"""

from .queue import TaskQueue, Task, TaskStatus
from .worker import TaskWorker
from .scheduler import TaskScheduler
from .decorators import background_task, scheduled_task

__all__ = [
    'TaskQueue',
    'Task',
    'TaskStatus',
    'TaskWorker',
    'TaskScheduler',
    'background_task',
    'scheduled_task',
]

__version__ = '1.0.0'
