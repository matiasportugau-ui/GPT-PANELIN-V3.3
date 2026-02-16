"""Task Worker Implementation.

Provides worker processes that execute tasks from the queue with retry logic.
"""

import asyncio
import inspect
import logging
import traceback
from datetime import datetime
from typing import Optional

from .queue import Task, TaskQueue, TaskStatus

logger = logging.getLogger(__name__)


class TaskWorker:
    """Worker that processes tasks from the queue."""
    
    def __init__(
        self,
        queue: TaskQueue,
        worker_id: Optional[str] = None,
        max_concurrent_tasks: int = 5
    ):
        """Initialize task worker.
        
        Args:
            queue: TaskQueue instance to process
            worker_id: Unique worker identifier
            max_concurrent_tasks: Maximum tasks to run concurrently
        """
        self.queue = queue
        self.worker_id = worker_id or "worker-1"
        self.max_concurrent_tasks = max_concurrent_tasks
        self._running = False
        self._semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self._active_tasks: set[asyncio.Task] = set()
    
    async def start(self) -> None:
        """Start the worker."""
        self._running = True
        logger.info(f"Worker {self.worker_id} started")
        
        while self._running:
            try:
                task = await self.queue.dequeue()
                if task:
                    # Create async task to process
                    async_task = asyncio.create_task(self._process_task(task))
                    self._active_tasks.add(async_task)
                    async_task.add_done_callback(self._active_tasks.discard)
                else:
                    # No tasks, sleep briefly
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {e}")
                await asyncio.sleep(1)
    
    async def stop(self) -> None:
        """Stop the worker gracefully."""
        logger.info(f"Worker {self.worker_id} stopping...")
        self._running = False
        
        # Wait for active tasks to complete
        if self._active_tasks:
            logger.info(f"Waiting for {len(self._active_tasks)} active tasks to complete...")
            await asyncio.gather(*self._active_tasks, return_exceptions=True)
        
        logger.info(f"Worker {self.worker_id} stopped")
    
    async def _process_task(self, task: Task) -> None:
        """Process a single task with retry logic.
        
        Args:
            task: Task to process
        """
        async with self._semaphore:
            while task.retry_count <= task.max_retries:
                try:
                    # Update task status
                    task.status = TaskStatus.RUNNING if task.retry_count == 0 else TaskStatus.RETRYING
                    task.started_at = datetime.utcnow()
                    await self.queue.update_task(task)
                    
                    logger.info(
                        f"Processing task {task.id} ({task.name}) "
                        f"[attempt {task.retry_count + 1}/{task.max_retries + 1}]"
                    )
                    
                    # Execute the task function
                    result = await self._execute_task_function(task)
                    
                    # Task completed successfully
                    task.status = TaskStatus.COMPLETED
                    task.result = result
                    task.completed_at = datetime.utcnow()
                    await self.queue.update_task(task)
                    
                    logger.info(f"Task {task.id} ({task.name}) completed successfully")
                    return
                
                except asyncio.CancelledError:
                    # Task was cancelled
                    task.status = TaskStatus.CANCELLED
                    task.completed_at = datetime.utcnow()
                    await self.queue.update_task(task)
                    logger.warning(f"Task {task.id} ({task.name}) was cancelled")
                    return
                
                except Exception as e:
                    task.retry_count += 1
                    error_msg = f"{type(e).__name__}: {str(e)}"
                    task.error = error_msg
                    
                    logger.error(
                        f"Task {task.id} ({task.name}) failed: {error_msg}\n"
                        f"Traceback:\n{traceback.format_exc()}"
                    )
                    
                    if task.retry_count > task.max_retries:
                        # Max retries exceeded
                        task.status = TaskStatus.FAILED
                        task.completed_at = datetime.utcnow()
                        await self.queue.update_task(task)
                        logger.error(
                            f"Task {task.id} ({task.name}) failed after "
                            f"{task.max_retries + 1} attempts"
                        )
                        return
                    else:
                        # Retry with exponential backoff
                        backoff_seconds = 2 ** task.retry_count
                        logger.info(
                            f"Retrying task {task.id} ({task.name}) in {backoff_seconds}s"
                        )
                        await asyncio.sleep(backoff_seconds)
    
    async def _execute_task_function(self, task: Task) -> any:
        """Execute the task function with timeout.
        
        Args:
            task: Task to execute
        
        Returns:
            Function result
        
        Raises:
            Any exception raised by the function
        """
        if not task.func:
            raise ValueError(f"Task {task.id} has no function to execute")
        
        # Determine if function is async or sync
        if inspect.iscoroutinefunction(task.func):
            # Async function
            if task.timeout:
                result = await asyncio.wait_for(
                    task.func(*task.args, **task.kwargs),
                    timeout=task.timeout
                )
            else:
                result = await task.func(*task.args, **task.kwargs)
        else:
            # Sync function - run in executor
            loop = asyncio.get_running_loop()
            if task.timeout:
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, task.func, *task.args, **task.kwargs),
                    timeout=task.timeout
                )
            else:
                result = await loop.run_in_executor(
                    None, task.func, *task.args, **task.kwargs
                )
        
        return result
    
    def get_active_task_count(self) -> int:
        """Get number of currently executing tasks.
        
        Returns:
            Number of active tasks
        """
        return len(self._active_tasks)
    
    def is_running(self) -> bool:
        """Check if worker is running.
        
        Returns:
            True if worker is running
        """
        return self._running
