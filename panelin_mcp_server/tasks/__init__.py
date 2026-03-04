"""Background task processing for GPT-PANELIN MCP Server.

Provides async task management for long-running operations:
- Batch BOM calculations (multiple panels in one request)
- Bulk pricing lookups (multiple products at once)
- Full quotation generation (BOM + pricing + accessories combined)

Tasks are submitted and tracked via unique IDs, with status polling
and result retrieval through dedicated MCP tools.
"""
