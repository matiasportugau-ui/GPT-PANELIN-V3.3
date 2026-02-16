"""MCP tool handlers for GPT-PANELIN.

Each module implements one or more MCP tools:

Core tools (synchronous):
- pricing: price_check tool
- catalog: catalog_search tool
- bom: bom_calculate tool
- errors: report_error tool
- quotation: quotation_store tool
- governance: validate_correction, commit_correction tools
  (self-healing architecture for change validation and impact analysis)

Wolf API KB Write tools (v3.4):
- wolf_kb_write: persist_conversation, register_correction,
                 save_customer, lookup_customer

Background task tools (async):
- tasks: batch_bom_calculate, bulk_price_check, full_quotation,
         task_status, task_result, task_list, task_cancel
"""
