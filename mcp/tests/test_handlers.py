"""Test MCP handlers return v1 contract envelopes.

This test suite validates that MCP tool handlers:
1. Can be imported correctly from the mcp.handlers package
2. Return proper v1 contract envelope structures
3. Handle errors appropriately with proper error codes

These tests run in CI via .github/workflows/mcp-tests.yml
"""

import asyncio
import pytest

# Import handlers - this is the critical import that was failing
# when pytest was run from mcp/tests directory instead of repo root
from mcp.handlers.pricing import handle_price_check
from mcp.handlers.catalog import handle_catalog_search
from mcp.handlers.bom import handle_bom_calculate

# Import error code registries for validation
from mcp_tools.contracts import (
    PRICE_CHECK_ERROR_CODES,
    CATALOG_SEARCH_ERROR_CODES,
    BOM_CALCULATE_ERROR_CODES,
)


class TestPriceCheckHandler:
    """Test price_check handler returns v1 contract envelope."""

    def test_success_response_structure(self):
        """Successful price lookup returns v1 envelope with matches."""
        async def run():
            result = await handle_price_check({
                "query": "IROOF30",
                "filter_type": "sku"
            })
            # Check v1 envelope structure
            assert result["ok"] is True
            assert result["contract_version"] == "v1"
            assert "matches" in result
            assert isinstance(result["matches"], list)
            assert len(result["matches"]) > 0

            # Check match structure
            match = result["matches"][0]
            assert "sku" in match
            assert "description" in match
            assert "price_usd_iva_inc" in match

        asyncio.run(run())

    def test_error_response_structure(self):
        """Error responses return v1 envelope with error code."""
        async def run():
            result = await handle_price_check({"query": ""})
            # Check v1 error envelope structure
            assert result["ok"] is False
            assert result["contract_version"] == "v1"
            assert "error" in result
            assert "code" in result["error"]
            assert "message" in result["error"]
            # Validate error code is in the contract-defined set
            assert result["error"]["code"] in PRICE_CHECK_ERROR_CODES

        asyncio.run(run())


class TestCatalogSearchHandler:
    """Test catalog_search handler returns v1 contract envelope."""

    def test_success_response_structure(self):
        """Successful catalog search returns v1 envelope with results."""
        async def run():
            result = await handle_catalog_search({
                "query": "panel",
                "category": "techo"
            })
            # Check v1 envelope structure
            assert result["ok"] is True
            assert result["contract_version"] == "v1"
            assert "results" in result
            assert isinstance(result["results"], list)

        asyncio.run(run())

    def test_error_response_structure(self):
        """Error responses return v1 envelope with error code."""
        async def run():
            result = await handle_catalog_search({"query": ""})
            # Check v1 error envelope structure
            assert result["ok"] is False
            assert result["contract_version"] == "v1"
            assert "error" in result
            assert "code" in result["error"]
            assert "message" in result["error"]
            # Validate error code is in the contract-defined set
            assert result["error"]["code"] in CATALOG_SEARCH_ERROR_CODES

        asyncio.run(run())


class TestBOMCalculateHandler:
    """Test bom_calculate handler returns v1 contract envelope."""

    def test_success_response_structure(self):
        """Successful BOM calculation returns v1 envelope with result."""
        async def run():
            result = await handle_bom_calculate({
                "product_family": "ISODEC",
                "thickness_mm": 100,
                "core_type": "EPS",
                "usage": "techo",
                "length_m": 10,
                "width_m": 5
            })
            # Check v1 envelope structure
            assert result["ok"] is True
            assert result["contract_version"] == "v1"
            assert "items" in result
            assert "summary" in result

        asyncio.run(run())

    def test_error_response_structure(self):
        """Error responses return v1 envelope with error code."""
        async def run():
            result = await handle_bom_calculate({
                "product_family": "",
                "thickness_mm": 100,
                "core_type": "EPS",
                "usage": "techo",
                "length_m": 10,
                "width_m": 5
            })
            # Check v1 error envelope structure
            assert result["ok"] is False
            assert result["contract_version"] == "v1"
            assert "error" in result
            assert "code" in result["error"]
            assert "message" in result["error"]
            # Validate error code is in the contract-defined set
            assert result["error"]["code"] in BOM_CALCULATE_ERROR_CODES

        asyncio.run(run())


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
