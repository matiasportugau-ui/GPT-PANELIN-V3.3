"""Compatibility helpers for Agno MCP client imports.

This repository already has a local package named `mcp/` (our server code),
which can shadow the external `mcp` SDK required by `agno.tools.mcp`.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any


def ensure_external_mcp_sdk() -> None:
    """Force-load the pip `mcp` package instead of local `/workspace/mcp`."""
    project_root = Path(__file__).resolve().parents[2]
    loaded = sys.modules.get("mcp")

    if loaded is not None:
        loaded_path = getattr(loaded, "__file__", "") or ""
        if "/site-packages/" in loaded_path:
            return
        if str(project_root) in loaded_path:
            del sys.modules["mcp"]

    original_path = list(sys.path)
    try:
        sys.path = [
            p
            for p in sys.path
            if p not in {"", ".", str(project_root), str(project_root / "mcp")}
        ]
        importlib.import_module("mcp")
    finally:
        sys.path = original_path


def load_mcp_tooling() -> tuple[Any, Any, Any]:
    """Return MCPTools + transport param classes from Agno."""
    ensure_external_mcp_sdk()
    from agno.tools.mcp import MCPTools
    from agno.tools.mcp.params import SSEClientParams, StreamableHTTPClientParams

    return MCPTools, SSEClientParams, StreamableHTTPClientParams

