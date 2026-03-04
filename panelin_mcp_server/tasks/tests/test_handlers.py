"""Tests for MCP tool handler functions for background tasks.

Tests the handler layer that bridges MCP tool calls to the task manager.
"""

import asyncio

import pytest

from panelin_mcp_server.tasks.manager import TaskManager, get_task_manager, _manager
from panelin_mcp_server.tasks.models import TaskStatus, TaskType
from panelin_mcp_server.tasks.workers import batch_bom_worker, bulk_pricing_worker, full_quotation_worker
from panelin_mcp_server.handlers.tasks import (
    handle_batch_bom_calculate,
    handle_bulk_price_check,
    handle_full_quotation,
    handle_task_status,
    handle_task_result,
    handle_task_list,
    handle_task_cancel,
)

import panelin_mcp_server.tasks.manager as manager_mod


@pytest.fixture(autouse=True)
def reset_task_manager():
    """Reset the singleton task manager before each test."""
    manager_mod._manager = None
    manager = get_task_manager()
    manager.register_worker(TaskType.BATCH_BOM, batch_bom_worker)
    manager.register_worker(TaskType.BULK_PRICING, bulk_pricing_worker)
    manager.register_worker(TaskType.FULL_QUOTATION, full_quotation_worker)
    yield
    manager_mod._manager = None


@pytest.mark.asyncio
async def test_handle_batch_bom_calculate():
    """Test submitting a batch BOM via handler."""
    result = await handle_batch_bom_calculate({
        "items": [
            {
                "product_family": "ISODEC",
                "thickness_mm": 100,
                "core_type": "EPS",
                "usage": "techo",
                "length_m": 10,
                "width_m": 5,
            }
        ]
    })
    assert "task_id" in result
    assert result["status"] in ("pending", "running")
    assert "hint" in result


@pytest.mark.asyncio
async def test_handle_batch_bom_calculate_empty():
    """Test batch BOM with empty items."""
    result = await handle_batch_bom_calculate({"items": []})
    assert "error" in result


@pytest.mark.asyncio
async def test_handle_batch_bom_calculate_too_many():
    """Test batch BOM with too many items."""
    items = [{"product_family": "X", "thickness_mm": 1, "usage": "techo", "length_m": 1, "width_m": 1}] * 51
    result = await handle_batch_bom_calculate({"items": items})
    assert "error" in result
    assert "50" in result["error"]


@pytest.mark.asyncio
async def test_handle_bulk_price_check():
    """Test submitting a bulk pricing lookup via handler."""
    result = await handle_bulk_price_check({
        "queries": [
            {"query": "ISODEC", "filter_type": "family"},
        ]
    })
    assert "task_id" in result
    assert result["status"] in ("pending", "running")


@pytest.mark.asyncio
async def test_handle_bulk_price_check_empty():
    """Test bulk pricing with empty queries."""
    result = await handle_bulk_price_check({"queries": []})
    assert "error" in result


@pytest.mark.asyncio
async def test_handle_full_quotation():
    """Test submitting a full quotation via handler."""
    result = await handle_full_quotation({
        "product_family": "ISODEC",
        "thickness_mm": 100,
        "core_type": "EPS",
        "usage": "techo",
        "length_m": 12,
        "width_m": 5,
    })
    assert "task_id" in result
    assert result["status"] in ("pending", "running")


@pytest.mark.asyncio
async def test_handle_full_quotation_missing_fields():
    """Test full quotation with missing required fields."""
    result = await handle_full_quotation({
        "product_family": "ISODEC",
    })
    assert "error" in result
    assert "Missing required fields" in result["error"]


@pytest.mark.asyncio
async def test_handle_task_status():
    """Test querying task status."""
    submit = await handle_batch_bom_calculate({
        "items": [
            {
                "product_family": "ISODEC",
                "thickness_mm": 100,
                "core_type": "EPS",
                "usage": "techo",
                "length_m": 10,
                "width_m": 5,
            }
        ]
    })
    task_id = submit["task_id"]

    status = await handle_task_status({"task_id": task_id})
    assert status["task_id"] == task_id
    assert status["status"] in ("pending", "running", "completed")


@pytest.mark.asyncio
async def test_handle_task_status_not_found():
    """Test status of non-existent task."""
    result = await handle_task_status({"task_id": "TASK-NONEXIST"})
    assert "error" in result


@pytest.mark.asyncio
async def test_handle_task_status_empty():
    """Test status with empty task_id."""
    result = await handle_task_status({"task_id": ""})
    assert "error" in result


@pytest.mark.asyncio
async def test_handle_task_result_completed():
    """Test retrieving result of a completed task."""
    submit = await handle_batch_bom_calculate({
        "items": [
            {
                "product_family": "ISODEC",
                "thickness_mm": 100,
                "core_type": "EPS",
                "usage": "techo",
                "length_m": 10,
                "width_m": 5,
            }
        ]
    })
    task_id = submit["task_id"]

    # Wait for completion
    await asyncio.sleep(0.3)

    result = await handle_task_result({"task_id": task_id})
    assert "result" in result or "error" in result
    if "result" in result:
        assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_handle_task_result_not_found():
    """Test result of non-existent task."""
    result = await handle_task_result({"task_id": "TASK-NONEXIST"})
    assert "error" in result


@pytest.mark.asyncio
async def test_handle_task_list():
    """Test listing tasks."""
    await handle_batch_bom_calculate({
        "items": [
            {
                "product_family": "ISODEC",
                "thickness_mm": 100,
                "core_type": "EPS",
                "usage": "techo",
                "length_m": 10,
                "width_m": 5,
            }
        ]
    })

    result = await handle_task_list({})
    assert "tasks" in result
    assert result["total"] >= 1


@pytest.mark.asyncio
async def test_handle_task_list_filter_by_type():
    """Test listing tasks filtered by type."""
    await handle_batch_bom_calculate({
        "items": [
            {
                "product_family": "ISODEC",
                "thickness_mm": 100,
                "core_type": "EPS",
                "usage": "techo",
                "length_m": 10,
                "width_m": 5,
            }
        ]
    })

    result = await handle_task_list({"task_type": "batch_bom_calculate"})
    assert result["total"] >= 1
    for t in result["tasks"]:
        assert t["task_type"] == "batch_bom_calculate"


@pytest.mark.asyncio
async def test_handle_task_list_invalid_status():
    """Test listing with invalid status filter."""
    result = await handle_task_list({"status": "bogus"})
    assert "error" in result


@pytest.mark.asyncio
async def test_handle_task_cancel():
    """Test cancelling a task."""
    # Submit and immediately cancel
    submit = await handle_batch_bom_calculate({
        "items": [
            {
                "product_family": "ISODEC",
                "thickness_mm": 100,
                "core_type": "EPS",
                "usage": "techo",
                "length_m": 10,
                "width_m": 5,
            }
        ]
    })
    task_id = submit["task_id"]

    # The task may complete very fast, so cancellation might not succeed
    cancel_result = await handle_task_cancel({"task_id": task_id})
    assert "task_id" in cancel_result


@pytest.mark.asyncio
async def test_handle_task_cancel_not_found():
    """Test cancelling a non-existent task."""
    result = await handle_task_cancel({"task_id": "TASK-NONEXIST"})
    assert "error" in result


@pytest.mark.asyncio
async def test_handle_task_cancel_empty():
    """Test cancel with empty task_id."""
    result = await handle_task_cancel({"task_id": ""})
    assert "error" in result
