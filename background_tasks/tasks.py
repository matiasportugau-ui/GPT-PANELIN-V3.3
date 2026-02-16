"""Predefined Background Tasks for Panelin.

Collection of background tasks for common operations like PDF generation,
data synchronization, and cleanup.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .decorators import background_task, scheduled_task
from .queue import TaskPriority

logger = logging.getLogger(__name__)


@background_task(
    name="generate_pdf",
    priority=TaskPriority.HIGH,
    max_retries=2,
    timeout=60.0
)
async def generate_quotation_pdf(
    quotation_data: Dict[str, Any],
    output_path: Optional[str] = None
) -> str:
    """Generate PDF quotation in background.
    
    Args:
        quotation_data: Quotation data dictionary
        output_path: Optional output path for PDF
    
    Returns:
        Path to generated PDF file
    """
    logger.info(f"Generating PDF for quotation: {quotation_data.get('quotation_id', 'unknown')}")
    
    try:
        # Import PDF generator (lazy import to avoid circular dependencies)
        from panelin_reports.pdf_generator import generate_quotation_pdf as gen_pdf
        
        # Generate PDF (this runs in executor since it's sync)
        loop = asyncio.get_event_loop()
        pdf_path = await loop.run_in_executor(
            None,
            gen_pdf,
            quotation_data,
            output_path
        )
        
        logger.info(f"PDF generated successfully: {pdf_path}")
        return pdf_path
    
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise


@background_task(
    name="calculate_bom",
    priority=TaskPriority.NORMAL,
    max_retries=3,
    timeout=30.0
)
async def calculate_bom_async(
    product_family: str,
    thickness_mm: float,
    core_type: str,
    usage: str,
    length_m: float,
    width_m: float,
    quantity_panels: Optional[int] = None
) -> Dict[str, Any]:
    """Calculate Bill of Materials in background.
    
    Args:
        product_family: Panel family (ISODEC, ISOROOF, etc.)
        thickness_mm: Panel thickness
        core_type: Core type (EPS or PIR)
        usage: Usage type (techo, pared, camara)
        length_m: Installation length
        width_m: Installation width/span
        quantity_panels: Optional panel quantity
    
    Returns:
        Complete BOM dictionary
    """
    logger.info(f"Calculating BOM for {product_family} {thickness_mm}mm")
    
    try:
        # Import BOM calculator
        from quotation_calculator_v3 import calculate_complete_bom
        
        # Run calculation in executor
        loop = asyncio.get_event_loop()
        bom = await loop.run_in_executor(
            None,
            calculate_complete_bom,
            product_family,
            thickness_mm,
            core_type,
            usage,
            length_m,
            width_m,
            quantity_panels
        )
        
        logger.info(f"BOM calculated successfully for {product_family}")
        return bom
    
    except Exception as e:
        logger.error(f"BOM calculation failed: {e}")
        raise


@background_task(
    name="sync_pricing",
    priority=TaskPriority.LOW,
    max_retries=5,
    timeout=120.0
)
async def sync_pricing_data(
    source: str = "shopify",
    force_update: bool = False
) -> Dict[str, Any]:
    """Synchronize pricing data from external sources.
    
    Args:
        source: Data source (shopify, api, manual)
        force_update: Force update even if recently synced
    
    Returns:
        Sync result with statistics
    """
    logger.info(f"Syncing pricing data from {source}")
    
    # Placeholder implementation
    # In real implementation, this would call external APIs
    await asyncio.sleep(2)  # Simulate API call
    
    result = {
        'source': source,
        'synced_at': datetime.utcnow().isoformat(),
        'products_updated': 0,
        'success': True
    }
    
    logger.info(f"Pricing sync completed: {result}")
    return result


@scheduled_task(interval_seconds=3600, priority=TaskPriority.LOW)
async def cleanup_old_tasks():
    """Clean up old completed tasks (runs hourly).
    
    Removes tasks older than 24 hours to prevent task_queue_state.json from growing indefinitely.
    """
    logger.info("Running scheduled task: cleanup_old_tasks")
    
    try:
        from .decorators import get_global_queue
        queue = get_global_queue()
        
        removed_count = await queue.clear_completed(older_than_hours=24)
        logger.info(f"Cleaned up {removed_count} old tasks")
        
        return {'removed_count': removed_count}
    
    except Exception as e:
        logger.error(f"Task cleanup failed: {e}")
        raise


@scheduled_task(daily_at=(0, 0), priority=TaskPriority.LOW)
async def daily_stats_report():
    """Generate daily task statistics report (runs at midnight UTC)."""
    logger.info("Running scheduled task: daily_stats_report")
    
    try:
        from .decorators import get_global_queue
        queue = get_global_queue()
        
        stats = await queue.get_task_stats()
        logger.info(f"Daily task stats: {stats}")
        
        # Could save to file or send notification here
        return stats
    
    except Exception as e:
        logger.error(f"Stats report failed: {e}")
        raise


@scheduled_task(interval_seconds=300, priority=TaskPriority.LOW)
async def validate_kb_files():
    """Validate knowledge base file integrity (runs every 5 minutes)."""
    logger.info("Running scheduled task: validate_kb_files")
    
    import json
    
    kb_files = [
        'BMC_Base_Conocimiento_GPT-2.json',
        'accessories_catalog.json',
        'bom_rules.json',
        'bromyros_pricing_gpt_optimized.json'
    ]
    
    results = {}
    workspace = Path.cwd()
    
    for filename in kb_files:
        filepath = workspace / filename
        try:
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    json.load(f)
                results[filename] = 'valid'
            else:
                results[filename] = 'missing'
        except json.JSONDecodeError:
            results[filename] = 'invalid_json'
        except Exception as e:
            results[filename] = f'error: {str(e)}'
    
    logger.info(f"KB validation results: {results}")
    return results


# Direct function access for cases where background execution is not desired
generate_quotation_pdf_sync = generate_quotation_pdf.__background_task_func__
calculate_bom_sync = calculate_bom_async.__background_task_func__
