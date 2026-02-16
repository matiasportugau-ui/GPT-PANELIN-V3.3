# GPT-PANELIN V3.2 — Improvement Plan

> Generated: 2026-02-14
> Status: Proposed
> Tracks: 6 audit findings → 4 phases of work

---

## Executive Summary

The repository has grown rapidly through Copilot-agent and Claude-agent contributions,
resulting in a functional but fragile system. The six findings below are ordered by
risk and grouped into four implementation phases. Each phase is designed to be
completed independently and produce immediate, measurable value.

---

## Phase 1: Foundation (Week 1) — Eliminate Regression Risk

**Goal:** Ensure recent bug fixes don't regress and critical paths are protected.

### 1.1 Add Tests for BOM Calculations (Critical)

| Item | Detail |
|------|--------|
| **Why** | `mcp/handlers/bom.py` had 3 bug fixes in 2 days (thickness, support, producto_ref). Zero automated tests exist for this module. |
| **What** | Create `mcp/tests/test_bom.py` with pytest |
| **Test cases** | |
| | Happy path: standard panel BOM with known dimensions → expected output |
| | Thickness conversion: input in mm → verify m conversion in formula |
| | Support calc: verify `length_m * autoportancia` (not `width_m`) |
| | Missing producto_ref → graceful error, not crash |
| | Zero/negative thickness → validation error |
| | Oversized dimensions (>100m) → warning or cap |
| **Fixtures** | Minimal `bom_rules.json` subset, mock catalog data |
| **Effort** | Medium (1-2 days) |
| **Owner** | Developer |

### 1.2 Add Tests for Pricing Handler

| Item | Detail |
|------|--------|
| **Why** | `mcp/handlers/pricing.py` had type-hint fixes indicating list-vs-scalar confusion |
| **What** | Create `mcp/tests/test_pricing.py` |
| **Test cases** | |
| | Single product price lookup → correct value |
| | List of products → correct list of prices |
| | Product not found → meaningful error |
| | Malformed pricing JSON → handled gracefully |
| **Effort** | Small (0.5-1 day) |

### 1.3 Add Tests for Quotation Calculator

| Item | Detail |
|------|--------|
| **Why** | `quotation_calculator_v3.py` is 986 lines of core business logic with 0 tests |
| **What** | Create `tests/test_quotation_calculator.py` |
| **Test cases** | Start with 3-5 golden-file tests using known quotation inputs/outputs |
| **Effort** | Medium-Large (2-3 days due to understanding the 986-line module) |

### 1.4 Verify Existing Tests Run

| Item | Detail |
|------|--------|
| **What** | Run all 5 existing test files, fix any broken imports/fixtures |
| **Files** | `.evolucionador/tests/test_*.py`, `openai_ecosystem/test_client.py`, `panelin_reports/test_pdf_generation.py` |
| **Effort** | Small (0.5 day) |

**Phase 1 Deliverables:**
- [ ] `mcp/tests/` directory with `test_bom.py`, `test_pricing.py`
- [ ] `tests/test_quotation_calculator.py` with golden-file tests
- [ ] All 8+ test files passing in CI
- [ ] `pytest.ini` or `pyproject.toml` [tool.pytest] config at repo root

---

## Phase 2: Architecture Cleanup (Week 2) — Reduce Duplication & Drift

### 2.1 Consolidate MCP Integration Paths

| Item | Detail |
|------|--------|
| **Why** | `mcp/` and `panelin_mcp_integration/` contain overlapping business logic. A pricing formula change currently requires updating 2+ files. |
| **What** | Extract shared business logic into a `core/` module |
| **Target layout** | |

```
core/
├── __init__.py
├── pricing.py        # Single source of truth for pricing formulas
├── bom.py            # Single source of truth for BOM calculations
├── catalog.py        # Catalog search logic
└── errors.py         # Shared error types

mcp/
├── server.py         # MCP protocol adapter — imports from core/
├── handlers/         # Thin wrappers calling core/ functions
└── ...

panelin_mcp_integration/
├── panelin_mcp_server.py      # MCP adapter — imports from core/
└── panelin_openai_integration.py  # OpenAI adapter — imports from core/
```

| **Effort** | Medium (2-3 days) |
| **Risk** | Low if tests from Phase 1 are in place first |

### 2.2 Resolve `corrections_log.json` Storage

| Item | Detail |
|------|--------|
| **Why** | Currently tracked in git with an empty array. If the GPT writes to it at runtime, it will cause merge conflicts. If it's never written to, it's dead code. |
| **Decision tree** | |
| | **If used at runtime** → add `corrections_log.json` to `.gitignore`, keep `corrections_log.schema.json` tracked as the template |
| | **If manually curated** → keep in git, add a rotation policy (archive when >50 entries) |
| | **If unused** → delete it |
| **Action** | Search codebase for references, then execute the matching branch |
| **Effort** | Small (0.5 day) |

---

## Phase 3: Documentation Restructure (Week 3) — Reduce Sprawl

### 3.1 Reorganize Documentation

| Item | Detail |
|------|--------|
| **Why** | 23 markdown files at root level. Mixed audiences (developers, operators, internal prompts). Redundant content between README.md and standalone MCP docs. |
| **Target state** | Max 3 `.md` files at root: `README.md`, `LICENSE`, `CONTRIBUTING.md` |

**Migration map:**

| Current File | Action | New Location |
|---|---|---|
| `README.md` | Keep + trim | Root (remove duplicated MCP sections, link to docs/) |
| `MCP_QUICK_START.md` | Move | `docs/getting-started/mcp-quick-start.md` |
| `MCP_USAGE_EXAMPLES.md` | Move | `docs/reference/mcp-examples.md` |
| `MCP_IMPLEMENTATION_SUMMARY.md` | Move | `docs/architecture/mcp-implementation.md` |
| `MCP_CROSSCHECK_EVOLUTION_PLAN.md` | Move | `docs/internal/mcp-evolution-plan.md` |
| `MCP_SERVER_COMPARATIVE_ANALYSIS.md` | Move | `docs/internal/mcp-comparative-analysis.md` |
| `MCP_RESEARCH_PROMPT.md` | Move | `docs/internal/prompts/mcp-research.md` |
| `MCP_AGENT_ARCHITECT_PROMPT.md` | Move | `docs/internal/prompts/mcp-architect.md` |
| `KB_ARCHITECTURE_AUDIT.md` | Move | `docs/internal/audits/kb-architecture.md` |
| `KB_MCP_MIGRATION_PROMPT.md` | Move | `docs/internal/prompts/kb-migration.md` |
| `USER_GUIDE.md` | Move | `docs/guides/user-guide.md` |
| `PANELIN_KNOWLEDGE_BASE_GUIDE.md` | Move | `docs/guides/knowledge-base.md` |
| `PANELIN_QUOTATION_PROCESS.md` | Move | `docs/guides/quotation-process.md` |
| `PANELIN_TRAINING_GUIDE.md` | Move | `docs/guides/training.md` |
| `GPT_INSTRUCTIONS_PRICING.md` | Move | `docs/reference/pricing-instructions.md` |
| `GPT_PDF_INSTRUCTIONS.md` | Move | `docs/reference/pdf-instructions.md` |
| `GPT_OPTIMIZATION_ANALYSIS.md` | Move | `docs/internal/optimization-analysis.md` |
| `GPT_UPLOAD_CHECKLIST.md` | Move | `docs/getting-started/upload-checklist.md` |
| `GPT_UPLOAD_IMPLEMENTATION_SUMMARY.md` | Merge into upload-checklist | Delete |
| `QUICK_START_GPT_UPLOAD.md` | Merge into upload-checklist | Delete |
| `IMPLEMENTATION_SUMMARY_V3.3.md` | Move | `docs/internal/implementation-v3.3.md` |
| `EVOLUCIONADOR_FINAL_REPORT.md` | Move | `docs/internal/evolucionador-report.md` |
| `panelin_context_consolidacion_sin_backend.md` | Move | `docs/architecture/context-consolidation.md` |

| **Effort** | Medium (1-2 days including cross-reference updates) |

### 3.2 Add Documentation Linting

| Item | Detail |
|------|--------|
| **What** | Add `markdownlint` config + CI step |
| **Why** | Prevent broken links, inconsistent formatting, stale content |
| **Effort** | Small (0.5 day) |

---

## Phase 4: Git Hygiene & CI (Week 4) — Prevent Recurrence

### 4.1 Enforce Commit Message Standards

| Item | Detail |
|------|--------|
| **Why** | 5+ "Initial plan" commits pollute history and break `git bisect` |
| **What** | |
| | Add a commit-msg hook (or GitHub Action) that rejects messages matching `^Initial plan$`, `^WIP$`, `^fixup$` |
| | Configure PR merge strategy to **squash merge** on main branch |
| | Add a PR template requiring a description of changes |
| **Effort** | Small (0.5 day) |

### 4.2 Add CI Pipeline

| Item | Detail |
|------|--------|
| **Why** | No CI currently validates code on PR. Tests exist but may not run. |
| **What** | GitHub Actions workflow: |
| | 1. `pip install -r requirements.txt -r mcp/requirements.txt` |
| | 2. `pytest --tb=short` (all test directories) |
| | 3. `markdownlint docs/` |
| | 4. Commit message lint |
| **File** | `.github/workflows/ci.yml` |
| **Effort** | Small-Medium (1 day) |

### 4.3 Branch Protection Rules

| Item | Detail |
|------|--------|
| **What** | Require CI pass + 1 approval before merge to main |
| **Effort** | Small (15 minutes via GitHub UI) |

---

## Priority Summary

| # | Item | Risk if Ignored | Effort | Phase |
|---|------|-----------------|--------|-------|
| 1 | BOM + Pricing tests | **Critical** — silent regressions in quotations | M | 1 |
| 2 | Quotation calculator tests | **High** — 986 lines of untested core logic | M-L | 1 |
| 3 | Consolidate MCP paths | **Medium** — business logic drift between modules | M | 2 |
| 4 | Documentation restructure | **Low-Medium** — developer confusion, stale docs | M | 3 |
| 5 | corrections_log.json | **Low** — currently empty, no immediate harm | S | 2 |
| 6 | Git hygiene + CI | **Medium** — prevents future quality erosion | S-M | 4 |

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Test files covering MCP handlers | 0 | 4 (bom, pricing, catalog, errors) |
| Test files covering core logic | 0 | 1 (quotation calculator) |
| Root-level .md files | 23 | 3 (README, LICENSE, CONTRIBUTING) |
| CI pipeline | None | Green on every PR |
| Duplicate business logic locations | 2 | 1 (core/) |
| Commit message policy | None | Enforced via hook/CI |
