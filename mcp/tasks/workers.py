"""Background worker functions for long-running operations.

Each worker receives a ``Task`` object and must return a dict result.
Workers update ``task.progress`` incrementally so callers can poll
progress via the ``task_status`` MCP tool.

Workers:
- ``batch_bom_worker``: Calculate BOM for multiple panel specifications.
- ``bulk_pricing_worker``: Look up pricing for multiple products.
- ``full_quotation_worker``: Combined BOM + pricing + accessories in one pass.
"""

from __future__ import annotations

import asyncio
from typing import Any

from .models import Task

# Import the existing synchronous handlers
from ..handlers.bom import handle_bom_calculate
from ..handlers.pricing import handle_price_check
from ..handlers.catalog import handle_catalog_search


async def batch_bom_worker(task: Task) -> dict[str, Any]:
    """Process multiple BOM calculations in a single background task.

    Expected ``task.arguments``::

        {
            "items": [
                {
                    "product_family": "ISODEC",
                    "thickness_mm": 100,
                    "core_type": "EPS",
                    "usage": "techo",
                    "length_m": 12,
                    "width_m": 5
                },
                ...
            ]
        }
    """
    items: list[dict[str, Any]] = task.arguments.get("items", [])
    if not items:
        raise ValueError("No items provided for batch BOM calculation")

    task.progress.total_items = len(items)
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for idx, item in enumerate(items):
        task.progress.current_item = (
            f"{item.get('product_family', '?')} "
            f"{item.get('core_type', '?')} "
            f"{item.get('thickness_mm', '?')}mm "
            f"({item.get('usage', '?')})"
        )

        try:
            result = await handle_bom_calculate(item)
            if "error" in result:
                errors.append({"index": idx, "input": item, "error": result["error"]})
            else:
                results.append({"index": idx, "input": item, "bom": result})
        except Exception as exc:
            errors.append({"index": idx, "input": item, "error": str(exc)})

        task.progress.completed_items = idx + 1

        # Small yield to keep the event loop responsive
        await asyncio.sleep(0)

    return {
        "task_type": "batch_bom_calculate",
        "total_requested": len(items),
        "successful": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors if errors else None,
        "source": "bom_rules.json + accessories_catalog.json",
    }


async def bulk_pricing_worker(task: Task) -> dict[str, Any]:
    """Look up pricing for multiple products in a single background task.

    Expected ``task.arguments``::

        {
            "queries": [
                {"query": "ISODEC", "filter_type": "family"},
                {"query": "ISODEC-100-1000", "filter_type": "sku"},
                ...
            ]
        }
    """
    queries: list[dict[str, Any]] = task.arguments.get("queries", [])
    if not queries:
        raise ValueError("No queries provided for bulk pricing lookup")

    task.progress.total_items = len(queries)
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for idx, query_args in enumerate(queries):
        task.progress.current_item = query_args.get("query", f"query #{idx}")

        try:
            result = await handle_price_check(query_args)
            if "error" in result:
                errors.append({"index": idx, "query": query_args, "error": result["error"]})
            else:
                results.append({"index": idx, "query": query_args, "pricing": result})
        except Exception as exc:
            errors.append({"index": idx, "query": query_args, "error": str(exc)})

        task.progress.completed_items = idx + 1
        await asyncio.sleep(0)

    return {
        "task_type": "bulk_price_check",
        "total_requested": len(queries),
        "successful": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors if errors else None,
        "source": "bromyros_pricing_master.json",
    }


async def full_quotation_worker(task: Task) -> dict[str, Any]:
    """Generate a complete quotation combining BOM + pricing + catalog data.

    This worker orchestrates multiple sub-operations:
    1. Calculate BOM for the given panel specification
    2. Look up pricing for the product family
    3. Search the catalog for complementary accessories
    4. Compile a unified quotation summary

    Expected ``task.arguments``::

        {
            "product_family": "ISODEC",
            "thickness_mm": 100,
            "core_type": "EPS",
            "usage": "techo",
            "length_m": 12,
            "width_m": 5,
            "quantity_panels": null,
            "client_name": "Empresa Constructora ABC",
            "project_name": "Galpón Industrial",
            "discount_percent": 5
        }
    """
    args = task.arguments

    # We have 3 main steps
    task.progress.total_items = 3
    task.progress.current_item = "Calculating BOM"

    # Step 1: BOM calculation
    bom_args = {
        "product_family": args.get("product_family", ""),
        "thickness_mm": args.get("thickness_mm", 0),
        "core_type": args.get("core_type", "EPS"),
        "usage": args.get("usage", ""),
        "length_m": args.get("length_m", 0),
        "width_m": args.get("width_m", 0),
    }
    qty = args.get("quantity_panels")
    if qty is not None:
        bom_args["quantity_panels"] = qty

    bom_result = await handle_bom_calculate(bom_args)
    task.progress.completed_items = 1
    await asyncio.sleep(0)

    # Step 2: Pricing lookup
    task.progress.current_item = "Looking up pricing"
    pricing_result = await handle_price_check({
        "query": args.get("product_family", ""),
        "filter_type": "family",
        "thickness_mm": args.get("thickness_mm"),
    })
    task.progress.completed_items = 2
    await asyncio.sleep(0)

    # Step 3: Catalog search for accessories
    task.progress.current_item = "Searching accessories catalog"
    usage = args.get("usage", "")
    catalog_result = await handle_catalog_search({
        "query": args.get("product_family", ""),
        "category": usage if usage in ("techo", "pared", "camara") else "all",
        "limit": 10,
    })
    task.progress.completed_items = 3

    # Compile the unified quotation
    discount = args.get("discount_percent", 0) or 0
    quotation: dict[str, Any] = {
        "task_type": "full_quotation",
        "quotation": {
            "client": args.get("client_name", "N/A"),
            "project": args.get("project_name", "N/A"),
            "product": f"{args.get('product_family', '?')} {args.get('core_type', '?')} {args.get('thickness_mm', '?')}mm",
            "usage": usage,
            "dimensions": {
                "length_m": args.get("length_m"),
                "width_m": args.get("width_m"),
            },
            "discount_percent": discount,
        },
        "bom": bom_result,
        "pricing": pricing_result,
        "catalog_matches": catalog_result,
        "notes": [
            "Prices in USD, IVA 22% included",
            "BOM is parametric estimate - verify against KB formulas",
            f"Discount of {discount}% applied where applicable" if discount > 0 else "No discount applied",
        ],
        "source": "bom_rules.json + bromyros_pricing_master.json + shopify_catalog_v1.json",
    }

    return quotation
