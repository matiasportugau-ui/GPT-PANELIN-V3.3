# MCP Handler Tests

This directory contains tests for the MCP (Model Context Protocol) handler functions.

## Running Tests

**Important:** Tests must be run from the repository root, not from this directory.

### Correct Usage (from repository root):

```bash
# From repository root
pytest mcp/tests/test_handlers.py -v --cov=mcp/handlers --cov-report=term-missing
```

### Why This Matters

Running pytest from the repository root ensures that:
1. The `mcp` package is properly resolved in Python's import path
2. Imports like `from mcp.handlers.pricing import handle_price_check` work correctly
3. The package structure is maintained properly

### What We Test

The test suite validates:
- **Import Resolution**: All handlers can be imported from `mcp.handlers.*`
- **v1 Contract Compliance**: Handlers return proper v1 contract envelopes
- **Success Responses**: Structure includes `ok: true`, `contract_version: "v1"`, and expected data fields
- **Error Responses**: Structure includes `ok: false`, `contract_version: "v1"`, and error details with codes

### Handlers Tested

- `handle_price_check` - Price lookup by SKU, family, or search query
- `handle_catalog_search` - Product catalog search
- `handle_bom_calculate` - Bill of Materials calculation

## CI/CD Integration

Tests run automatically via `.github/workflows/mcp-tests.yml` on:
- Pushes to `main` or `develop` branches
- Pull requests targeting `main` or `develop`
- Changes to MCP handlers, tests, or tools

## Dependencies

```bash
pip install pytest pytest-cov pytest-asyncio
pip install -r mcp/requirements.txt
```

## Coverage

Current coverage focuses on the critical handler interface layer. See the workflow output for detailed coverage reports.
