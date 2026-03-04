"""
Panelin v5.0 — MCP Connector
================================

Connects to the existing MCP server (18 tools) via SSE transport.
Provides filtered toolsets for different agent configurations.

The MCP server runs on port 8000 and exposes tools for:
- Pricing: price_check, bulk_price_check
- Catalog: catalog_search
- BOM: bom_calculate, batch_bom_calculate
- Quotation: full_quotation, quotation_store
- Governance: report_error, register_correction
- Persistence: persist_conversation, save_customer, lookup_customer
- Tasks: task_status, task_result, task_list, task_cancel
"""

from __future__ import annotations

import logging
from typing import Optional

from agno.tools.mcp import MCPTools

from src.core.config import get_settings

logger = logging.getLogger(__name__)


TOOLSET_PRICING = [
    "price_check",
    "bulk_price_check",
    "catalog_search",
]

TOOLSET_BOM = [
    "bom_calculate",
    "batch_bom_calculate",
]

TOOLSET_QUOTATION = [
    "full_quotation",
    "quotation_store",
]

TOOLSET_GOVERNANCE = [
    "report_error",
    "register_correction",
]

TOOLSET_PERSISTENCE = [
    "persist_conversation",
    "save_customer",
    "lookup_customer",
]

TOOLSET_TASKS = [
    "task_status",
    "task_result",
    "task_list",
    "task_cancel",
]

ALL_MCP_TOOLS = (
    TOOLSET_PRICING
    + TOOLSET_BOM
    + TOOLSET_QUOTATION
    + TOOLSET_GOVERNANCE
    + TOOLSET_PERSISTENCE
    + TOOLSET_TASKS
)


def get_mcp_tools(
    url: Optional[str] = None,
    include_tools: Optional[list[str]] = None,
    exclude_tools: Optional[list[str]] = None,
) -> MCPTools:
    """Create an MCPTools instance connected to the Panelin MCP server.

    Args:
        url: MCP server SSE URL. Defaults to settings.mcp_server_url.
        include_tools: Whitelist of tool names to include (optional).
        exclude_tools: Blacklist of tool names to exclude (optional).

    Returns:
        MCPTools instance (use as async context manager).

    Usage:
        async with get_mcp_tools() as mcp:
            agent = Agent(tools=[mcp])
    """
    settings = get_settings()
    server_url = url or settings.mcp_server_url

    kwargs = {"url": server_url, "transport": "sse"}

    if include_tools:
        kwargs["include_tools"] = include_tools
    if exclude_tools:
        kwargs["exclude_tools"] = exclude_tools

    logger.info(
        "Creating MCPTools connection to %s (include=%s, exclude=%s)",
        server_url,
        include_tools,
        exclude_tools,
    )

    return MCPTools(**kwargs)


def get_pricing_tools(url: Optional[str] = None) -> MCPTools:
    """MCP tools filtered to pricing-only operations."""
    return get_mcp_tools(url=url, include_tools=TOOLSET_PRICING)


def get_bom_tools(url: Optional[str] = None) -> MCPTools:
    """MCP tools filtered to BOM operations."""
    return get_mcp_tools(url=url, include_tools=TOOLSET_BOM)


def get_governance_tools(url: Optional[str] = None) -> MCPTools:
    """MCP tools for governance (error reporting, corrections)."""
    return get_mcp_tools(url=url, include_tools=TOOLSET_GOVERNANCE)
