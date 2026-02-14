"""MCP tool contract registry for first-wave tools."""

from __future__ import annotations

CONTRACT_VERSION = "v1"

TOOL_CONTRACT_VERSIONS = {
    "kb_search": CONTRACT_VERSION,
    "price_check": CONTRACT_VERSION,
    "bom_calculate": CONTRACT_VERSION,
    "catalog_search": CONTRACT_VERSION,
    "quotation_store": CONTRACT_VERSION,
}
