# GPT-PANELIN-V3.3 — Final Repository Review & Documentation

**Date**: 2026-02-25  
**Branch**: `cursor/initial-repository-structure-2a28`  
**Reviewer**: Automated deep-review  
**Scope**: Full repository audit — architecture, data, code, infrastructure, and restructured directories

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Repository Manifest](#2-repository-manifest)
3. [Architecture Overview](#3-architecture-overview)
4. [Knowledge Base Audit](#4-knowledge-base-audit)
5. [Core Engine Review](#5-core-engine-review)
6. [Infrastructure & Deployment](#6-infrastructure--deployment)
7. [New Structured Directories Audit](#7-new-structured-directories-audit)
8. [Quality Findings (P0/P1/P2)](#8-quality-findings-p0p1p2)
9. [SAI Score Assessment](#9-sai-score-assessment)
10. [Migration Gap Analysis](#10-migration-gap-analysis)
11. [Prioritized Backlog](#11-prioritized-backlog)
12. [Test Coverage Report](#12-test-coverage-report)
13. [Security Review](#13-security-review)
14. [Recommendations](#14-recommendations)

---

## 1. Executive Summary

GPT-PANELIN-V3.3 is a production AI assistant system for **BMC Uruguay** panel quotations. It combines an OpenAI GPT assistant with a multi-layered knowledge base, MCP protocol server, Wolf API backend, and autonomous evolution capabilities.

### What Works Well
- **Deterministic calculation engine** (`quotation_calculator_v3.py`) — uses Python Decimal, never delegates math to the LLM
- **Rich knowledge base** — 7+ production JSON files with real pricing from BROMYROS, 70+ accessories, 6 construction systems
- **Parametric BOM rules** (`bom_rules.json`) — complete formulas for all 6 systems with autoportancia tables
- **MCP Server** — 30+ tools with contract-based definitions, observability, and background task support
- **Wolf API** — Event-sourced KB versioning with rollback, GCS storage, PostgreSQL audit logs
- **CI/CD** — 7 GitHub Actions workflows covering validation, testing, and deployment
- **Autonomous evolution** — EVOLUCIONADOR system with daily analysis

### What Needs Work
- **New structured directories** (`kb/`, `rules/`, `schemas/`, `tests/`) contain only **placeholder data** — no migration from production files yet
- **kb_self_learning module** has critical architectural issues (in-memory state, no DB persistence, no auth)
- **Currency/IVA mismatch** between old (USD/22%) and new (ARS/21%) structures
- **No automated test runner** for the YAML test cases

### SAI Score: 68/100 (see Section 9)

---

## 2. Repository Manifest

### Directory Structure

```
/workspace/
├── kb/                          # NEW: Structured knowledge base (placeholders)
│   ├── catalog.csv
│   ├── pricing.csv
│   ├── accessories_map.json
│   └── autoportancia.csv
├── rules/                       # NEW: BOM rules & validations (placeholders)
│   ├── bom_rules_vertical.json
│   ├── bom_rules_horizontal.json
│   ├── validations_vertical.json
│   └── validations_horizontal.json
├── schemas/                     # NEW: Output contracts
│   └── quote_output.schema.json
├── tests/                       # NEW: Test scenarios (YAML)
│   ├── test_vertical_basic.yaml
│   ├── test_horizontal_span_missing.yaml
│   ├── test_horizontal_autoportancia_missing.yaml
│   ├── test_horizontal_span_ok.yaml
│   ├── test_unit_complete_subtotals.yaml
│   ├── test_accessory_ambiguity.yaml
│   └── test_missing_price.yaml
├── docs/                        # Documentation
│   ├── kb_contract.md           # NEW: KB contract definition
│   ├── units_and_rounding.md    # NEW: Units standardization
│   ├── mcp/                     # MCP documentation
│   └── README.md
├── .evolucionador/              # Autonomous evolution system
│   ├── core/                    # Analyzer, validator, optimizer
│   ├── reports/                 # Evolution reports
│   ├── knowledge/               # Patterns, benchmarks
│   └── tests/
├── .github/workflows/           # CI/CD (7 workflows)
├── backend/                     # Flask API (chat, conversations)
├── mcp/                         # MCP Server (30+ tools)
│   ├── handlers/                # 10 tool handler modules
│   ├── storage/                 # FileStore / QdrantStore
│   ├── tasks/                   # Background task manager
│   └── tools/                   # Tool JSON definitions
├── wolf_api/                    # FastAPI KB write operations
├── panelin_reports/             # PDF generation
├── kb_pipeline/                 # Index builder
├── kb_self_learning/            # Self-learning module (WIP)
├── frontend/                    # Web interface
├── config/                      # Production config
├── scripts/                     # Deployment & utility scripts
├── terraform/                   # GCP infrastructure
├── observability/               # Cost monitoring & metrics
├── openai_ecosystem/            # OpenAI API normalizer
├── artifacts/hot/               # Hot-reload optimized files
└── archive/                     # Historical documentation
```

### Key Production Files (Root Level)

| File | Size | Purpose | Real Data? |
|------|------|---------|------------|
| `bom_rules.json` | 20 KB | Parametric BOM rules, 6 systems, autoportancia | Yes |
| `accessories_catalog.json` | 49 KB | 70+ accessories with real prices | Yes |
| `BMC_Base_Conocimiento_GPT-2.json` | 16 KB | Master KB v6.0 — prices, formulas, rules | Yes |
| `BMC_Base_Unificada_v4.json` | 11 KB | Validated formulas (31 real quotes) | Yes |
| `bromyros_pricing_gpt_optimized.json` | 132 KB | Optimized pricing index (96 products) | Yes |
| `bromyros_pricing_master.json` | 142 KB | Master pricing (fallback) | Yes |
| `shopify_catalog_v1.json` | 760 KB | Full Shopify catalog | Yes |
| `normalized_full_cleaned.csv` | 60 KB | Master pricing CSV from BROMYROS 2026 | Yes |
| `perfileria_index.json` | 15 KB | Profile price index (59 items) | Yes |
| `Panelin_GPT_config.json` | 32 KB | Complete GPT assistant config v2.5 | Yes |
| `quotation_calculator_v3.py` | 47 KB | Deterministic calculation engine | Yes |
| `corrections_log.json` | 7 KB | Error correction tracking | Mixed |

### File Count by Type

| Extension | Count | Notes |
|-----------|-------|-------|
| `.py` | ~107 | Core logic, MCP handlers, scripts, tests |
| `.json` | ~77 | KB, configs, schemas, tool definitions |
| `.md` | ~115 | Documentation, guides, reports |
| `.yaml/.yml` | ~12 | CI/CD workflows, test cases, config |
| `.csv` | ~5 | Pricing, catalog data |
| `.sh` | ~5 | Deployment and utility scripts |
| `.rtf` | 3 | Legacy support documents |

---

## 3. Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER (Chat / API)                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│               OpenAI GPT Assistant                              │
│  (Panelin - BMC Assistant Pro, Instructions v2.5 Canonical)     │
│  KB Hierarchy: L1 Master → L2 Validation → L3 Dynamic → L4     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
┌─────────▼─────┐  ┌──────▼──────┐  ┌──────▼──────┐
│  Code          │  │  MCP Server │  │  Wolf API   │
│  Interpreter   │  │  (30+ tools)│  │  (FastAPI)  │
│  (PDF, Calc)   │  │  stdio/SSE  │  │  KB Write   │
└─────────┬─────┘  └──────┬──────┘  └──────┬──────┘
          │                │                │
┌─────────▼────────────────▼────────────────▼─────────────────────┐
│                    Knowledge Base Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │ JSON KBs     │  │ CSV Data     │  │ GCS / PostgreSQL   │    │
│  │ (pricing,    │  │ (Shopify,    │  │ (conversations,    │    │
│  │  BOM rules,  │  │  normalized) │  │  corrections,      │    │
│  │  accessories)│  │              │  │  customers, audit)  │    │
│  └──────────────┘  └──────────────┘  └────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Envelope Engine (Orquestación)

The GPT operates with an **Envelope Engine** that classifies requests into:

| Phase | Description |
|-------|-------------|
| **VERTICAL** | Wall systems (ISOPANEL EPS, ISOWALL PIR, ISOFRIG PIR) |
| **HORIZONTAL** | Roof systems (ISODEC EPS/PIR, ISOROOF 3G) — requires `span_m` + autoportancia |
| **UNIT_COMPLETE** | Combined wall + roof — separate subtotals, unified total |

### Data Flow

1. User provides project parameters (system, dimensions, thickness)
2. Engine validates inputs (P0 hard-stops for missing critical data)
3. System selects appropriate BOM rules by construction system
4. Calculator computes quantities using deterministic formulas (ceil rounding)
5. Pricing lookup against KB hierarchy (L1 Master priority)
6. Output: itemized quote with traceability (rule_id → line_item)

---

## 4. Knowledge Base Audit

### Production KB (Root Level) — Status: ACTIVE

| Component | Status | Quality | Notes |
|-----------|--------|---------|-------|
| `BMC_Base_Conocimiento_GPT-2.json` | Active | High | Master KB v6.0, validated formulas, user corrections |
| `bromyros_pricing_master.json` | Active | High | 96 products, 11 families, BROMYROS cost matrix 2026 |
| `bromyros_pricing_gpt_optimized.json` | Active | High | Fast-lookup indices by SKU/family/type |
| `accessories_catalog.json` | Active | High | 70+ items, real prices, compatibility mappings |
| `bom_rules.json` | Active | High | 6 systems, parametric formulas, autoportancia tables |
| `shopify_catalog_v1.json` | Active | High | Full Shopify catalog (descriptions, images, variants) |
| `normalized_full_cleaned.csv` | Active | High | Master pricing CSV with cost/sale/web prices |
| `perfileria_index.json` | Active | High | 59 profiles/accessories with per-meter pricing |
| `BMC_Base_Unificada_v4.json` | Active | High | Validation reference (31 real quotes) |
| `panelin_truth_bmcuruguay_web_only_v2.json` | Active | Medium | Shopify snapshot, needs refresh policy |

### KB Conventions (Production)

| Convention | Value | Notes |
|------------|-------|-------|
| Currency | USD | All prices in US dollars |
| IVA Rate | 22% | Already included in unit prices |
| IVA Treatment | Included | NEVER add IVA on top |
| Rounding | ceil | Always round up (panels, profiles, fixations) |
| Standard Units | m2, ml, unid, tubo, kit | See bom_rules.json |

### KB Hierarchy (from GPT Config)

```
Level 1   Master:    BMC_Base_Conocimiento_GPT-2.json, bromyros_pricing_master.json
Level 1.2 Accessories: accessories_catalog.json (70+ items)
Level 1.3 BOM Rules:   bom_rules.json (6 systems)
Level 1.5 Fast Lookup:  bromyros_pricing_gpt_optimized.json
Level 1.6 Catalog:     shopify_catalog_v1.json + index CSV
Level 2   Validation:  BMC_Base_Unificada_v4.json
Level 3   Dynamic:     panelin_truth_bmcuruguay_web_only_v2.json
Level 4   Support:     RTF files, process guides, training guides
```

---

## 5. Core Engine Review

### `quotation_calculator_v3.py` (1,281 lines)

**Quality: HIGH**

| Aspect | Assessment |
|--------|------------|
| Financial precision | Uses `decimal.Decimal` — no floating-point errors |
| Thread safety | `threading.Lock` for cached data |
| Autoportancia validation | Complete — checks span vs manufacturer limits |
| Accessories | Integrated with 97-item catalog |
| BOM system selection | All 6 systems supported |
| Error handling | Defensive with fallback paths |
| Traceability | `calculation_verified: True` flag on all outputs |

**Key Functions**:
- `calculate_panel_quote()` — Main entry point
- `validate_autoportancia()` — Span/load validation with hard-stop
- `calculate_accessories()` — System-specific accessory BOM
- `calculate_accessories_pricing()` — V3 pricing valorization
- `suggest_optimization()` — Waste reduction recommendations
- `lookup_product_specs()` — Indexed product search

### `bom_rules.json` (655 lines)

**Quality: HIGH**

| System | Formulas | Autoportancia | Status |
|--------|----------|---------------|--------|
| `techo_isodec_eps` | Complete | 4 thickness variants | Production |
| `techo_isodec_pir` | Complete | 4 thickness variants | Production |
| `techo_isoroof_3g` | Complete | 4 thickness variants | Production |
| `pared_isopanel_eps` | Complete | N/A (wall) | Production |
| `pared_isowall_pir` | Complete | N/A (wall) | Production |
| `pared_isofrig_pir` | Complete | N/A (wall) | Production |

---

## 6. Infrastructure & Deployment

### MCP Server (`/mcp/`)

| Feature | Status | Notes |
|---------|--------|-------|
| Transport | stdio + SSE | Dual transport support |
| Tools | 30+ registered | Contracts in `/mcp_tools/contracts/` |
| Storage | FileStore + Qdrant (optional) | Graceful degradation |
| Background Tasks | TaskManager with concurrency limits | Batch BOM, bulk pricing |
| Observability | JSONL structured logging | Token counting, latency, error codes |
| Wolf API Integration | Full CRUD | Conversations, corrections, customers |

### Wolf API (`/wolf_api/`)

| Feature | Status | Notes |
|---------|--------|-------|
| Framework | FastAPI | Async with SQLAlchemy |
| Storage | GCS (JSONL) + PostgreSQL | Event-sourced versioning |
| KB Versioning | SHA-256 checksums | Create, rollback, audit |
| Auth | API key + KB write password | Constant-time comparison |
| Endpoints | 9 routes | CRUD + versioning + health |

### CI/CD Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci-cd.yml` | push/PR | JSON validation, tests, Docker build, deploy |
| `deploy-wolf-api.yml` | manual/push | Wolf API Docker build + Cloud Run deploy |
| `deploy-gpt-assistant.yml` | manual | Validate KB + deploy OpenAI Assistant |
| `mcp-tests.yml` | push/PR | MCP handler tests with coverage |
| `evolucionador-daily.yml` | cron (daily) | Autonomous evolution analysis |
| `generate-gpt-config.yml` | manual | GPT config generation |
| `health-check.yml` | cron | System health monitoring |

### Deployment Stack

| Component | Technology |
|-----------|-----------|
| Containers | Docker (multi-stage builds) |
| Orchestration | Docker Compose (local), Cloud Run (prod) |
| IaC | Terraform (GCP) |
| Database | Cloud SQL PostgreSQL |
| Storage | Google Cloud Storage |
| Secrets | Google Secret Manager |
| Registry | Artifact Registry |
| CI/CD | GitHub Actions |

---

## 7. New Structured Directories Audit

### Status: PLACEHOLDER ONLY — Migration Pending

The new directories (`kb/`, `rules/`, `schemas/`, `tests/`, `docs/`) provide an excellent **target architecture** but currently contain only placeholder data.

#### `kb/` Directory

| File | Rows | Real Data? | Gap vs Production |
|------|------|------------|-------------------|
| `catalog.csv` | 11 SKUs | No (PLACEHOLDER_*) | Production has 96+ real products |
| `pricing.csv` | 11 rows | No (prices empty) | Production has full BROMYROS pricing |
| `accessories_map.json` | 2 rules | No (PLACEHOLDER SKUs) | Production has 70+ accessories |
| `autoportancia.csv` | 1 row | No (all PLACEHOLDER) | Production has 12+ validated entries |

#### `rules/` Directory

| File | Rules | Real Data? | Gap vs Production |
|------|-------|------------|-------------------|
| `bom_rules_vertical.json` | 2 rules | No (PLACEHOLDER formulas) | `bom_rules.json` has 3 wall systems |
| `bom_rules_horizontal.json` | 2 rules | No (PLACEHOLDER formulas) | `bom_rules.json` has 3 roof systems |
| `validations_vertical.json` | 1 validation | No (basic only) | Missing dimensional checks |
| `validations_horizontal.json` | 2 validations | Partial (P0 messages correct) | Hard-stop messages are accurate |

#### `schemas/` Directory

| File | Status | Notes |
|------|--------|-------|
| `quote_output.schema.json` | Complete | Good JSON Schema 2020-12, ready for validation |

#### `tests/` Directory

| Test | Scenario | Status |
|------|----------|--------|
| `test_vertical_basic.yaml` | Standard VERTICAL quote | Well-defined |
| `test_horizontal_span_missing.yaml` | P0: missing span_m | Correct hard-stop message |
| `test_horizontal_autoportancia_missing.yaml` | P0: no autoportancia match | Correct hard-stop message |
| `test_horizontal_span_ok.yaml` | Valid HORIZONTAL | Well-defined |
| `test_unit_complete_subtotals.yaml` | UNIT_COMPLETE | Correct structure |
| `test_accessory_ambiguity.yaml` | Ambiguous accessory | Good disambiguation test |
| `test_missing_price.yaml` | No price data | Correct hard-stop message |

### Critical Inconsistencies

| Issue | Old (Production) | New (Structured) | Impact |
|-------|-------------------|-------------------|--------|
| **Currency** | USD | ARS | Will produce wrong quotes if used |
| **IVA Rate** | 22% (0.22) | 21% (0.21) | Tax calculations will be incorrect |
| **SKUs** | Real (e.g., "6805", "IROOF50") | PLACEHOLDER_* | Cannot match to products |
| **Systems** | 6 named systems | 2 generic (VERTICAL/HORIZONTAL) | Loses granularity |
| **Autoportancia** | 12+ validated rows | 1 placeholder row | Cannot validate spans |

---

## 8. Quality Findings (P0/P1/P2)

### P0 — Critical (Blocks Production)

| ID | Component | Finding | Impact |
|----|-----------|---------|--------|
| P0-001 | `kb/pricing.csv` | Currency = ARS, IVA = 0.21 (should be USD, 0.22) | Inconsistent with production config |
| P0-002 | `kb/` (all files) | All PLACEHOLDER data — not usable for real quotes | New structure not production-ready |
| P0-003 | `kb_self_learning/` | No database persistence (in-memory only) | Data lost on restart |
| P0-004 | `kb_self_learning/` | FastAPI routers not registered | Endpoints inaccessible |
| P0-005 | `kb_self_learning/` | No authentication despite config requiring it | Security gap |
| P0-006 | New vs Old | No migration path defined between root files and `kb/`/`rules/` | Dual source of truth |

### P1 — High (Should Fix)

| ID | Component | Finding | Impact |
|----|-----------|---------|--------|
| P1-001 | `rules/` | Only 2 generic systems vs 6 in production | Cannot support ISODEC/ISOFRIG/etc. |
| P1-002 | `kb/autoportancia.csv` | 1 placeholder row vs 12+ validated | Cannot validate horizontal spans |
| P1-003 | `tests/` | No test runner — YAML tests are spec-only | Cannot verify behavior automatically |
| P1-004 | `corrections_log.json` | Contains test entries mixed with real data | Audit trail pollution |
| P1-005 | `quotation_calculator_v3.py` | Path traversal risk in file loading | Security concern |
| P1-006 | Multiple scripts | Missing file size validation on uploads | DoS risk |
| P1-007 | `quote_output.schema.json` | Not connected to any validation pipeline | Schema exists but unused |

### P2 — Medium (Product Quality)

| ID | Component | Finding | Impact |
|----|-----------|---------|--------|
| P2-001 | PDF generation | Template exists but not integrated with new schema | Output format inconsistency |
| P2-002 | Traceability | `rule_id → line_items` in schema but not in calculator | Cannot trace which rule produced which item |
| P2-003 | Multi-currency | Only USD supported, new structure mentions ARS | No regional support |
| P2-004 | `observability/` | Baseline costs hardcoded | Not configurable per deployment |
| P2-005 | Shell scripts | Bash-specific, may not work on all systems | Portability |
| P2-006 | `requirements.txt` | `asyncio>=3.4.3` listed (it's stdlib) | Misleading dependency |

---

## 9. SAI Score Assessment

**SAI (System Architecture Index) — Estimated: 68/100**

| Dimension | Weight | Score | Weighted | Notes |
|-----------|--------|-------|----------|-------|
| Orchestration (Envelope Engine) | 15% | 9/10 | 13.5 | VERTICAL/HORIZONTAL/UNIT_COMPLETE well-defined |
| P0 Stabilization | 10% | 8/10 | 8.0 | Hard-stops for span_m, autoportancia, pricing |
| KB Coverage (Production Files) | 15% | 8/10 | 12.0 | Rich production data, 6 systems, 96 products |
| KB Structure (New Dirs) | 10% | 3/10 | 3.0 | Placeholder only, migration pending |
| BOM Rules Quality | 10% | 8/10 | 8.0 | Complete parametric formulas in bom_rules.json |
| Calculation Engine | 10% | 9/10 | 9.0 | Deterministic, Decimal, thread-safe |
| Infrastructure | 10% | 7/10 | 7.0 | Docker, CI/CD, Terraform, but kb_self_learning broken |
| Test Coverage | 5% | 4/10 | 2.0 | YAML specs exist but no runner; MCP tests good |
| Output Schema | 5% | 6/10 | 3.0 | Schema defined but not wired to pipeline |
| Traceability | 5% | 4/10 | 2.0 | Schema supports it, engine doesn't emit it |
| Security | 5% | 5/10 | 2.5 | API keys exist, but path traversal + kb_self_learning gaps |
| **TOTAL** | **100%** | | **70.0** | |

### Score Breakdown

- **Strong (8-9)**: Orchestration, calculation engine, production KB, BOM rules
- **Adequate (6-7)**: Infrastructure, P0 stabilization, output schema
- **Weak (3-5)**: New structured dirs, test coverage, traceability, security
- **Delta from previous estimate (62)**: +8 points from structured directory creation and schema definition

---

## 10. Migration Gap Analysis

### What Exists in Production (Root) but NOT in New Structure

| Data | Production Source | Target | Status |
|------|-------------------|--------|--------|
| 96 real products | `bromyros_pricing_*.json` | `kb/catalog.csv` | Not migrated |
| Real USD pricing | `bromyros_pricing_*.json` | `kb/pricing.csv` | Not migrated |
| 70+ accessories | `accessories_catalog.json` | `kb/accessories_map.json` | Not migrated |
| 12+ autoportancia rows | `bom_rules.json` → `autoportancia` | `kb/autoportancia.csv` | Not migrated |
| 6 system formulas | `bom_rules.json` → `sistemas` | `rules/bom_rules_*.json` | Not migrated |
| Fixation kit details | `bom_rules.json` → `kits_fijacion` | `rules/` | Not migrated |
| Standard lengths | `bom_rules.json` → `largos_std` | `rules/` | Not migrated |

### Migration Priority

1. **Autoportancia table** → `kb/autoportancia.csv` (P0: blocks HORIZONTAL validation)
2. **Pricing with correct currency/IVA** → `kb/pricing.csv` (P0: wrong defaults)
3. **Real SKU catalog** → `kb/catalog.csv` (P0: enables product identity)
4. **Accessories mapping** → `kb/accessories_map.json` (P0: enables exact match)
5. **System-specific BOM rules** → `rules/bom_rules_*.json` (P1: currently generic)
6. **Test runner** → Python script to execute YAML tests (P1: enables CI)

---

## 11. Prioritized Backlog

### P0 — Bloqueante (Do First)

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 1 | Fix `kb/pricing.csv` currency to USD and IVA to 0.22 | S | Prevents wrong quotes |
| 2 | Migrate autoportancia table from `bom_rules.json` to `kb/autoportancia.csv` | M | Enables HORIZONTAL validation |
| 3 | Populate `kb/catalog.csv` with real SKUs from `accessories_catalog.json` + `bromyros_pricing` | L | Single source of truth for products |
| 4 | Populate `kb/pricing.csv` with real prices from `bromyros_pricing_master.json` | L | Enables pricing in new structure |
| 5 | Populate `kb/accessories_map.json` with real mappings from `accessories_catalog.json` | M | Enables accessory selection |
| 6 | Fix `kb_self_learning/` — register routers, add persistence, add auth | L | Module currently non-functional |

### P1 — Robustez (Next Sprint)

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 7 | Expand `rules/bom_rules_*.json` to cover all 6 systems with real formulas | L | Full BOM coverage |
| 8 | Build test runner (`tests/run_tests.py`) to execute YAML test cases | M | Automated regression |
| 9 | Wire `quote_output.schema.json` to validation in calculation pipeline | M | Output contract enforcement |
| 10 | Add traceability (`rule_id → line_item`) to calculator output | M | Debugging, audit |
| 11 | Clean `corrections_log.json` — remove test entries, apply pending | S | Clean audit trail |
| 12 | Add dimensional validations to `validations_vertical.json` | S | Robustness |

### P2 — Producto (Future)

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 13 | Integrate PDF template with `quote_output.schema.json` | M | Consistent outputs |
| 14 | Multi-currency support (USD + ARS with exchange rate) | M | Regional expansion |
| 15 | Example library by system (complete worked examples) | M | Documentation |
| 16 | Price versioning with effective date enforcement | M | Historical accuracy |

---

## 12. Test Coverage Report

### Existing Test Infrastructure

| Test Suite | Location | Runner | Status |
|------------|----------|--------|--------|
| MCP Handler Tests | `test_mcp_handlers_v1.py` | pytest | Active, CI-integrated |
| MCP Integration Tests | `mcp/tests/` | pytest | Active |
| Wolf API Tests | `wolf_api/tests/` | pytest | Active |
| Backend Tests | `backend/tests/` | pytest | Active |
| EVOLUCIONADOR Tests | `.evolucionador/tests/` | pytest | Active |
| **YAML Scenario Tests** | `tests/*.yaml` | **None** | Spec-only, no runner |
| Background Task Tests | `background_tasks/tests/` | pytest | Active |
| OpenAI Ecosystem Tests | `openai_ecosystem/test_client.py` | pytest | Active |

### YAML Test Scenarios (7 cases)

| Test | Covers | Hard-Stop Expected |
|------|--------|--------------------|
| `test_vertical_basic` | Standard VERTICAL with all inputs | None |
| `test_horizontal_span_missing` | Missing span_m | "Falta dato crítico: luz (span_m)" |
| `test_horizontal_autoportancia_missing` | No autoportancia match | "Falta información de autoportancia..." |
| `test_horizontal_span_ok` | Valid HORIZONTAL | None |
| `test_unit_complete_subtotals` | UNIT_COMPLETE | None (separate subtotals) |
| `test_accessory_ambiguity` | Ambiguous term "esquinero" | Must list options |
| `test_missing_price` | No pricing data available | "No tengo esa información..." |

### Coverage Gaps

- No integration tests for end-to-end quote generation with new structure
- No validation tests for schema compliance of calculator output
- No performance/load tests
- No test for currency/IVA calculation correctness

---

## 13. Security Review

### Findings

| Severity | Component | Issue | Recommendation |
|----------|-----------|-------|----------------|
| High | `kb_self_learning/` | No authentication on write endpoints | Add API key / JWT auth |
| High | `kb_self_learning/` | In-memory state — no persistence | Implement database storage |
| Medium | `quotation_calculator_v3.py` | File paths from user input without sanitization | Add path validation |
| Medium | Multiple scripts | `eval` / command substitution without validation | Use parameterized commands |
| Medium | MCP `write_file` handler | Password-protected but path traversal possible | Restrict to allowed directories |
| Low | `requirements.txt` | No pinned versions for some deps | Pin all versions |
| Low | Docker | No non-root user in some Dockerfiles | Add USER directive |

### Positive Security Practices

- Wolf API uses constant-time comparison for API keys
- KB write operations require explicit password
- Terraform manages secrets via Google Secret Manager
- CI/CD validates JSON integrity before deployment

---

## 14. Recommendations

### Immediate (This Sprint)

1. **Fix currency/IVA in `kb/pricing.csv`** — Change to USD and 0.22 to match production
2. **Write a migration script** — Extract data from root JSON files into the new `kb/`/`rules/` structure
3. **Build a YAML test runner** — Simple Python script that loads YAML, runs against calculator, validates expectations
4. **Document the dual-structure period** — Clearly mark which files are authoritative (root = production, kb/ = target)

### Short-Term (Next 2 Sprints)

5. **Complete data migration** to new structure
6. **Fix `kb_self_learning` module** or remove it from deployment
7. **Add traceability** to calculator output
8. **Wire schema validation** into the quote output pipeline

### Medium-Term (Quarter)

9. **Deprecate root-level data files** once migration is complete
10. **Implement multi-currency** support
11. **Add price versioning** with effective date enforcement
12. **Build example library** with worked cases per system

---

## Appendix A: Hard-Stop Messages (Normalized)

These are the exact hard-stop messages the system must produce:

| Condition | Message |
|-----------|---------|
| Missing span_m for HORIZONTAL | `"Falta dato crítico: luz (span_m)"` |
| No autoportancia match | `"Falta información de autoportancia para este caso. No se emite cotización formal sin verificación"` |
| Price not in KB | `"No tengo esa información en mi base de conocimiento"` |

## Appendix B: Construction Systems Supported

| System ID | Type | Product | Notes |
|-----------|------|---------|-------|
| `techo_isodec_eps` | HORIZONTAL | ISODEC EPS | Heavy roof, varilla fixation |
| `techo_isodec_pir` | HORIZONTAL | ISODEC PIR | Heavy roof, higher thermal |
| `techo_isoroof_3g` | HORIZONTAL | ISOROOF 3G | Light roof, self-tapping |
| `pared_isopanel_eps` | VERTICAL | ISOPANEL EPS | Wall panel, standard |
| `pared_isowall_pir` | VERTICAL | ISOWALL PIR | Wall panel, higher thermal |
| `pared_isofrig_pir` | VERTICAL | ISOFRIG PIR | Cold chamber, max thermal |

## Appendix C: File Lineage

```
Production (Active)                    Target (Placeholder)
─────────────────                      ────────────────────
bom_rules.json ──────────────────────→ rules/bom_rules_vertical.json
                                       rules/bom_rules_horizontal.json

accessories_catalog.json ────────────→ kb/catalog.csv
                                       kb/accessories_map.json

bromyros_pricing_master.json ────────→ kb/pricing.csv

bom_rules.json → autoportancia ──────→ kb/autoportancia.csv

(new) ───────────────────────────────→ schemas/quote_output.schema.json
(new) ───────────────────────────────→ tests/*.yaml
(new) ───────────────────────────────→ docs/kb_contract.md
(new) ───────────────────────────────→ docs/units_and_rounding.md
```

---

*End of Final Review — GPT-PANELIN-V3.3*
