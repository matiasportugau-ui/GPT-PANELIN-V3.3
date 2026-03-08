"""Tests for background worker functions.

These tests exercise the actual worker implementations against
the real KB data files in the repository.
"""

import pytest

from panelin_mcp_server.tasks.models import Task, TaskType
from panelin_mcp_server.tasks.workers import batch_bom_worker, bulk_pricing_worker, full_quotation_worker


def _make_task(task_type: TaskType, arguments: dict) -> Task:
    return Task(task_id="TASK-TESTWORK", task_type=task_type, arguments=arguments)


@pytest.mark.asyncio
async def test_batch_bom_worker_success():
    """Test batch BOM worker with valid items."""
    task = _make_task(TaskType.BATCH_BOM, {
        "items": [
            {
                "product_family": "ISODEC",
                "thickness_mm": 100,
                "core_type": "EPS",
                "usage": "techo",
                "length_m": 12,
                "width_m": 5,
            },
        ]
    })

    result = await batch_bom_worker(task)
    assert result["task_type"] == "batch_bom_calculate"
    assert result["total_requested"] == 1
    assert result["successful"] >= 0
    assert task.progress.completed_items == 1


@pytest.mark.asyncio
async def test_batch_bom_worker_multiple_items():
    """Test batch BOM with multiple items including an invalid one."""
    task = _make_task(TaskType.BATCH_BOM, {
        "items": [
            {
                "product_family": "ISODEC",
                "thickness_mm": 100,
                "core_type": "EPS",
                "usage": "techo",
                "length_m": 12,
                "width_m": 5,
            },
            {
                "product_family": "NONEXISTENT",
                "thickness_mm": 0,
                "core_type": "EPS",
                "usage": "techo",
                "length_m": 5,
                "width_m": 3,
            },
        ]
    })

    result = await batch_bom_worker(task)
    assert result["total_requested"] == 2
    assert task.progress.completed_items == 2
    # Second item should produce an error result (missing thickness or unknown family)
    assert result["successful"] + result["failed"] == 2


@pytest.mark.asyncio
async def test_batch_bom_worker_empty_items():
    """Test batch BOM worker with no items raises ValueError."""
    task = _make_task(TaskType.BATCH_BOM, {"items": []})
    with pytest.raises(ValueError, match="No items provided"):
        await batch_bom_worker(task)


@pytest.mark.asyncio
async def test_bulk_pricing_worker_success():
    """Test bulk pricing worker with valid queries."""
    task = _make_task(TaskType.BULK_PRICING, {
        "queries": [
            {"query": "ISODEC", "filter_type": "family"},
        ]
    })

    result = await bulk_pricing_worker(task)
    assert result["task_type"] == "bulk_price_check"
    assert result["total_requested"] == 1
    assert task.progress.completed_items == 1


@pytest.mark.asyncio
async def test_bulk_pricing_worker_multiple_queries():
    """Test bulk pricing with multiple queries."""
    task = _make_task(TaskType.BULK_PRICING, {
        "queries": [
            {"query": "ISODEC", "filter_type": "family"},
            {"query": "ISOROOF", "filter_type": "family"},
            {"query": "panel techo", "filter_type": "search"},
        ]
    })

    result = await bulk_pricing_worker(task)
    assert result["total_requested"] == 3
    assert task.progress.completed_items == 3


@pytest.mark.asyncio
async def test_bulk_pricing_worker_empty_queries():
    """Test bulk pricing worker with no queries raises ValueError."""
    task = _make_task(TaskType.BULK_PRICING, {"queries": []})
    with pytest.raises(ValueError, match="No queries provided"):
        await bulk_pricing_worker(task)


@pytest.mark.asyncio
async def test_full_quotation_worker():
    """Test full quotation worker completes all 3 phases."""
    task = _make_task(TaskType.FULL_QUOTATION, {
        "product_family": "ISODEC",
        "thickness_mm": 100,
        "core_type": "EPS",
        "usage": "techo",
        "length_m": 12,
        "width_m": 5,
        "client_name": "Test Client",
        "project_name": "Test Project",
        "discount_percent": 10,
    })

    result = await full_quotation_worker(task)
    assert result["task_type"] == "full_quotation"
    assert "quotation" in result
    assert "bom" in result
    assert "pricing" in result
    assert "catalog_matches" in result
    assert result["quotation"]["client"] == "Test Client"
    assert result["quotation"]["project"] == "Test Project"
    assert result["quotation"]["discount_percent"] == 10
    assert task.progress.completed_items == 3


@pytest.mark.asyncio
async def test_full_quotation_worker_minimal():
    """Test full quotation with minimal arguments."""
    task = _make_task(TaskType.FULL_QUOTATION, {
        "product_family": "ISOROOF",
        "thickness_mm": 80,
        "core_type": "EPS",
        "usage": "techo",
        "length_m": 8,
        "width_m": 4,
    })

    result = await full_quotation_worker(task)
    assert result["task_type"] == "full_quotation"
    assert result["quotation"]["client"] == "N/A"
    assert result["quotation"]["project"] == "N/A"
