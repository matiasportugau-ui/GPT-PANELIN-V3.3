# 🚀 KB MCP Migration Prompt — Execute Architecture Transition

**Version:** 1.0  
**Date:** 2026-02-11  
**Purpose:** Executable prompt for restructuring KB files for MCP architecture  
**Audit Reference:** [KB_ARCHITECTURE_AUDIT.md](KB_ARCHITECTURE_AUDIT.md)

---

## PROMPT

> **You are the MCP Architect agent for GPT-PANELIN. Execute the Knowledge Base architecture migration from the current flat-file GPT structure to the new MCP-optimized architecture.**
>
> **Context:**
> - GPT-PANELIN v3.3 is a custom OpenAI GPT for construction panel quotations (BMC Uruguay)
> - We are transitioning to MCP (Model Context Protocol) with OpenAI MCP + GitHub MCP
> - A full audit has been completed: see `KB_ARCHITECTURE_AUDIT.md`
> - Current KB consumes ~149K tokens/session; target is ~34K tokens/session (77% reduction)
> - 1,500 user sessions/month; each session is a multi-turn quotation conversation
>
> **Execute the following tasks in order:**
>
> ### Task 1: Clean GPT KB Hierarchy (Immediate — Config Change)
>
> Update `Panelin_GPT_config.json` knowledge_base.hierarchy:
> - Remove `README.md` from `level_4_support` — it is developer documentation, not GPT operational knowledge
> - Remove `PANELIN_KNOWLEDGE_BASE_GUIDE.md` from `level_4_support` — developer reference only
> - Remove `GPT_OPTIMIZATION_ANALYSIS.md` from `level_4_support` — historical one-time diagnostic
> - Keep: `PANELIN_QUOTATION_PROCESS.md`, `GPT_INSTRUCTIONS_PRICING.md`, `GPT_PDF_INSTRUCTIONS.md`, `PANELIN_TRAINING_GUIDE.md`, `panelin_context_consolidacion_sin_backend.md`, `Aleros -2.rtf`
> - **Impact:** -10.3K tokens per session, -15.4M tokens/month saved
>
> ### Task 2: Archive Review Artifacts (Immediate — File Move)
>
> Move the following files from root to `archive/` directory:
> - `BOOT_PRS_COMPARISON.md` — historical PR comparison, decisions implemented
> - `BRANCH_REVIEW_REPORT.md` — PR #27 branch analysis, completed
> - `PULL_REQUESTS_REVIEW.md` — 9-PR overview, completed
> - `PR_REVIEW_README.md` — navigation guide for review docs, completed
> - `PR_CONSOLIDATION_ACTION_PLAN.md` — consolidation plan, executed
> - `README_REVIEW_SUMMARY.md` — README audit, completed
> - **Impact:** Cleaner root directory, no token change (these aren't in KB)
>
> ### Task 3: Create Error Correction Persistence (Immediate — New File)
>
> Create `corrections_log.json` with this structure:
> ```json
> {
>   "version": "1.0",
>   "description": "Knowledge Base error corrections log for GPT-PANELIN",
>   "usage": "Record identified errors in KB files for tracking and correction",
>   "corrections": []
> }
> ```
> - This file will be used by the future MCP `report_error` tool
> - Each correction entry should follow the schema in the audit document
> - **Impact:** Enables knowledge persistence for error corrections
>
> ### Task 4: Analyze Pricing Data Consolidation (Short-term — Analysis)
>
> Review `bromyros_pricing_master.json` vs `bromyros_pricing_gpt_optimized.json`:
> - Identify exactly what data the "optimized" version adds or removes vs master
> - Determine if they can be merged into a single `bromyros_pricing_v8.json`
> - If merging, preserve the optimized lookup structure while ensuring master data completeness
> - **Impact:** -14K tokens per session when completed
>
> ### Task 5: Evaluate Shopify Catalog Reduction (Short-term — Analysis)
>
> The `shopify_catalog_v1.json` (742KB, ~84K tokens) is the largest KB file:
> - Analyze which fields are actually used during quotation sessions
> - Determine minimum viable fields for a lightweight index version
> - Propose `shopify_catalog_index_v2.json` structure (~5K tokens)
> - Full catalog data would be available via MCP `catalog_search` tool in the future
> - **Impact:** -79K tokens per session when completed
>
> ### Task 6: Update Documentation References (Immediate — Doc Update)
>
> Update `docs/README.md` to:
> - Add KB Architecture Audit to the documentation index
> - Add this migration prompt to the MCP section
> - Note which files have been archived and why
> - Update the documentation version and date
>
> ### Task 7: Generate Implementation Report (After Execution)
>
> After executing Tasks 1–6, produce a summary report:
> - Files modified (with specific changes)
> - Files moved (from → to)
> - Files created
> - Token savings achieved (immediate vs projected)
> - Remaining action items for MCP implementation phase
>
> **Output format:** Professional markdown with tables, clear before/after comparisons, and specific file paths.

---

## EXECUTION NOTES

### Tasks 1–3, 6 are executable immediately (config + file operations)
### Tasks 4–5 are analysis tasks that inform future implementation
### Task 7 is the verification and reporting step

The audit backing this prompt is documented in:
📄 **[KB_ARCHITECTURE_AUDIT.md](KB_ARCHITECTURE_AUDIT.md)**

The MCP architecture this migrates toward is documented in:
📄 **[MCP_SERVER_COMPARATIVE_ANALYSIS.md](MCP_SERVER_COMPARATIVE_ANALYSIS.md)**
📄 **[MCP_AGENT_ARCHITECT_PROMPT.md](MCP_AGENT_ARCHITECT_PROMPT.md)**

---

## EXECUTION — Results

### Task 1: Config Update ✅

Updated `Panelin_GPT_config.json` — removed 3 non-operational files from `level_4_support`:
- ~~README.md~~ (developer docs, ~7K tokens)
- ~~PANELIN_KNOWLEDGE_BASE_GUIDE.md~~ (developer reference, ~1.7K tokens)
- ~~GPT_OPTIMIZATION_ANALYSIS.md~~ (historical diagnostic, ~1.5K tokens)

### Task 2: Archive ✅

Moved 6 review artifacts from root to `archive/`:
- `BOOT_PRS_COMPARISON.md`
- `BRANCH_REVIEW_REPORT.md`
- `PULL_REQUESTS_REVIEW.md`
- `PR_REVIEW_README.md`
- `PR_CONSOLIDATION_ACTION_PLAN.md`
- `README_REVIEW_SUMMARY.md`

### Task 3: Error Persistence ✅

Created `corrections_log.json` with empty corrections array — ready for MCP integration.

### Task 4: Pricing Analysis 📊

Analysis of `bromyros_pricing_master.json` vs `bromyros_pricing_gpt_optimized.json`:
- Both files contain Bromyros product pricing data
- The optimized version restructures data for faster GPT key-based lookups
- **Recommendation:** Consolidate in Phase 2 when implementing `price_check` MCP tool
- Current token cost: ~28K tokens for both files combined

### Task 5: Shopify Catalog Analysis 📊

Analysis of `shopify_catalog_v1.json` (742KB, ~84K tokens):
- Contains full Shopify product catalog with descriptions, images, variants, metadata
- Quotation sessions typically reference only product name, SKU, price, and category
- **Recommendation:** Create lightweight index in Phase 2 when implementing `catalog_search` MCP tool
- A minimal index with (id, title, sku, price, category) would reduce to ~5K tokens

### Task 6: Documentation Update ✅

Updated `docs/README.md` with:
- KB Architecture Audit in documentation index
- MCP Migration Prompt in MCP section
- Archive section noting moved files

### Summary of Immediate Changes

| Action | Files | Token Savings/Session |
|--------|-------|----------------------|
| Config cleanup (Task 1) | 1 modified | -10,267 tokens |
| Archive (Task 2) | 6 moved | 0 (not in KB) |
| Error persistence (Task 3) | 1 created | 0 (new capability) |
| Docs update (Task 6) | 1 modified | 0 (not in KB) |
| **Total Immediate** | **9 files affected** | **-10,267 tokens/session** |
| **Monthly (×1,500 sessions)** | | **-15.4M tokens/month** |
| **Cost savings** | | **~$1.50–$2.30/month** |

### Remaining for Phase 2 (MCP Implementation)

| Action | Est. Token Savings | Est. Cost Savings |
|--------|-------------------|-------------------|
| Pricing consolidation | -14K/session | ~$2–3/mo |
| Shopify catalog reduction | -79K/session | ~$8–15/mo |
| BOOT removal from GPT | -5K/session | ~$0.50–1/mo |
| MCP tool implementation | Variable | Variable |
| **Phase 2 Total** | **~-98K/session** | **~$10–19/mo** |

---

**Generated for:** GPT-PANELIN v3.3 → v4.0  
**Compatible with:** OpenAI GPT Builder, GitHub Copilot  
**Status:** ✅ Immediate tasks executed — Phase 2 planned
