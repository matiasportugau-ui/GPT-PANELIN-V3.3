"""Async Task Queue Implementation.

Provides a thread-safe async queue for managing background tasks with priority support.
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
from collections import defaultdict


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Task:
    """Represents a background task."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    func: Optional[Callable] = field(default=None, repr=False)
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary (excluding function)."""
        data = asdict(self)
        data.pop('func', None)  # Remove function as it's not serializable
        data['priority'] = self.priority.value
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        data['started_at'] = self.started_at.isoformat() if self.started_at else None
        data['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create task from dictionary."""
        data = data.copy()
        data['priority'] = TaskPriority(data.get('priority', TaskPriority.NORMAL.value))
        data['status'] = TaskStatus(data.get('status', TaskStatus.PENDING.value))
        
        # Convert ISO format strings back to datetime
        for field_name in ['created_at', 'started_at', 'completed_at']:
            if data.get(field_name):
                data[field_name] = datetime.fromisoformat(data[field_name])
        
        data.pop('func', None)  # Function not in serialized data
        return cls(**data)
    
    def __lt__(self, other: 'Task') -> bool:
        """Compare tasks by priority for priority queue."""
        return self.priority.value > other.priority.value  # Higher priority first


class TaskQueue:
    """Async task queue with persistence and priority support."""
    
    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize task queue.
        
        Args:
            storage_path: Path to store task state (JSON file)
        """
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._tasks: Dict[str, Task] = {}
        self._lock = asyncio.Lock()
        self._storage_path = storage_path or Path("task_queue_state.json")
        self._load_state()
    
    def _load_state(self) -> None:
        """Load persisted task state from disk."""
        if self._storage_path.exists():
            try:
                with open(self._storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for task_data in data.get('tasks', []):
                        task = Task.from_dict(task_data)
                        self._tasks[task.id] = task
                        # Re-queue pending tasks
                        if task.status == TaskStatus.PENDING:
                            self._queue.put_nowait((task.priority.value, task))
            except Exception as e:
                print(f"Warning: Could not load task state: {e}")
    
    async def _save_state(self) -> None:
        """Persist task state to disk."""
        async with self._lock:
            try:
                data = {
                    'tasks': [task.to_dict() for task in self._tasks.values()],
                    'saved_at': datetime.utcnow().isoformat()
                }
                with open(self._storage_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, default=str)
            except Exception as e:
                print(f"Warning: Could not save task state: {e}")
    
    async def enqueue(
        self,
        func: Callable,
        *args,
        name: Optional[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
        timeout: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Task:
        """Add a task to the queue.
        
        Args:
            func: Async or sync function to execute
            *args: Positional arguments for the function
            name: Human-readable task name
            priority: Task priority level
            max_retries: Maximum retry attempts
            timeout: Task execution timeout in seconds
            metadata: Additional task metadata
            **kwargs: Keyword arguments for the function
        
        Returns:
            Created Task object
        """
        task = Task(
            name=name or func.__name__,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            max_retries=max_retries,
            timeout=timeout,
            metadata=metadata or {}
        )
        
        async with self._lock:
            self._tasks[task.id] = task
            await self._queue.put((priority.value, task))
            await self._save_state()
        
        return task
    
    async def dequeue(self) -> Optional[Task]:
        """Get next task from queue.
        
        Returns:
            Next task or None if queue is empty
        """
        try:
            _, task = await asyncio.wait_for(self._queue.get(), timeout=0.1)
            return task
        except asyncio.TimeoutError:
            return None
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID.
        
        Args:
            task_id: Task identifier
        
        Returns:
            Task object or None if not found
        """
        async with self._lock:
            return self._tasks.get(task_id)
    
    async def update_task(self, task: Task) -> None:
        """Update task state.
        
        Args:
            task: Task object to update
        """
        async with self._lock:
            self._tasks[task.id] = task
            await self._save_state()
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task.
        
        Args:
            task_id: Task identifier
        
        Returns:
            True if cancelled, False if task not found or already running
        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.utcnow()
                await self._save_state()
                return True
            return False
    
    async def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get all tasks with specified status.
        
        Args:
            status: Task status to filter by
        
        Returns:
            List of matching tasks
        """
        async with self._lock:
            return [
                task for task in self._tasks.values()
                if task.status == status
            ]
    
    async def get_task_stats(self) -> Dict[str, int]:
        """Get task statistics.
        
        Returns:
            Dictionary with task counts by status
        """
        async with self._lock:
            stats = defaultdict(int)
            for task in self._tasks.values():
                stats[task.status.value] += 1
            return dict(stats)
    
    async def clear_completed(self, older_than_hours: int = 24) -> int:
        """Clear old completed tasks.
        
        Args:
            older_than_hours: Remove tasks completed more than this many hours ago
        
        Returns:
            Number of tasks removed
        """
        async with self._lock:
            cutoff = datetime.utcnow().timestamp() - (older_than_hours * 3600)
            to_remove = []
            
            for task_id, task in self._tasks.items():
                if (
                    task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
                    and task.completed_at
                    and task.completed_at.timestamp() < cutoff
                ):
                    to_remove.append(task_id)
            
            for task_id in to_remove:
                del self._tasks[task_id]
            
            if to_remove:
                await self._save_state()
            
            return len(to_remove)
    
    def size(self) -> int:
        """Get current queue size.
        
        Returns:
            Number of pending tasks in queue
        """
        return self._queue.qsize()
    
    async def close(self) -> None:
        """Close queue and save state."""
        await self._save_state()
