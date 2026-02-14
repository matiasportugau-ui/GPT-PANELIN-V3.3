# MCP Handler Tests

This directory contains comprehensive tests for all MCP handlers.

## Test Coverage

- **16 tests** covering all 4 handlers
- **100% contract compliance** validation
- **Input validation** testing
- **Error handling** verification
- **Data extraction** validation

## Running Tests

### Quick Test

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest test_handlers.py -v
```

### With Coverage

```bash
pytest test_handlers.py --cov=../handlers --cov-report=term-missing
```

### Specific Tests

```bash
# Test a specific handler
pytest test_handlers.py::TestPriceCheck -v

# Test a specific function
pytest test_handlers.py::TestPriceCheck::test_valid_search_returns_matches -v

# Test contract compliance only
pytest test_handlers.py::TestContractCompliance -v
```

## Test Structure

### TestPriceCheck (6 tests)
- `test_valid_search_returns_matches`: Validates successful price lookup
- `test_query_too_short_returns_error`: Tests query length validation
- `test_invalid_thickness_returns_error`: Tests thickness range validation
- `test_thickness_filter_works`: Validates thickness filtering
- `test_no_results_returns_error`: Tests SKU_NOT_FOUND error
- `test_invalid_filter_type_returns_error`: Tests filter type validation

### TestCatalogSearch (4 tests)
- `test_valid_search_returns_results`: Validates successful catalog search
- `test_query_too_short_returns_error`: Tests query length validation
- `test_invalid_category_returns_error`: Tests category validation
- `test_limit_parameter_works`: Validates result limiting

### TestBomCalculate (3 tests)
- `test_valid_bom_returns_calculation`: Validates BOM calculation
- `test_missing_required_fields_returns_error`: Tests required field validation
- `test_invalid_thickness_returns_error`: Tests thickness range validation

### TestReportError (2 tests)
- `test_valid_error_report_succeeds`: Validates error reporting
- `test_missing_required_fields_returns_error`: Tests required field validation

### TestContractCompliance (1 test)
- `test_all_handlers_return_envelope`: Validates all handlers return v1 contract envelope

## Expected Output

```
============================= test session starts ==============================
test_handlers.py::TestPriceCheck::test_valid_search_returns_matches PASSED [  6%]
test_handlers.py::TestPriceCheck::test_query_too_short_returns_error PASSED [ 12%]
test_handlers.py::TestPriceCheck::test_invalid_thickness_returns_error PASSED [ 18%]
test_handlers.py::TestPriceCheck::test_thickness_filter_works PASSED [ 25%]
test_handlers.py::TestPriceCheck::test_no_results_returns_error PASSED [ 31%]
test_handlers.py::TestPriceCheck::test_invalid_filter_type_returns_error PASSED [ 37%]
test_handlers.py::TestCatalogSearch::test_valid_search_returns_results PASSED [ 43%]
test_handlers.py::TestCatalogSearch::test_query_too_short_returns_error PASSED [ 50%]
test_handlers.py::TestCatalogSearch::test_invalid_category_returns_error PASSED [ 56%]
test_handlers.py::TestCatalogSearch::test_limit_parameter_works PASSED [ 62%]
test_handlers.py::TestBomCalculate::test_valid_bom_returns_calculation PASSED [ 68%]
test_handlers.py::TestBomCalculate::test_missing_required_fields_returns_error PASSED [ 75%]
test_handlers.py::TestBomCalculate::test_invalid_thickness_returns_error PASSED [ 81%]
test_handlers.py::TestReportError::test_valid_error_report_succeeds PASSED [ 87%]
test_handlers.py::TestReportError::test_missing_required_fields_returns_error PASSED [ 93%]
test_handlers.py::TestContractCompliance::test_all_handlers_return_envelope PASSED [100%]

============================== 16 passed in 0.04s ===============================
```

## CI/CD Integration

These tests run automatically on every push/PR via GitHub Actions:

- **Workflow**: `.github/workflows/mcp-tests.yml`
- **Triggers**: Push to main/develop/copilot branches, PRs
- **Validates**:
  - Handler functionality
  - Contract compliance
  - KB file integrity
  - JSON schema validation

## Adding New Tests

When adding a new handler:

1. Create test class following existing pattern
2. Test success cases with valid inputs
3. Test error cases with invalid inputs
4. Test contract envelope compliance
5. Add to `TestContractCompliance.test_all_handlers_return_envelope`

Example:

```python
class TestNewHandler:
    """Tests for new_handler."""
    
    @pytest.mark.asyncio
    async def test_valid_input_succeeds(self):
        """Test that valid input returns success."""
        result = await handle_new_handler({'param': 'value'})
        
        assert result['ok'] is True
        assert result['contract_version'] == 'v1'
        assert 'expected_field' in result
    
    @pytest.mark.asyncio
    async def test_invalid_input_returns_error(self):
        """Test that invalid input returns error."""
        result = await handle_new_handler({'param': ''})
        
        assert result['ok'] is False
        assert result['contract_version'] == 'v1'
        assert result['error']['code'] == 'EXPECTED_ERROR_CODE'
```

## Debugging Failed Tests

### View Full Error Details

```bash
pytest test_handlers.py -v --tb=long
```

### Run in Debug Mode

```bash
pytest test_handlers.py -vv --pdb
```

### Test Specific Scenario

```python
# Add to test file temporarily
@pytest.mark.asyncio
async def test_debug_scenario():
    result = await handle_price_check({'query': 'debug', 'thickness_mm': 25})
    import json
    print(json.dumps(result, indent=2))
    assert False  # Force failure to see output
```

## Contract Validation

All handlers MUST return v1 contract envelope:

✅ **Success**:
```json
{
  "ok": true,
  "contract_version": "v1",
  ... handler-specific fields ...
}
```

✅ **Error**:
```json
{
  "ok": false,
  "contract_version": "v1",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {}
  }
}
```

❌ **Invalid** (will fail tests):
```json
{
  "error": "Something went wrong"
}
```

## Performance

Tests run in ~0.04s total. If tests are slow:

1. Check if loading large files repeatedly
2. Consider using fixtures for shared data
3. Mock external dependencies if any

## Next Steps

- ✅ Run tests locally before pushing
- ✅ Check CI results after pushing
- ✅ Maintain 100% pass rate
- ✅ Add tests for new features
