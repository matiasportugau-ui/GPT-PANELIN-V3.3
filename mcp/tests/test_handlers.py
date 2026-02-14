"""Comprehensive tests for MCP handlers.

Tests all handlers for:
- V1 contract envelope compliance
- Input validation
- Error handling
- Data extraction
"""

from __future__ import annotations

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp.handlers.pricing import handle_price_check
from mcp.handlers.catalog import handle_catalog_search
from mcp.handlers.bom import handle_bom_calculate
from mcp.handlers.errors import handle_report_error


class TestPriceCheck:
    """Tests for price_check handler."""
    
    @pytest.mark.asyncio
    async def test_valid_search_returns_matches(self):
        """Test that valid search returns matches with v1 envelope."""
        result = await handle_price_check({
            'query': 'isoroof',
            'filter_type': 'search'
        })
        
        assert result['ok'] is True
        assert result['contract_version'] == 'v1'
        assert 'matches' in result
        assert isinstance(result['matches'], list)
        assert len(result['matches']) > 0
        
        # Validate match structure
        match = result['matches'][0]
        assert 'sku' in match
        assert 'description' in match
        assert 'price_usd_iva_inc' in match
    
    @pytest.mark.asyncio
    async def test_query_too_short_returns_error(self):
        """Test that short query returns validation error."""
        result = await handle_price_check({'query': 'a'})
        
        assert result['ok'] is False
        assert result['contract_version'] == 'v1'
        assert 'error' in result
        assert result['error']['code'] == 'INVALID_FILTER'
        assert 'message' in result['error']
    
    @pytest.mark.asyncio
    async def test_invalid_thickness_returns_error(self):
        """Test that invalid thickness returns error."""
        result = await handle_price_check({
            'query': 'test',
            'thickness_mm': 10  # Below minimum of 20
        })
        
        assert result['ok'] is False
        assert result['contract_version'] == 'v1'
        assert result['error']['code'] == 'INVALID_THICKNESS'
    
    @pytest.mark.asyncio
    async def test_thickness_filter_works(self):
        """Test that thickness filter correctly filters results."""
        result = await handle_price_check({
            'query': 'isoroof',
            'thickness_mm': 30
        })
        
        if result['ok']:
            # All matches should either have thickness_mm=30 or no thickness
            for match in result['matches']:
                if 'thickness_mm' in match:
                    assert match['thickness_mm'] == 30
    
    @pytest.mark.asyncio
    async def test_no_results_returns_error(self):
        """Test that no matches returns SKU_NOT_FOUND error."""
        result = await handle_price_check({
            'query': 'nonexistentproduct12345xyz'
        })
        
        assert result['ok'] is False
        assert result['contract_version'] == 'v1'
        assert result['error']['code'] == 'SKU_NOT_FOUND'
    
    @pytest.mark.asyncio
    async def test_invalid_filter_type_returns_error(self):
        """Test that invalid filter_type returns error."""
        result = await handle_price_check({
            'query': 'test',
            'filter_type': 'invalid'
        })
        
        assert result['ok'] is False
        assert result['error']['code'] == 'INVALID_FILTER'


class TestCatalogSearch:
    """Tests for catalog_search handler."""
    
    @pytest.mark.asyncio
    async def test_valid_search_returns_results(self):
        """Test that valid search returns results with v1 envelope."""
        result = await handle_catalog_search({
            'query': 'panel',
            'limit': 5
        })
        
        assert result['ok'] is True
        assert result['contract_version'] == 'v1'
        assert 'results' in result
        assert isinstance(result['results'], list)
    
    @pytest.mark.asyncio
    async def test_query_too_short_returns_error(self):
        """Test that short query returns validation error."""
        result = await handle_catalog_search({'query': 'x'})
        
        assert result['ok'] is False
        assert result['contract_version'] == 'v1'
        assert result['error']['code'] == 'QUERY_TOO_SHORT'
    
    @pytest.mark.asyncio
    async def test_invalid_category_returns_error(self):
        """Test that invalid category returns error."""
        result = await handle_catalog_search({
            'query': 'panel',
            'category': 'invalid'
        })
        
        assert result['ok'] is False
        assert result['error']['code'] == 'INVALID_CATEGORY'
    
    @pytest.mark.asyncio
    async def test_limit_parameter_works(self):
        """Test that limit parameter is respected."""
        result = await handle_catalog_search({
            'query': 'panel',
            'limit': 3
        })
        
        if result['ok'] and result['results']:
            assert len(result['results']) <= 3


class TestBomCalculate:
    """Tests for bom_calculate handler."""
    
    @pytest.mark.asyncio
    async def test_valid_bom_returns_calculation(self):
        """Test that valid BOM request returns calculation."""
        result = await handle_bom_calculate({
            'product_family': 'ISOROOF',
            'thickness_mm': 50,
            'usage': 'techo',
            'length_m': 10,
            'width_m': 5
        })
        
        assert result['ok'] is True
        assert result['contract_version'] == 'v1'
        # Should have calculation fields (system, product, dimensions, etc.)
    
    @pytest.mark.asyncio
    async def test_missing_required_fields_returns_error(self):
        """Test that missing required fields returns error."""
        result = await handle_bom_calculate({
            'thickness_mm': 50
        })
        
        assert result['ok'] is False
        assert result['contract_version'] == 'v1'
        assert result['error']['code'] == 'INVALID_DIMENSIONS'
    
    @pytest.mark.asyncio
    async def test_invalid_thickness_returns_error(self):
        """Test that invalid thickness returns error."""
        result = await handle_bom_calculate({
            'product_family': 'ISOROOF',
            'thickness_mm': 10,  # Below minimum of 30
            'usage': 'techo',
            'length_m': 10,
            'width_m': 5
        })
        
        assert result['ok'] is False
        assert result['error']['code'] == 'INVALID_THICKNESS'


class TestReportError:
    """Tests for report_error handler."""
    
    @pytest.mark.asyncio
    async def test_valid_error_report_succeeds(self):
        """Test that valid error report succeeds."""
        result = await handle_report_error({
            'kb_file': 'test_file.json',
            'field': 'items[0].price',
            'wrong_value': '100',
            'correct_value': '150',
            'source': 'user_correction',
            'notes': 'Test correction'
        })
        
        assert result['ok'] is True
        assert result['contract_version'] == 'v1'
    
    @pytest.mark.asyncio
    async def test_missing_required_fields_returns_error(self):
        """Test that missing required fields returns error."""
        result = await handle_report_error({
            'kb_file': 'test.json'
        })
        
        assert result['ok'] is False
        assert result['contract_version'] == 'v1'
        assert 'error' in result


class TestContractCompliance:
    """Tests for v1 contract envelope compliance across all handlers."""
    
    @pytest.mark.asyncio
    async def test_all_handlers_return_envelope(self):
        """Test that all handlers return v1 contract envelope."""
        handlers = [
            (handle_price_check, {'query': 'test'}),
            (handle_catalog_search, {'query': 'test'}),
            (handle_bom_calculate, {'thickness_mm': 50}),
            (handle_report_error, {'kb_file': 'test.json'})
        ]
        
        for handler, args in handlers:
            result = await handler(args)
            assert 'ok' in result
            assert 'contract_version' in result
            assert result['contract_version'] == 'v1'
            
            if result['ok']:
                # Success case - should NOT have error key
                assert 'error' not in result
            else:
                # Error case - should have error with code and message
                assert 'error' in result
                assert 'code' in result['error']
                assert 'message' in result['error']
