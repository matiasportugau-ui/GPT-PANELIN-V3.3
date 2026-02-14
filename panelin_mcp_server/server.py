"""GPT-PANELIN MCP Server.

A minimal MCP server that exposes BMC quotation tools:
- price_check: Product pricing lookup
- catalog_search: Product catalog search
- bom_calculate: Bill of Materials calculator
- report_error: KB error correction logger

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

TOOLS_DIR = Path(__file__).parent / "tools"


def _load_tool_schema(name: str) -> dict[str, Any]:
    """Load a tool JSON schema from the tools/ directory."""
    path = TOOLS_DIR / f"{name}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# Tool handler dispatch
TOOL_HANDLERS = {
    "price_check": handle_price_check,
    "catalog_search": handle_catalog_search,
    "bom_calculate": handle_bom_calculate,
    "report_error": handle_report_error,
}

TOOL_NAMES = list(TOOL_HANDLERS.keys())


def create_server() -> Any:
    """Create and configure the MCP server instance."""
    if not HAS_MCP_SDK:
        print(
            "ERROR: MCP SDK not installed. Run: pip install mcp>=1.0.0",
            file=sys.stderr,
        )
        sys.exit(1)

    server = Server("panelin-mcp-server")

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
        handler = TOOL_HANDLERS.get(name)
        if not handler:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

        result = await handler(arguments)
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
