"""MCP tool handlers for GPT-PANELIN.

Each module implements one or more MCP tools:

Core tools (synchronous):
- pricing: price_check tool
- catalog: catalog_search tool
- bom: bom_calculate tool
- errors: report_error tool

Background task tools (async):
- tasks: batch_bom_calculate, bulk_price_check, full_quotation,
         task_status, task_result, task_list, task_cancel
"""
