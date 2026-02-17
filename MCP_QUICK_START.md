# MCP Server Quick Start Guide

**Panelin MCP Server** - Get your Model Context Protocol server running in under 5 minutes.

---

## 🚀 Quick Setup (3 Steps)

### Step 1: Install Dependencies

```bash
# From the repository root
pip install -r mcp/requirements.txt
```

This installs:
- `mcp>=1.0.0` - Model Context Protocol SDK
- `uvicorn>=0.30.0` - ASGI server (for remote hosting)
- `starlette>=0.40.0` - Web framework
- `httpx>=0.27.0` - HTTP client
- `pydantic>=2.0.0` - Data validation

### Step 2: Start the Server

**Important:** Run the server from the repository root (not from inside the `mcp/` directory) to ensure the local package is used.

**For local testing (stdio transport):**
```bash
# From the repository root
python -m mcp.server
```

**For remote hosting (SSE transport):**
```bash
# From the repository root
python -m mcp.server --transport sse --port 8000
```

### Step 3: Test the Connection

**With stdio transport:**
The server communicates via standard input/output. Use an MCP client like Claude Desktop to connect.

**With SSE transport:**
```bash
# The SSE endpoint will keep the connection open (Server-Sent Events stream).
# To verify the server is running, check the server logs for startup messages,
# or use a proper MCP client that can communicate with SSE endpoints.

# If you need to verify the server is listening:
curl --max-time 2 http://localhost:8000/messages 2>&1 | grep -q "Method Not Allowed\|404" && echo "Server is running" || echo "Server not responding"
```

---

## 🔧 Available Tools

Your MCP server exposes 4 tools:

| Tool | Purpose | Example Query |
|------|---------|---------------|
| `price_check` | Look up product pricing | "What's the price of ISODEC-100-1000?" |
| `catalog_search` | Search product catalog | "Find panels for industrial roofs" |
| `bom_calculate` | Calculate Bill of Materials | Generate complete BOM for 12m x 6m roof installation |
| `report_error` | Log KB errors | Report incorrect pricing in knowledge base |

### Additional Tools (v3.4+)

**Variable Modification Tools:**
- `register_correction` - Register corrections to catalog data (requires password)
- `validate_correction` - Validate impact of proposed corrections
- `commit_correction` - Apply validated corrections

See [GPT_WEIGHT_MODIFICATION_GUIDE.md](GPT_WEIGHT_MODIFICATION_GUIDE.md) for details on modification capabilities.

---

## 💡 Integration Examples

There are two distinct integration paths in this project:

### 1. MCP-compatible Clients (Model Context Protocol)

**For local MCP clients (Claude Desktop, IDE extensions, etc.):**

1. Start server with stdio transport: `python -m mcp.server` (from repo root)
2. Configure your MCP client to point to the server executable
3. The client will discover available tools from the MCP protocol

**For remote MCP clients:**

1. Start server with SSE transport: `python -m mcp.server --transport sse --port 8000`
2. Configure your MCP client to connect to the SSE endpoint
3. Tools will be available via the MCP protocol over HTTP

**MCP tool schemas are available at:**
- `mcp/tools/price_check.json`
- `mcp/tools/catalog_search.json`
- `mcp/tools/bom_calculate.json`
- `mcp/tools/report_error.json`

These JSON files describe MCP tools and are consumed by MCP-aware clients.

### 2. OpenAI Custom GPT Actions (HTTP / OpenAPI-based)

**Note:** OpenAI Custom GPT Actions use HTTP endpoints defined by OpenAPI schemas, which is a different integration approach than MCP.

To integrate with OpenAI Custom GPT Actions:

1. Deploy the SSE transport server: `python -m mcp.server --transport sse --port 8000`
2. Create HTTP endpoint wrappers that expose the MCP tools as REST APIs
3. Generate an OpenAPI schema for those HTTP endpoints
4. In OpenAI GPT Builder, import the OpenAPI specification
5. Configure authentication for your deployed HTTP endpoints

The MCP server's stdio transport cannot be used directly with OpenAI Custom GPT Actions, as Actions require HTTP endpoints.

---

## 📊 Benefits

| Benefit | Impact |
|---------|--------|
| **Token Savings** | 77% reduction (149K → 34K tokens/session) |
| **Real-time Data** | Dynamic queries instead of static KB files |
| **Error Tracking** | Persistent KB error logging |
| **Standard Protocol** | Works with any MCP client |
| **Scalability** | External data doesn't consume context window |

---

## 🆘 Troubleshooting

**Issue: "Module 'mcp' not found"**
- Solution: Run `pip install -r requirements.txt` from the `mcp/` directory

**Issue: "Port 8000 already in use"**
- Solution: Use a different port: `python -m mcp.server --transport sse --port 8001`

**Issue: "Cannot connect to stdio server"**
- Solution: Ensure your MCP client is configured for stdio transport, not SSE

**Issue: "Tool handler error"**
- Solution: Check that all KB files exist in the parent directory (bromyros_pricing_master.json, etc.)

---

## 📚 Next Steps

- Read the full [MCP Server Documentation](README.md#-mcp-server)
- Review [Tool Schemas](mcp/tools/)
- Check [MCP Comparative Analysis](MCP_SERVER_COMPARATIVE_ANALYSIS.md)
- See [KB Architecture Audit](KB_ARCHITECTURE_AUDIT.md) for optimization details

---

**Status:** ✅ Production Ready | **Version:** 1.0.0  
**Support:** See [README.md](README.md) for detailed documentation
