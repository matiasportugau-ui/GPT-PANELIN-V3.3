"""Command-line interface for background tasks management.

Provides CLI commands to start workers, manage tasks, and monitor status.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

from .queue import TaskQueue, TaskStatus
from .worker import TaskWorker
from .scheduler import TaskScheduler
from .decorators import set_global_queue, register_scheduled_tasks


def load_config(config_path: str = "background_tasks_config.json") -> dict:
    """Load configuration from JSON file."""
    path = Path(config_path)
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


async def start_worker(args):
    """Start background task worker."""
    config = load_config(args.config)
    queue_config = config.get('queue', {})
    worker_config = config.get('worker', {})
    
    # Create queue
    storage_path = queue_config.get('storage_path', 'task_queue_state.json')
    queue = TaskQueue(storage_path=Path(storage_path))
    set_global_queue(queue)
    
    # Create worker
    worker_id = args.worker_id or worker_config.get('worker_id', 'worker-1')
    max_concurrent = args.max_concurrent or worker_config.get('max_concurrent_tasks', 5)
    worker = TaskWorker(queue, worker_id=worker_id, max_concurrent_tasks=max_concurrent)
    
    # Create scheduler if enabled
    scheduler = None
    scheduler_config = config.get('scheduler', {})
    if scheduler_config.get('enable_on_startup', True):
        scheduler = TaskScheduler(queue)
        
        # Register scheduled tasks from tasks module
        try:
            from . import tasks
            register_scheduled_tasks(scheduler, tasks)
            await scheduler.start()
            print(f"✓ Scheduler started with {len(scheduler.get_scheduled_tasks())} tasks")
        except Exception as e:
            print(f"Warning: Could not start scheduler: {e}")
    
    print(f"✓ Worker {worker_id} starting...")
    print(f"  Max concurrent tasks: {max_concurrent}")
    print(f"  Storage: {storage_path}")
    print(f"  Queue size: {queue.size()}")
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        print("\n⚠ Stopping worker...")
        await worker.stop()
        if scheduler:
            await scheduler.stop()
        await queue.close()
        print("✓ Worker stopped")


async def list_tasks(args):
    """List tasks in queue."""
    config = load_config(args.config)
    storage_path = config.get('queue', {}).get('storage_path', 'task_queue_state.json')
    
    queue = TaskQueue(storage_path=Path(storage_path))
    
    if args.status:
        try:
            status = TaskStatus(args.status)
            tasks = await queue.get_tasks_by_status(status)
            print(f"\nTasks with status '{args.status}':")
        except ValueError:
            print(f"Error: Invalid status '{args.status}'")
            print(f"Valid statuses: {', '.join(s.value for s in TaskStatus)}")
            return
    else:
        tasks = list(queue._tasks.values())
        print(f"\nAll tasks:")
    
    if not tasks:
        print("  (none)")
    else:
        for task in tasks[:args.limit]:
            print(f"  {task.id[:8]}... | {task.name:20} | {task.status.value:10} | "
                  f"retries: {task.retry_count}/{task.max_retries}")
    
    await queue.close()


async def get_task_status(args):
    """Get status of a specific task."""
    config = load_config(args.config)
    storage_path = config.get('queue', {}).get('storage_path', 'task_queue_state.json')
    
    queue = TaskQueue(storage_path=Path(storage_path))
    task = await queue.get_task(args.task_id)
    
    if not task:
        print(f"Task not found: {args.task_id}")
        return
    
    print(f"\nTask: {task.id}")
    print(f"  Name: {task.name}")
    print(f"  Status: {task.status.value}")
    print(f"  Priority: {task.priority.name}")
    print(f"  Retries: {task.retry_count}/{task.max_retries}")
    print(f"  Created: {task.created_at}")
    if task.started_at:
        print(f"  Started: {task.started_at}")
    if task.completed_at:
        print(f"  Completed: {task.completed_at}")
    if task.result:
        print(f"  Result: {task.result}")
    if task.error:
        print(f"  Error: {task.error}")
    
    await queue.close()


async def show_stats(args):
    """Show task statistics."""
    config = load_config(args.config)
    storage_path = config.get('queue', {}).get('storage_path', 'task_queue_state.json')
    
    queue = TaskQueue(storage_path=Path(storage_path))
    stats = await queue.get_task_stats()
    
    print("\nTask Statistics:")
    print(f"  Pending:   {stats.get('pending', 0):5}")
    print(f"  Running:   {stats.get('running', 0):5}")
    print(f"  Retrying:  {stats.get('retrying', 0):5}")
    print(f"  Completed: {stats.get('completed', 0):5}")
    print(f"  Failed:    {stats.get('failed', 0):5}")
    print(f"  Cancelled: {stats.get('cancelled', 0):5}")
    print(f"  ─────────────────")
    print(f"  Total:     {sum(stats.values()):5}")
    
    await queue.close()


async def cleanup_tasks(args):
    """Clean up old completed tasks."""
    config = load_config(args.config)
    storage_path = config.get('queue', {}).get('storage_path', 'task_queue_state.json')
    
    queue = TaskQueue(storage_path=Path(storage_path))
    removed = await queue.clear_completed(older_than_hours=args.hours)
    
    print(f"✓ Removed {removed} tasks older than {args.hours} hours")
    
    await queue.close()


async def cancel_task(args):
    """Cancel a pending task."""
    config = load_config(args.config)
    storage_path = config.get('queue', {}).get('storage_path', 'task_queue_state.json')
    
    queue = TaskQueue(storage_path=Path(storage_path))
    success = await queue.cancel_task(args.task_id)
    
    if success:
        print(f"✓ Task {args.task_id} cancelled")
    else:
        print(f"✗ Could not cancel task {args.task_id} (not found or already running)")
    
    await queue.close()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Panelin Background Tasks CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--config',
        default='background_tasks_config.json',
        help='Path to configuration file'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Start worker command
    start_parser = subparsers.add_parser('start', help='Start background task worker')
    start_parser.add_argument('--worker-id', help='Worker identifier')
    start_parser.add_argument('--max-concurrent', type=int, help='Max concurrent tasks')
    
    # List tasks command
    list_parser = subparsers.add_parser('list', help='List tasks')
    list_parser.add_argument('--status', help='Filter by status')
    list_parser.add_argument('--limit', type=int, default=50, help='Maximum tasks to show')
    
    # Get task status command
    status_parser = subparsers.add_parser('status', help='Get task status')
    status_parser.add_argument('task_id', help='Task ID')
    
    # Show statistics command
    stats_parser = subparsers.add_parser('stats', help='Show task statistics')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old tasks')
    cleanup_parser.add_argument('--hours', type=int, default=24, help='Remove tasks older than N hours')
    
    # Cancel task command
    cancel_parser = subparsers.add_parser('cancel', help='Cancel a task')
    cancel_parser.add_argument('task_id', help='Task ID to cancel')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    command_map = {
        'start': start_worker,
        'list': list_tasks,
        'status': get_task_status,
        'stats': show_stats,
        'cleanup': cleanup_tasks,
        'cancel': cancel_task,
    }
    
    asyncio.run(command_map[args.command](args))


if __name__ == '__main__':
    main()
