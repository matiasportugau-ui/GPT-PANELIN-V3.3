# MCP Server Quick Start Guide

## Overview

The GPT-PANELIN MCP Server exposes 4 tools for construction panel quotation:
- `price_check`: Product pricing lookup
- `catalog_search`: Product catalog search
- `bom_calculate`: Bill of Materials calculator
- `report_error`: KB error correction logger

## Prerequisites

```bash
# Install Python dependencies
pip install -r mcp/requirements.txt

# Install test dependencies (optional)
pip install -r mcp/tests/requirements.txt
```

## Running Tests

```bash
# Run all handler tests
cd mcp/tests
pytest test_handlers.py -v

# Run with coverage
pytest test_handlers.py --cov=../handlers --cov-report=term-missing
```

## Starting the Server

### Option 1: stdio transport (for local testing / OpenAI Custom GPT)

```bash
python -m mcp.server
```

The server will communicate via stdin/stdout. This is the recommended mode for:
- OpenAI Custom GPT Actions
- Local testing with MCP clients
- Direct integration with OpenAI Responses API

### Option 2: SSE transport (for remote hosting)

```bash
python -m mcp.server --transport sse --port 8000
```

The server will start on `http://localhost:8000` with Server-Sent Events transport. Use this for:
- Hosting on cloud platforms (Railway, Render, Fly.io)
- Remote access from multiple clients
- Production deployments

## Testing the Server

### Manual Testing

```bash
# Test price_check handler
python3 << 'EOF'
import asyncio
from mcp.handlers.pricing import handle_price_check

async def test():
    result = await handle_price_check({'query': 'isoroof', 'filter_type': 'search'})
    print(result)

asyncio.run(test())
EOF
```

### Automated Testing

```bash
# Run full test suite
cd mcp/tests && pytest test_handlers.py

# Test specific handler
pytest test_handlers.py::TestPriceCheck -v

# Test contract compliance
pytest test_handlers.py::TestContractCompliance -v
```

## CI/CD Integration

The repository includes automated testing via GitHub Actions:

- **`.github/workflows/mcp-tests.yml`**: Runs on every push/PR
  - Tests all MCP handlers
  - Validates contract schemas
  - Validates KB files
  - Checks server syntax

## Deployment

### Deploy to Railway

1. Create a new project on [Railway](https://railway.app)
2. Connect your GitHub repository
3. Set the start command:
   ```
   python -m mcp.server --transport sse --port $PORT
   ```
4. Railway will auto-deploy on every push

### Deploy to Render

1. Create a new Web Service on [Render](https://render.com)
2. Connect your GitHub repository
3. Configure:
   - **Build Command**: `pip install -r mcp/requirements.txt`
   - **Start Command**: `python -m mcp.server --transport sse --port $PORT`
4. Render will auto-deploy on every push

### Deploy to Fly.io

1. Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
2. Create `fly.toml` in repository root:
   ```toml
   app = "gpt-panelin-mcp"
   primary_region = "ewr"

   [build]
     dockerfile = "Dockerfile"

   [[services]]
     internal_port = 8000
     protocol = "tcp"

     [[services.ports]]
       handlers = ["http"]
       port = 80
   ```
3. Deploy: `fly launch && fly deploy`

## Health Checks

The server includes built-in validation:

```python
# Check all handlers return v1 contract envelope
python3 << 'EOF'
import asyncio
from mcp.handlers.pricing import handle_price_check
from mcp.handlers.catalog import handle_catalog_search
from mcp.handlers.bom import handle_bom_calculate
from mcp.handlers.errors import handle_report_error

async def health_check():
    handlers = [
        (handle_price_check, {'query': 'test'}),
        (handle_catalog_search, {'query': 'panel'}),
        (handle_bom_calculate, {'product_family': 'ISOROOF', 'thickness_mm': 50, 'usage': 'techo', 'length_m': 10, 'width_m': 5}),
        (handle_report_error, {'kb_file': 'test.json', 'field': 'test', 'wrong_value': '1', 'correct_value': '2', 'source': 'validation_check'})
    ]
    
    for handler, args in handlers:
        result = await handler(args)
        assert 'ok' in result and 'contract_version' in result
        print(f"✓ {handler.__name__}")
    
    print("\n✅ All handlers healthy!")

asyncio.run(health_check())
EOF
```

## Troubleshooting

### Import Errors

If you get `ModuleNotFoundError: No module named 'mcp'`:

```bash
# Ensure you're in the repository root
cd /path/to/GPT-PANELIN-V3.2

# Install dependencies
pip install -r mcp/requirements.txt
```

### Tool Schema Validation Errors

If contracts don't match handlers:

```bash
# Run contract validation
python3 << 'EOF'
import json
from pathlib import Path

contracts_dir = Path("mcp_tools/contracts")
for contract_file in contracts_dir.glob("*.v1.json"):
    with open(contract_file) as f:
        contract = json.load(f)
    print(f"✓ {contract_file.name}: {contract.get('tool_name')}")
EOF
```

### Handler Response Format Errors

All handlers must return v1 contract envelope:

```json
{
  "ok": true,
  "contract_version": "v1",
  ... tool-specific fields ...
}
```

Or for errors:

```json
{
  "ok": false,
  "contract_version": "v1",
  "error": {
    "code": "ERROR_CODE",
    "message": "Error message",
    "details": {}
  }
}
```

## OpenAI Integration

### Register with Custom GPT

1. Go to ChatGPT → Custom GPTs → Create
2. In **Actions** section:
   - If self-hosting: Add your server URL
   - If using stdio: Configure with OpenAI Apps SDK
3. Import tool schemas from `mcp_tools/contracts/*.v1.json`

### Use with OpenAI Responses API

```python
from openai import OpenAI

client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Check price for ISOROOF 50mm"}],
    tools=[{
        "type": "function",
        "function": {
            "name": "price_check",
            "description": "Look up product pricing",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "filter_type": {"type": "string", "enum": ["sku", "family", "type", "search"]}
                },
                "required": ["query"]
            }
        }
    }]
)
```

## Next Steps

1. ✅ **Tests**: Run `pytest mcp/tests/test_handlers.py` to verify everything works
2. 🚀 **Deploy**: Choose a hosting platform and deploy the server
3. 🔗 **Integrate**: Connect with OpenAI Custom GPT or Responses API
4. 📊 **Monitor**: Use GitHub Actions to track test results and coverage

For more details, see:
- [MCP Architecture](../MCP_CROSSCHECK_EVOLUTION_PLAN.md)
- [KB Audit](../KB_ARCHITECTURE_AUDIT.md)
- [Tool Contracts](../mcp_tools/contracts/)
