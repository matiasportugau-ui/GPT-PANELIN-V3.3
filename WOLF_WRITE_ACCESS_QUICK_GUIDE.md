# Wolf API Write Access - Quick Reference Guide

## ✅ Summary

**YES - Wolf has writing access to modify the Knowledge Base (KB) for GPT**

The Wolf API client is configured with three write operations that allow GPT to:
1. Save conversation summaries
2. Register KB corrections
3. Store customer data

All write operations are **password-protected** and require **API key authentication**.

---

## 🔐 Environment Setup

### Required Variables

```bash
# .env file configuration
WOLF_API_KEY="your_api_key_here"                # Required
WOLF_API_URL="https://panelin-api-642127786762.us-central1.run.app"
WOLF_KB_WRITE_PASSWORD="your_secure_password"   # Override default "mywolfy"
```

### Quick Setup

```bash
# Copy example environment file
cp .env.example .env

# Edit and set your values
nano .env
```

---

## 📝 Available Write Operations

| Operation | Requires Password | Purpose |
|-----------|-------------------|---------|
| `persist_conversation` | ✅ Yes | Save conversation summaries and quotation history |
| `register_correction` | ✅ Yes | Register KB corrections detected during conversations |
| `save_customer` | ✅ Yes | Store customer data for future quotations |
| `lookup_customer` | ❌ No | Retrieve existing customer data (read-only) |

---

## 🧪 Quick Verification

### Run Verification Script

```bash
# Make executable
chmod +x scripts/verify_wolf_write_access.sh

# Run verification
./scripts/verify_wolf_write_access.sh
```

### Run Unit Tests

```bash
# Install dependencies
pip install pytest pytest-asyncio

# Run tests (20 test cases)
pytest mcp/tests/test_wolf_kb_write.py -v
```

---

## 🔍 Example Usage

### From GPT (via MCP)

```python
# Example: Register a KB correction
await mcp_client.call_tool(
    name="register_correction",
    arguments={
        "source_file": "bromyros_pricing_master.json",
        "field_path": "products[0].price_usd",
        "old_value": "100.00",
        "new_value": "105.50",
        "reason": "Price updated per BMC Feb 2026",
        "password": "mywolfy"  # Or value from WOLF_KB_WRITE_PASSWORD
    }
)
```

### From Python Code

```python
from panelin_mcp_integration.panelin_mcp_server import PanelinMCPServer

# Initialize client
client = PanelinMCPServer(
    api_key="your_api_key",
    base_url="https://panelin-api-642127786762.us-central1.run.app"
)

# Save customer data
result = client.save_customer(
    name="Juan Perez",
    phone="091234567",
    address="Av. Rivera 1234"
)
```

---

## 🛡️ Security Features

✅ **Password Protection**: All write operations require password validation  
✅ **API Key Auth**: X-API-Key header required for all requests  
✅ **Input Validation**: Phone format, required fields, field path injection prevention  
✅ **Error Handling**: Proper error codes and messages  
✅ **Audit Logging**: All operations logged for compliance  

---

## 📊 Test Coverage

| Test Category | Test Cases | Status |
|--------------|------------|--------|
| Password Validation | 5 tests | ✅ Pass |
| Input Validation | 6 tests | ✅ Pass |
| Success Scenarios | 5 tests | ✅ Pass |
| API Failure Handling | 2 tests | ✅ Pass |
| Error Codes | 2 tests | ✅ Pass |
| **TOTAL** | **20 tests** | **✅ 100%** |

---

## ⚠️ Important Notes

### Default Password Warning

The default password is `"mywolfy"` if `WOLF_KB_WRITE_PASSWORD` is not set.

**ALWAYS set a custom password in production!**

```bash
# In .env file
WOLF_KB_WRITE_PASSWORD="YourSecurePassword123!@#"
```

### Phone Number Format

For `save_customer` operation, phone must be in Uruguayan format:
- `09XXXXXXX` (9 digits)
- `+598XXXXXXXX` (12 characters)

**Valid examples:**
- `"091234567"`
- `"+59891234567"`
- `"091 234 567"` (normalized automatically)

**Invalid examples:**
- `"12345"` ❌
- `"1234567890"` ❌

---

## 📄 Additional Documentation

- **Full Verification Report:** `WOLF_KB_WRITE_ACCESS_VERIFICATION.md`
- **Implementation Details:** `mcp/handlers/wolf_kb_write.py`
- **Wolf Client:** `panelin_mcp_integration/panelin_mcp_server.py`
- **Unit Tests:** `mcp/tests/test_wolf_kb_write.py`
- **MCP Server:** `mcp/server.py` (lines 166-172)

---

## 🚀 Next Steps

1. ✅ **Verified:** Wolf has write access to KB
2. 📝 **Set:** `WOLF_API_KEY` in production environment
3. 🔐 **Change:** `WOLF_KB_WRITE_PASSWORD` from default
4. 🧪 **Test:** Run verification script
5. 🎯 **Deploy:** Enable GPT KB modification features

---

## 📞 Support

For API key provisioning or technical questions:
- Contact: System Administrator
- Documentation: See `WOLF_KB_WRITE_ACCESS_VERIFICATION.md`
- Tests: `pytest mcp/tests/test_wolf_kb_write.py -v`

---

**Last Updated:** 2026-02-16  
**Version:** 1.0  
**Status:** ✅ Verified & Production-Ready
