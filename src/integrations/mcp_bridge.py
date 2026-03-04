"""
Panelin v5.0 — MCP Bridge

Connects to the existing MCP server (25 tools) via SSE or Streamable HTTP.
The MCPTools instance is used by the Panelin agent to access:
    - price_check, catalog_search, bom_calculate
    - quotation_store, persist_conversation
    - register_correction, save_customer, lookup_customer
    - batch operations, governance tools, file ops
"""

from __future__ import annotations

from typing import Optional

from agno.tools.mcp import MCPTools

from src.core.config import get_settings


async def create_mcp_tools(
    url: Optional[str] = None,
    transport: Optional[str] = None,
    include_tools: Optional[list[str]] = None,
    exclude_tools: Optional[list[str]] = None,
) -> MCPTools:
    """Create and connect MCPTools to the existing MCP server.

    Args:
        url: Override MCP server URL (default from settings).
        transport: Transport type: "sse" or "streamable-http".
        include_tools: Whitelist of tool names to include.
        exclude_tools: Blacklist of tool names to exclude.

    Returns:
        Connected MCPTools instance.

    Usage:
        async with create_mcp_tools() as mcp:
            agent = create_panelin_agent(mcp_tools=mcp)
            await agent.arun("cotización de 6 paneles isodec 100mm")
    """
    settings = get_settings()

    mcp = MCPTools(
        url=url or settings.mcp_server_url,
        transport=transport or settings.mcp_transport,
        include_tools=include_tools,
        exclude_tools=exclude_tools,
    )
    await mcp.connect()
    return mcp


CORE_TOOLS = [
    "price_check",
    "catalog_search",
    "bom_calculate",
    "quotation_store",
]

PERSISTENCE_TOOLS = [
    "persist_conversation",
    "save_customer",
    "lookup_customer",
    "register_correction",
]

GOVERNANCE_TOOLS = [
    "validate_correction",
    "commit_correction",
    "list_corrections",
    "update_correction_status",
    "batch_validate_corrections",
]

BATCH_TOOLS = [
    "batch_bom_calculate",
    "bulk_price_check",
    "full_quotation",
    "task_status",
    "task_result",
    "task_list",
    "task_cancel",
]
