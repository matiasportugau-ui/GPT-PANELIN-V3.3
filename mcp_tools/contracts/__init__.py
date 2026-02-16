"""MCP tool contract registry for first-wave and v3.4 Wolf API KB Write tools."""

from __future__ import annotations

CONTRACT_VERSION = "v1"

TOOL_CONTRACT_VERSIONS = {
    "kb_search": CONTRACT_VERSION,
    "price_check": CONTRACT_VERSION,
    "bom_calculate": CONTRACT_VERSION,
    "catalog_search": CONTRACT_VERSION,
    "quotation_store": CONTRACT_VERSION,
    # Wolf API KB Write tools (v3.4)
    "persist_conversation": CONTRACT_VERSION,
    "register_correction": CONTRACT_VERSION,
    "save_customer": CONTRACT_VERSION,
    "lookup_customer": CONTRACT_VERSION,
}

# Error codes for price_check
SKU_NOT_FOUND = "SKU_NOT_FOUND"
INVALID_FILTER = "INVALID_FILTER"
INVALID_THICKNESS = "INVALID_THICKNESS"
INTERNAL_ERROR = "INTERNAL_ERROR"

# Note: PRICE_CHECK_ERROR_CODES is a registry of all allowed price_check error codes.
# The keys mirror the constant values intentionally so callers can both validate
# error codes and iterate the contract surface in a single, centralized mapping.
PRICE_CHECK_ERROR_CODES = {
    "SKU_NOT_FOUND": SKU_NOT_FOUND,
    "INVALID_FILTER": INVALID_FILTER,
    "INVALID_THICKNESS": INVALID_THICKNESS,
    "INTERNAL_ERROR": INTERNAL_ERROR,
}

# Error codes for bom_calculate
INVALID_DIMENSIONS = "INVALID_DIMENSIONS"
RULE_NOT_FOUND = "RULE_NOT_FOUND"

# Note: BOM_CALCULATE_ERROR_CODES is a registry of all allowed bom_calculate
# error codes, used for validation and contract enumeration; keys mirror values
# by design for consistent lookup and iteration.
BOM_CALCULATE_ERROR_CODES = {
    "INVALID_DIMENSIONS": INVALID_DIMENSIONS,
    "INVALID_THICKNESS": INVALID_THICKNESS,
    "RULE_NOT_FOUND": RULE_NOT_FOUND,
    "INTERNAL_ERROR": INTERNAL_ERROR,
}

# Error codes for catalog_search
INVALID_CATEGORY = "INVALID_CATEGORY"
QUERY_TOO_SHORT = "QUERY_TOO_SHORT"
CATALOG_UNAVAILABLE = "CATALOG_UNAVAILABLE"

# Note: CATALOG_SEARCH_ERROR_CODES is a registry of all allowed catalog_search
# error codes for validation and tooling; the duplicated key/value strings are
# intentional to keep the mapping explicit and self-describing.
CATALOG_SEARCH_ERROR_CODES = {
    "INVALID_CATEGORY": INVALID_CATEGORY,
    "QUERY_TOO_SHORT": QUERY_TOO_SHORT,
    "CATALOG_UNAVAILABLE": CATALOG_UNAVAILABLE,
    "INTERNAL_ERROR": INTERNAL_ERROR,
}

# Error codes for Wolf API KB Write tools (v3.4)
PASSWORD_REQUIRED = "PASSWORD_REQUIRED"
INVALID_PASSWORD = "INVALID_PASSWORD"
INVALID_PHONE = "INVALID_PHONE"
WOLF_API_ERROR = "WOLF_API_ERROR"

WOLF_KB_WRITE_ERROR_CODES = {
    "PASSWORD_REQUIRED": PASSWORD_REQUIRED,
    "INVALID_PASSWORD": INVALID_PASSWORD,
    "INVALID_PHONE": INVALID_PHONE,
    "WOLF_API_ERROR": WOLF_API_ERROR,
    "INTERNAL_ERROR": INTERNAL_ERROR,
}

LOOKUP_CUSTOMER_ERROR_CODES = {
    "QUERY_TOO_SHORT": QUERY_TOO_SHORT,
    "WOLF_API_ERROR": WOLF_API_ERROR,
    "INTERNAL_ERROR": INTERNAL_ERROR,
}

# Error codes for governance tools (self-healing architecture)
INVALID_KB_FILE = "INVALID_KB_FILE"
FIELD_NOT_FOUND = "FIELD_NOT_FOUND"
VALUE_MISMATCH = "VALUE_MISMATCH"
CHANGE_NOT_FOUND = "CHANGE_NOT_FOUND"
CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"

VALIDATE_CORRECTION_ERROR_CODES = {
    "INVALID_KB_FILE": INVALID_KB_FILE,
    "FIELD_NOT_FOUND": FIELD_NOT_FOUND,
    "VALUE_MISMATCH": VALUE_MISMATCH,
    "INTERNAL_ERROR": INTERNAL_ERROR,
}

COMMIT_CORRECTION_ERROR_CODES = {
    "CHANGE_NOT_FOUND": CHANGE_NOT_FOUND,
    "CONFIRMATION_REQUIRED": CONFIRMATION_REQUIRED,
    "INTERNAL_ERROR": INTERNAL_ERROR,
}
