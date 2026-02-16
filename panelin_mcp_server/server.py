"""GPT-PANELIN MCP Server.

A minimal MCP server that exposes BMC quotation tools:
- price_check: Product pricing lookup
- catalog_search: Product catalog search
- bom_calculate: Bill of Materials calculator
- report_error: KB error correction logger

Wolf API KB Write tools (v3.4):
- persist_conversation: Save conversation summaries to KB
- register_correction: Register KB corrections via Wolf API
- save_customer: Store customer data for future quotations
- lookup_customer: Retrieve existing customer data

Background task processing tools (async, long-running operations):
- batch_bom_calculate: Submit batch BOM calculations
- bulk_price_check: Submit bulk pricing lookups
- full_quotation: Submit combined BOM + pricing + catalog quotation
- task_status: Check background task progress
- task_result: Retrieve completed task output
- task_list: List recent background tasks
- task_cancel: Cancel a pending/running task

Usage:
    # stdio transport (for OpenAI Custom GPT Actions / local testing)
    python -m panelin_mcp_server.server

    # SSE transport (for remote hosting)
    python -m panelin_mcp_server.server --transport sse --port 8000

Requires: mcp>=1.0.0 (pip install mcp)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# Attempt to import MCP SDK — gracefully handle if not installed
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    HAS_MCP_SDK = True
except ImportError:
    HAS_MCP_SDK = False

from .handlers.pricing import handle_price_check
from .handlers.catalog import handle_catalog_search
from .handlers.bom import handle_bom_calculate
from .handlers.errors import handle_report_error
from .handlers.governance import handle_validate_correction, handle_commit_correction
from .handlers.quotation import configure_quotation_store, handle_quotation_store
from .handlers.wolf_kb_write import (
    configure_wolf_kb_client,
    handle_persist_conversation,
    handle_register_correction,
    handle_save_customer,
    handle_lookup_customer,
)
from .storage.factory import initialize_memory_store
from .observability import (
    get_invocation_context,
    log_tool_invocation_error,
    log_tool_invocation_start,
    log_tool_invocation_success,
)
from .handlers.tasks import (
    handle_batch_bom_calculate,
    handle_bulk_price_check,
    handle_full_quotation,
    handle_task_status,
    handle_task_result,
    handle_task_list,
    handle_task_cancel,
)

TOOLS_DIR = Path(__file__).parent / "tools"


def _load_tool_schema(name: str) -> dict[str, Any]:
    """Load a tool JSON schema from the tools/ directory."""
    path = TOOLS_DIR / f"{name}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# Tool handler dispatch — core tools + background task tools
TOOL_HANDLERS = {
    # Core tools (synchronous)
    "price_check": handle_price_check,
    "catalog_search": handle_catalog_search,
    "bom_calculate": handle_bom_calculate,
    "report_error": handle_report_error,
    "validate_correction": handle_validate_correction,
    "commit_correction": handle_commit_correction,
    "quotation_store": handle_quotation_store,
    # Wolf API KB Write tools (v3.4)
    "persist_conversation": handle_persist_conversation,
    "register_correction": handle_register_correction,
    "save_customer": handle_save_customer,
    "lookup_customer": handle_lookup_customer,
    # Background task tools (async)
    "batch_bom_calculate": handle_batch_bom_calculate,
    "bulk_price_check": handle_bulk_price_check,
    "full_quotation": handle_full_quotation,
    "task_status": handle_task_status,
    "task_result": handle_task_result,
    "task_list": handle_task_list,
    "task_cancel": handle_task_cancel,
}

TOOL_NAMES = list(TOOL_HANDLERS.keys())


def _estimate_token_count(payload: Any) -> int:
    """Estimate token count using a conservative character heuristic."""
    serialized = json.dumps(payload, ensure_ascii=False, default=str)
    return max(1, round(len(serialized) / 4))


def _init_task_workers() -> None:
    """Register background task workers with the task manager.

    Called once during server creation to wire up the worker functions
    for each supported background task type.
    """
    from .tasks.manager import get_task_manager
    from .tasks.models import TaskType
    from .tasks.workers import (
        batch_bom_worker,
        bulk_pricing_worker,
        full_quotation_worker,
    )

    manager = get_task_manager()
    manager.register_worker(TaskType.BATCH_BOM, batch_bom_worker)
    manager.register_worker(TaskType.BULK_PRICING, bulk_pricing_worker)
    manager.register_worker(TaskType.FULL_QUOTATION, full_quotation_worker)


def create_server() -> Any:
    """Create and configure the MCP server instance."""
    if not HAS_MCP_SDK:
        print(
            "ERROR: MCP SDK not installed. Run: pip install mcp>=1.0.0",
            file=sys.stderr,
        )
        sys.exit(1)

    # Initialize background task workers
    _init_task_workers()

    server = Server("panelin-mcp-server")
    memory_store, store_metadata = initialize_memory_store()
    configure_quotation_store(
        memory_store,
        enable_vector_retrieval=bool(store_metadata.get("enable_vector_retrieval", False)),
        backend_metadata=store_metadata,
    )

    # Initialize Wolf API KB Write client (v3.4)
    wolf_api_key = os.environ.get("WOLF_API_KEY", "")
    wolf_api_url = os.environ.get("WOLF_API_URL", "https://panelin-api-642127786762.us-central1.run.app")
    if wolf_api_key:
        from panelin_mcp_integration.panelin_mcp_server import PanelinMCPServer as WolfClient
        wolf_client = WolfClient(api_key=wolf_api_key, base_url=wolf_api_url)
        configure_wolf_kb_client(wolf_client)

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        tools = []
        for name in TOOL_NAMES:
            schema = _load_tool_schema(name)
            tools.append(
                Tool(
                    name=schema["name"],
                    description=schema["description"],
                    inputSchema=schema["inputSchema"],
                )
            )
        return tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        context = get_invocation_context(name, arguments)
        token_input = _estimate_token_count(arguments)
        started_at = log_tool_invocation_start(context, token_input)

        handler = TOOL_HANDLERS.get(name)
        if not handler:
            log_tool_invocation_error(context, started_at, "UNKNOWN_TOOL", token_input)
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

        try:
            result = await handler(arguments)
        except Exception as exc:  # noqa: BLE001
            error_code = getattr(exc, "code", exc.__class__.__name__.upper())
            log_tool_invocation_error(context, started_at, str(error_code), token_input)
            raise

        token_output = _estimate_token_count(result)
        log_tool_invocation_success(context, started_at, token_input, token_output)
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]

    return server


async def main_stdio() -> None:
    """Run server with stdio transport."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    parser = argparse.ArgumentParser(description="GPT-PANELIN MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if not HAS_MCP_SDK:
        print("ERROR: MCP SDK not installed. Run: pip install mcp>=1.0.0", file=sys.stderr)
        sys.exit(1)

    if args.transport == "stdio":
        import asyncio
        asyncio.run(main_stdio())
    elif args.transport == "sse":
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Route, Mount
        import uvicorn

        server = create_server()
        sse = SseServerTransport("/messages")

        async def handle_sse_app(scope, receive, send):
            async with sse.connect_sse(scope, receive, send) as streams:
                await server.run(streams[0], streams[1], server.create_initialization_options())

        app = Starlette(routes=[
            Mount("/sse", app=handle_sse_app),
            Route("/messages", endpoint=sse.handle_post_message, methods=["POST"]),
        ])
        uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
