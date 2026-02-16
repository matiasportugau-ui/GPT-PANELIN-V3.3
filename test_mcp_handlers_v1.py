"""Test MCP handlers return v1 contract envelopes."""

import asyncio
import pytest

from panelin_mcp_server.handlers.pricing import handle_price_check
from panelin_mcp_server.handlers.catalog import handle_catalog_search
from panelin_mcp_server.handlers.bom import handle_bom_calculate


class TestPriceCheckV1Contract:
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
            assert result["error"]["code"] in ["SKU_NOT_FOUND", "INVALID_FILTER", "INVALID_THICKNESS", "INTERNAL_ERROR"]
            
        asyncio.run(run())
    
    def test_sku_not_found_error(self):
        """SKU not found returns proper error code."""
        async def run():
            result = await handle_price_check({
                "query": "NONEXISTENT_SKU_12345",
                "filter_type": "sku"
            })
            assert result["ok"] is False
            assert result["error"]["code"] == "SKU_NOT_FOUND"
            
        asyncio.run(run())
    
    def test_invalid_filter_error(self):
        """Invalid filter_type returns proper error code."""
        async def run():
            result = await handle_price_check({
                "query": "IROOF30",
                "filter_type": "invalid_filter_type"
            })
            assert result["ok"] is False
            assert result["error"]["code"] == "INVALID_FILTER"
            
        asyncio.run(run())
    
    def test_invalid_thickness_error(self):
        """Out of range thickness_mm returns proper error code."""
        async def run():
            # Test below minimum
            result = await handle_price_check({
                "query": "IROOF30",
                "thickness_mm": 10
            })
            assert result["ok"] is False
            assert result["error"]["code"] == "INVALID_THICKNESS"
            
            # Test above maximum
            result = await handle_price_check({
                "query": "IROOF30",
                "thickness_mm": 300
            })
            assert result["ok"] is False
            assert result["error"]["code"] == "INVALID_THICKNESS"
            
        asyncio.run(run())


class TestCatalogSearchV1Contract:
    """Test catalog_search handler returns v1 contract envelope."""

    def test_success_response_structure(self):
        """Successful catalog search returns v1 envelope with results."""
        async def run():
            # Note: catalog might be empty, so we just check structure
            result = await handle_catalog_search({
                "query": "panel",
                "limit": 5
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
            assert result["error"]["code"] in ["INVALID_CATEGORY", "QUERY_TOO_SHORT", "CATALOG_UNAVAILABLE", "INTERNAL_ERROR"]
            
        asyncio.run(run())
    
    def test_query_too_short_error(self):
        """Query too short returns proper error code."""
        async def run():
            result = await handle_catalog_search({"query": "a"})
            assert result["ok"] is False
            assert result["error"]["code"] == "QUERY_TOO_SHORT"
            
        asyncio.run(run())
    
    def test_invalid_category_error(self):
        """Invalid category returns proper error code."""
        async def run():
            result = await handle_catalog_search({
                "query": "panel",
                "category": "invalid_category"
            })
            assert result["ok"] is False
            assert result["error"]["code"] == "INVALID_CATEGORY"
            
        asyncio.run(run())


class TestBOMCalculateV1Contract:
    """Test bom_calculate handler returns v1 contract envelope."""

    def test_success_response_structure(self):
        """Successful BOM calculation returns v1 envelope with summary and items."""
        async def run():
            result = await handle_bom_calculate({
                "product_family": "ISODEC",
                "thickness_mm": 100,
                "core_type": "EPS",
                "usage": "techo",
                "length_m": 10,
                "width_m": 8
            })
            # Check v1 envelope structure
            assert result["ok"] is True
            assert result["contract_version"] == "v1"
            assert "summary" in result
            assert "items" in result
            
            # Check summary structure
            summary = result["summary"]
            assert "area_m2" in summary
            assert "panel_count" in summary
            assert "total_usd_iva_inc" in summary
            
            # Check items structure
            assert isinstance(result["items"], list)
            if result["items"]:
                item = result["items"][0]
                assert "item_type" in item
                assert "sku" in item
                assert "quantity" in item
                assert "unit" in item
                assert "unit_price_usd_iva_inc" in item
                assert "subtotal_usd_iva_inc" in item
            
        asyncio.run(run())

    def test_error_response_structure(self):
        """Error responses return v1 envelope with error code."""
        async def run():
            result = await handle_bom_calculate({
                "product_family": "ISODEC",
                # Missing required fields
            })
            # Check v1 error envelope structure
            assert result["ok"] is False
            assert result["contract_version"] == "v1"
            assert "error" in result
            assert "code" in result["error"]
            assert "message" in result["error"]
            assert result["error"]["code"] in ["INVALID_DIMENSIONS", "INVALID_THICKNESS", "RULE_NOT_FOUND", "INTERNAL_ERROR"]
            
        asyncio.run(run())
    
    def test_invalid_dimensions_error(self):
        """Missing dimensions returns proper error code."""
        async def run():
            result = await handle_bom_calculate({
                "product_family": "ISODEC",
                "thickness_mm": 100
            })
            assert result["ok"] is False
            assert result["error"]["code"] == "INVALID_DIMENSIONS"
            
        asyncio.run(run())
    
    def test_invalid_thickness_error(self):
        """Invalid thickness returns proper error code."""
        async def run():
            result = await handle_bom_calculate({
                "product_family": "ISODEC",
                "thickness_mm": 0,
                "usage": "techo",
                "length_m": 10,
                "width_m": 8
            })
            assert result["ok"] is False
            assert result["error"]["code"] == "INVALID_THICKNESS"
            
        asyncio.run(run())


class TestLegacyFormatBackwardsCompatibility:
    """Test legacy_format parameter provides backwards compatibility."""

    def test_price_check_legacy_format(self):
        """legacy_format=True returns old response structure."""
        async def run():
            result = await handle_price_check(
                {"query": "IROOF30", "filter_type": "sku"},
                legacy_format=True
            )
            # Should have old structure
            assert "message" in result or "results" in result
            assert "ok" not in result
            assert "contract_version" not in result
            
        asyncio.run(run())
    
    def test_catalog_search_legacy_format(self):
        """legacy_format=True returns old response structure."""
        async def run():
            result = await handle_catalog_search(
                {"query": "panel"},
                legacy_format=True
            )
            # Should have old structure
            assert "message" in result or "results" in result
            assert "ok" not in result
            assert "contract_version" not in result
            
        asyncio.run(run())
    
    def test_bom_calculate_legacy_format(self):
        """legacy_format=True returns old response structure."""
        async def run():
            result = await handle_bom_calculate(
                {
                    "product_family": "ISODEC",
                    "thickness_mm": 100,
                    "core_type": "EPS",
                    "usage": "techo",
                    "length_m": 10,
                    "width_m": 8
                },
                legacy_format=True
            )
            # Should have old structure
            assert "system" in result or "product" in result
            assert "ok" not in result
            assert "contract_version" not in result
            
        asyncio.run(run())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
