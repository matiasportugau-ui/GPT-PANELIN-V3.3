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

# Error codes for price_check
PRICE_CHECK_ERROR_CODES = {
    "SKU_NOT_FOUND": "SKU_NOT_FOUND",
    "INVALID_FILTER": "INVALID_FILTER",
    "INVALID_THICKNESS": "INVALID_THICKNESS",
    "INTERNAL_ERROR": "INTERNAL_ERROR",
}

# Error codes for bom_calculate
BOM_CALCULATE_ERROR_CODES = {
    "INVALID_DIMENSIONS": "INVALID_DIMENSIONS",
    "INVALID_THICKNESS": "INVALID_THICKNESS",
    "RULE_NOT_FOUND": "RULE_NOT_FOUND",
    "INTERNAL_ERROR": "INTERNAL_ERROR",
}

# Error codes for catalog_search
CATALOG_SEARCH_ERROR_CODES = {
    "INVALID_CATEGORY": "INVALID_CATEGORY",
    "QUERY_TOO_SHORT": "QUERY_TOO_SHORT",
    "CATALOG_UNAVAILABLE": "CATALOG_UNAVAILABLE",
    "INTERNAL_ERROR": "INTERNAL_ERROR",
}
