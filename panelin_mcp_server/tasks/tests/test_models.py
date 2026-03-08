"""Tests for background task data models."""

import pytest

from panelin_mcp_server.tasks.models import Task, TaskProgress, TaskStatus, TaskType


class TestTaskProgress:
    """Tests for TaskProgress dataclass."""

    def test_default_values(self):
        progress = TaskProgress()
        assert progress.total_items == 0
        assert progress.completed_items == 0
        assert progress.current_item == ""
        assert progress.percentage == 0.0

    def test_percentage_calculation(self):
        progress = TaskProgress(total_items=10, completed_items=3)
        assert progress.percentage == 30.0

    def test_percentage_zero_total(self):
        progress = TaskProgress(total_items=0, completed_items=0)
        assert progress.percentage == 0.0

    def test_percentage_all_complete(self):
        progress = TaskProgress(total_items=5, completed_items=5)
        assert progress.percentage == 100.0

    def test_to_dict(self):
        progress = TaskProgress(total_items=10, completed_items=7, current_item="ISODEC EPS 100mm")
        d = progress.to_dict()
        assert d["total_items"] == 10
        assert d["completed_items"] == 7
        assert d["current_item"] == "ISODEC EPS 100mm"
        assert d["percentage"] == 70.0


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_all_statuses(self):
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.CANCELLED == "cancelled"


class TestTaskType:
    """Tests for TaskType enum."""

    def test_all_types(self):
        assert TaskType.BATCH_BOM == "batch_bom_calculate"
        assert TaskType.BULK_PRICING == "bulk_price_check"
        assert TaskType.FULL_QUOTATION == "full_quotation"


class TestTask:
    """Tests for Task dataclass."""

    def _make_task(self, **kwargs) -> Task:
        defaults = {
            "task_id": "TASK-TEST0001",
            "task_type": TaskType.BATCH_BOM,
        }
        defaults.update(kwargs)
        return Task(**defaults)

    def test_default_state(self):
        task = self._make_task()
        assert task.task_id == "TASK-TEST0001"
        assert task.task_type == TaskType.BATCH_BOM
        assert task.status == TaskStatus.PENDING
        assert task.result is None
        assert task.error is None
        assert task.started_at is None
        assert task.completed_at is None
        assert task.created_at is not None

    def test_mark_running(self):
        task = self._make_task()
        task.mark_running()
        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None

    def test_mark_completed(self):
        task = self._make_task()
        task.mark_running()
        result = {"test": "data"}
        task.mark_completed(result)
        assert task.status == TaskStatus.COMPLETED
        assert task.result == result
        assert task.completed_at is not None

    def test_mark_failed(self):
        task = self._make_task()
        task.mark_running()
        task.mark_failed("Something went wrong")
        assert task.status == TaskStatus.FAILED
        assert task.error == "Something went wrong"
        assert task.completed_at is not None

    def test_mark_cancelled(self):
        task = self._make_task()
        task.mark_cancelled()
        assert task.status == TaskStatus.CANCELLED
        assert task.completed_at is not None

    def test_to_summary_pending(self):
        task = self._make_task()
        s = task.to_summary()
        assert s["task_id"] == "TASK-TEST0001"
        assert s["task_type"] == "batch_bom_calculate"
        assert s["status"] == "pending"
        assert "result" not in s
        assert "progress" not in s

    def test_to_summary_running(self):
        task = self._make_task()
        task.mark_running()
        task.progress.total_items = 5
        task.progress.completed_items = 2
        s = task.to_summary()
        assert s["status"] == "running"
        assert "progress" in s
        assert s["progress"]["percentage"] == 40.0

    def test_to_summary_failed(self):
        task = self._make_task()
        task.mark_running()
        task.mark_failed("Test error")
        s = task.to_summary()
        assert s["status"] == "failed"
        assert s["error"] == "Test error"

    def test_to_full_dict_completed(self):
        task = self._make_task(arguments={"items": [{"x": 1}]})
        task.mark_running()
        task.mark_completed({"answer": 42})
        d = task.to_full_dict()
        assert d["task_id"] == "TASK-TEST0001"
        assert d["result"] == {"answer": 42}
        assert d["arguments"] == {"items": [{"x": 1}]}
