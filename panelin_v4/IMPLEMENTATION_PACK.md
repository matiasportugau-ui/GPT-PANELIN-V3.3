# PANELIN v4.0 — FULL IMPLEMENTATION PACK

**Version:** 4.0.0
**Date:** 2026-02-25
**Status:** All tests passing, production-ready for integration
**Branch:** `cursor/panelin-4-0-architecture-85ce`

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [File Inventory](#3-file-inventory)
4. [Module Specifications](#4-module-specifications)
5. [Data Model](#5-data-model)
6. [SRE Algorithm (Full Specification)](#6-sre-algorithm)
7. [SAI Scoring System](#7-sai-scoring-system)
8. [Integration Guide](#8-integration-guide)
9. [Test Results](#9-test-results)
10. [GPT Prompt (PROMPT_CORE_V4)](#10-gpt-prompt)
11. [Quick Start](#11-quick-start)
12. [Known Limitations & Roadmap](#12-roadmap)

---

## 1. EXECUTIVE SUMMARY

Panelin v4.0 is an **Autonomous Technical-Commercial Quotation Engine** that replaces
the rigid blocking behavior of v3.3 with intelligent risk-based classification.

### What changed from v3.3 to v4.0

| Aspect | v3.3 | v4.0 |
|--------|------|------|
| Missing span (luz) | **BLOCKS** quotation | Classifies risk, uses documented defaults |
| Operating modes | Single (formal) | **3 levels**: informativo / pre_cotizacion / formal |
| Validation | Coupled to calculation | **Separate engine**, non-blocking in pre mode |
| Quality metrics | None | **SAI score** (0-100) per quotation |
| Testing | Manual | **34 automated** + 19 regression + 30 stress |
| Batch processing | Not supported | **Built-in** batch with 49 real-world cases |
| Blocking rate | ~44% (from original test run) | **0%** in pre_cotizacion mode |
| Processing speed | ~100ms | **< 0.4ms** per quotation |
| Accessories matching | First match | **Priority chain**: family > thickness > UNIVERSAL |

### Final Test Metrics

| Metric | Value |
|--------|-------|
| pytest unit tests | **34/34** (100%) |
| Regression suite | **19/19** (100%) |
| Stress test (30 mixed) | 0 errors, 0% blocking |
| Real-world batch (49 quotes) | **$138,772** total quoted, 0% blocking |
| SAI average | **87.9** |
| SAI pass rate (≥80) | **81.6%** |
| Avg processing time | **0.38ms** per quotation |

---

## 2. ARCHITECTURE OVERVIEW

```
INPUT TEXT (free-form Spanish)
    ↓
┌──────────────────────┐
│  1. CLASSIFIER       │  Detects type (roof/wall/accessories/update)
│                      │  Determines mode (informativo/pre/formal)
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│  2. PARSER           │  Converts text → structured QuoteRequest
│                      │  NEVER raises. Tags incomplete fields.
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│  3. SRE ENGINE       │  Calculates Structural Risk Score (0-100)
│                      │  Determines quotation level (1/2/3/block)
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│  4. BOM ENGINE       │  Generates Bill of Materials
│                      │  Family-aware accessory matching
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│  5. PRICING ENGINE   │  Values items from KB exclusively
│                      │  NEVER invents prices
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│  6. VALIDATION       │  Multi-layer checks (A/B/C/D)
│                      │  Non-blocking in pre mode
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│  7. SAI SCORER       │  Quality index (0-100)
└──────────┬───────────┘
           ↓
    OUTPUT JSON (QuotationOutput)
```

### Operating Modes

| Mode | Blocks? | When |
|------|---------|------|
| `informativo` | Never | Quick info requests |
| `pre_cotizacion` | **Never** | Internal runs, batch, ML/WA queries |
| `formal` | If CRITICAL | PDF emission, contractual JSON |

### SRE Quotation Levels

| SRE Score | Level | Name | Behavior |
|-----------|-------|------|----------|
| 0-30 | 3 | Formal Certified | Full validation, PDF/JSON ready |
| 31-60 | 2 | Technical Conditioned | Valid with structural warnings |
| 61-85 | 1 | Commercial Quick | Pre-quote with documented defaults |
| 86+ | Block | Technical Block | Requires engineering review |

---

## 3. FILE INVENTORY

```
panelin_v4/                         (3,500 lines total)
├── __init__.py                     Package definition (v4.0.0)
├── ARCHITECTURE.md                 Technical architecture doc
├── PROMPT_CORE_V4.md               Complete GPT prompt with SRE
├── IMPLEMENTATION_PACK.md          This document
├── run_batch_test.py               49 real-world quotation batch runner
│
├── data/
│   └── default_assumptions.json    Configurable defaults for missing data
│
├── engine/                         Core pipeline (2,212 lines)
│   ├── __init__.py
│   ├── classifier.py       (238)   Request type & mode classifier
│   ├── parser.py            (362)   Text → QuoteRequest parser
│   ├── sre_engine.py        (293)   Structural Risk Engine
│   ├── bom_engine.py        (528)   Bill of Materials generator
│   ├── pricing_engine.py    (243)   KB-only pricing
│   ├── validation_engine.py (207)   Multi-layer validation
│   └── quotation_engine.py  (338)   Pipeline orchestrator
│
├── evaluator/                      QA system (819 lines)
│   ├── __init__.py
│   ├── sai_engine.py        (224)   System Accuracy Index calculator
│   ├── regression_suite.py  (420)   19 expert test cases
│   └── stress_test_runner.py(175)   30-request stress test
│
└── tests/                          pytest suite (257 lines)
    ├── __init__.py
    └── test_engine.py       (257)   34 test cases (6 test classes)
```

### KB Dependencies (read-only)

| File | Location | Purpose |
|------|----------|---------|
| `bom_rules.json` | `/workspace/` | BOM parametric rules + autoportancia tables |
| `accessories_catalog.json` | `/workspace/` | 70+ accessories with real prices (IVA inc.) |
| `bromyros_pricing_master.json` | `/workspace/` | Panel pricing by family/thickness |
| `default_assumptions.json` | `panelin_v4/data/` | Configurable defaults |

---

## 4. MODULE SPECIFICATIONS

### 4.1 Classifier (`engine/classifier.py`)

**Purpose:** First pipeline stage. Classifies request text into type + mode.

**API:**
```python
from panelin_v4.engine.classifier import classify_request, OperatingMode

result = classify_request(
    text="Isodec 100 mm / 6 paneles de 6.5 mts / techo completo",
    force_mode=None  # or OperatingMode.FORMAL
)

result.request_type   # RequestType.ROOF_SYSTEM
result.operating_mode # OperatingMode.PRE_COTIZACION
result.has_roof       # True
result.confidence     # 0.85
result.signals        # ["roof_keywords=3", "roof_system_detected", ...]
```

**Request Types:** `roof_system`, `wall_system`, `room_complete`, `accessories_only`,
`update`, `waterproofing`, `conventional_sheet`, `post_sale`, `info_only`, `mixed`

**Keyword Banks:** 7 keyword lists (roof, wall, accessory, update, waterproofing,
sheet, post-sale) with confidence scoring.

### 4.2 Parser (`engine/parser.py`)

**Purpose:** Converts free-form Spanish text to canonical `QuoteRequest` object.

**Key Design:** NEVER raises exceptions. Missing data is tagged in `incomplete_fields`.

**API:**
```python
from panelin_v4.engine.parser import parse_request

req = parse_request("Isodec EPS 100 mm / 6 paneles de 6,5 mts / techo completo a H°")

req.familia          # "ISODEC"
req.sub_familia      # "EPS"
req.thickness_mm     # 100
req.uso              # "techo"
req.structure_type   # "hormigon"
req.geometry.panel_lengths  # [6.5, 6.5, 6.5, 6.5, 6.5, 6.5]
req.geometry.panel_count    # 6
req.incomplete_fields       # ["span_m"]
```

**Detection Capabilities:**
- Product families: ISODEC, ISOROOF, ISOPANEL, ISOWALL, ISOFRIG, HIANSA
- Thickness: mm, cm (auto-converts), "de espesor"
- Panel specs: `6 p. de 6,5 mts`, `3 paneles de 2,30 m + 1 panel de 3,05 m`
- Dimensions: `7 x 10`, `5 m largo x 11 m ancho`
- Structure: H°, hormigón, metal, madera
- Roof type: 1/2/4 aguas, mariposa
- Phone numbers (Uruguayan format), shipping, accessories, height

### 4.3 SRE Engine (`engine/sre_engine.py`)

**Purpose:** Calculates Structural Risk Score (0-100). Core v4.0 innovation.

**API:**
```python
from panelin_v4.engine.sre_engine import calculate_sre

sre = calculate_sre(req)
sre.score              # 45
sre.level              # QuotationLevel.LEVEL_2_CONDITIONED
sre.r_datos            # 40
sre.r_autoportancia    # 0
sre.r_geometria        # 5
sre.r_sistema          # 0
sre.recommendations    # ["Provide span for structural validation."]
sre.alternative_thicknesses  # [150, 200] (when span exceeds capacity)
```

**Formula:** `SRE = R_datos + R_autoportancia + R_geometria + R_sistema`

See [Section 6](#6-sre-algorithm) for the complete specification.

### 4.4 BOM Engine (`engine/bom_engine.py`)

**Purpose:** Generates Bill of Materials using `bom_rules.json` parametric rules.

**API:**
```python
from panelin_v4.engine.bom_engine import calculate_bom

bom = calculate_bom(
    familia="ISODEC", sub_familia="EPS", thickness_mm=100,
    uso="techo", length_m=5.0, width_m=11.0,
    structure_type="metal", roof_type="2_aguas"
)

bom.panel_count         # 10
bom.area_m2             # 55.0
bom.supports_per_panel  # 2
bom.fixation_points     # 44
bom.items               # [BOMItem(tipo="panel", ...), BOMItem(tipo="gotero_frontal", ...), ...]
```

**Accessory Matching Priority:**
1. Exact family match (e.g., gotero for ISODEC)
2. Exact thickness match
3. Sub-family compatible
4. UNIVERSAL fallback

**Supports:** 6 construction systems, 3 structure types, 4 roof geometries.

**Items generated for roof:** panel, gotero_frontal, gotero_lateral, cumbrera (if 2+ aguas),
varilla, tuerca, arandela_carrocero, tortuga_pvc, taco (if hormigon), silicona,
cinta_butilo, fijacion_perfileria.

**Items generated for wall:** panel, perfil_u, varilla, tuerca, arandela_carrocero,
tortuga_pvc, taco (if hormigon), silicona, cinta_butilo.

### 4.5 Pricing Engine (`engine/pricing_engine.py`)

**Purpose:** Values BOM items from KB files exclusively.

**API:**
```python
from panelin_v4.engine.pricing_engine import calculate_pricing

pricing = calculate_pricing(bom, "ISODEC", "EPS", 100)

pricing.subtotal_panels_usd      # 2533.85
pricing.subtotal_accessories_usd # 383.25
pricing.subtotal_total_usd       # 2917.10
pricing.missing_prices           # [] or ["taco (SKU: None): price not found"]
pricing.items                    # [PricedItem(...), ...]
```

**Inviolable Rules:**
- Prices ONLY from `accessories_catalog.json` and `bromyros_pricing_master.json`
- All prices include IVA 22% -- NEVER add IVA on top
- NEVER calculate price as cost x margin
- If price not found: explicit entry in `missing_prices`, never invents

### 4.6 Validation Engine (`engine/validation_engine.py`)

**Purpose:** Multi-layer validation. Non-blocking in pre_cotizacion mode.

**API:**
```python
from panelin_v4.engine.validation_engine import validate_quotation

validation = validate_quotation(request, sre, bom, pricing, mode)

validation.is_valid            # True
validation.can_emit_formal     # False (only True in formal mode with 0 criticals)
validation.autoportancia_status # "not_verified" | "validated" | "exceeded" | ...
validation.critical_count      # 0
validation.warning_count       # 2
validation.issues              # [ValidationIssue(...), ...]
```

**Validation Layers:**

| Layer | Code | Checks |
|-------|------|--------|
| A - Integrity | A001-A003 | Family identified, thickness specified, prices found |
| B - Technical | B001-B004 | Span for roof, autoportancia limits, BOM completeness |
| C - Commercial | C001-C002 | Location for shipping, accessories for roof |
| D - Mathematical | D001-D002 | Total > 0, subtotals consistent |

**Key Behavior:** In `pre_cotizacion` mode, CRITICAL issues from layers A/B/C are
**downgraded to WARNING**. Only layer D (math errors) stays CRITICAL. This ensures
pre-quotations NEVER block.

### 4.7 Quotation Orchestrator (`engine/quotation_engine.py`)

**Purpose:** Coordinates all engines. Main entry point.

**API:**
```python
from panelin_v4.engine.quotation_engine import process_quotation, process_batch
from panelin_v4.engine.classifier import OperatingMode

# Single quotation
output = process_quotation(
    text="Isodec 100 mm / 6 paneles de 6.5 mts / techo completo a metal + flete",
    force_mode=OperatingMode.PRE_COTIZACION,
    client_name="Test Client",
    client_location="Montevideo"
)

output.quote_id          # "PV4-20260225-A1B2C3D4"
output.mode              # "pre_cotizacion"
output.level             # "formal_certified"
output.status            # "draft" | "validated" | "requires_review" | "blocked"
output.confidence_score  # 88.0
output.assumptions_used  # ["span_m assumed 1.5m (residential default)"]
output.to_json()         # Full JSON output

# Batch processing
outputs = process_batch([
    {"text": "Isodec 100 mm / 6 paneles...", "client_name": "Client 1"},
    {"text": "Isopanel 50 mm / 13 paneles...", "client_name": "Client 2"},
], force_mode=OperatingMode.PRE_COTIZACION)
```

**Default Assumptions (pre mode only):**

| Parameter | Default | Condition |
|-----------|---------|-----------|
| `span_m` | 1.5m | Roof without span |
| `structure_type` | metal (techo/pared), hormigon (camara) | Not specified |
| `width_m` | panel_count x ancho_util | When only panel count given |

Every assumption is recorded in `output.assumptions_used` for audit trail.

---

## 5. DATA MODEL

### QuotationOutput (top-level)

```json
{
  "quote_id": "PV4-20260225-A1B2C3D4",
  "timestamp": "2026-02-25T14:30:00",
  "mode": "pre_cotizacion",
  "level": "formal_certified",
  "status": "draft",
  "confidence_score": 88.0,
  "assumptions_used": ["span_m assumed 1.5m"],
  "processing_notes": [],

  "classification": {
    "request_type": "roof_system",
    "operating_mode": "pre_cotizacion",
    "has_roof": true, "has_wall": false,
    "has_accessories": true, "is_update": false,
    "confidence": 0.85
  },

  "request": {
    "familia": "ISODEC", "sub_familia": "EPS",
    "thickness_mm": 100, "uso": "techo",
    "structure_type": "metal", "span_m": 1.5,
    "geometry": { "length_m": 6.5, "panel_count": 6 },
    "incomplete_fields": []
  },

  "sre": {
    "score": 5, "level": "formal_certified",
    "r_datos": 0, "r_autoportancia": 0,
    "r_geometria": 0, "r_sistema": 5
  },

  "bom": {
    "system_key": "techo_isodec_eps",
    "area_m2": 43.68, "panel_count": 6,
    "supports_per_panel": 2, "fixation_points": 30,
    "items": [
      {"tipo": "panel", "quantity": 6, "unit": "unid"},
      {"tipo": "gotero_frontal", "sku": "GF100", "quantity": 3},
      ...
    ]
  },

  "pricing": {
    "subtotal_panels_usd": 2011.09,
    "subtotal_accessories_usd": 350.42,
    "subtotal_total_usd": 2361.51,
    "iva_mode": "incluido",
    "missing_prices": []
  },

  "validation": {
    "is_valid": true, "can_emit_formal": false,
    "autoportancia_status": "not_verified",
    "critical_count": 0, "warning_count": 1
  }
}
```

---

## 6. SRE ALGORITHM

### Formula

```
SRE = R_datos + R_autoportancia + R_geometria + R_sistema
```

### R_datos (0-40, capped)

| Condition | Points |
|-----------|--------|
| Span missing for roof | +40 |
| Thickness missing | +25 |
| Structure type missing | +15 |
| Dimensions incomplete | +20 |
| "Ver plano" / "aguardo planta" without measurements | +25 |

**Capped at 40.** Even if all conditions true, R_datos never exceeds 40.

### R_autoportancia (0-50)

Only calculated when span_m, familia, and thickness_mm are all present.

```
ratio = span_m / luz_max_m
```

| Ratio | Points | Meaning |
|-------|--------|---------|
| ≤ 0.60 | 0 | Safe zone |
| 0.61 - 0.75 | 10 | Low risk |
| 0.76 - 0.85 | 20 | Moderate risk |
| 0.86 - 1.00 | 30 | Near limit |
| > 1.00 | **50** | **EXCEEDS** capacity |

When ratio > 1.0, the engine searches for alternative thicknesses that satisfy
the span and includes them in `alternative_thicknesses`.

### Autoportancia Reference Table (from `bom_rules.json`)

| Family | Thickness | Max Span (luz_max_m) |
|--------|-----------|---------------------|
| ISODEC EPS | 100mm | 5.5m |
| ISODEC EPS | 150mm | 7.5m |
| ISODEC EPS | 200mm | 9.1m |
| ISODEC EPS | 250mm | 10.4m |
| ISODEC PIR | 50mm | 3.5m |
| ISODEC PIR | 80mm | 5.5m |
| ISODEC PIR | 120mm | 7.6m |
| ISOROOF 3G | 30mm | 2.8m |
| ISOROOF 3G | 50mm | 3.3m |
| ISOROOF 3G | 80mm | 4.0m |
| ISOPANEL EPS | 50mm | 3.0m |
| ISOPANEL EPS | 100mm | 5.5m |
| ISOPANEL EPS | 150mm | 7.5m |
| ISOPANEL EPS | 200mm | 9.1m |

### R_geometria (0-15)

| Condition | Points |
|-----------|--------|
| 2 aguas roof | +5 |
| 4 aguas roof | +8 |
| Mariposa roof | +10 |
| Panel length > 12m | +10 |
| Central union detected | +5 |

### R_sistema (0-15)

| System | Points |
|--------|--------|
| Wall (pared) | 0 |
| ISODEC EPS techo | +5 |
| ISODEC PIR techo | +8 |
| ISOROOF techo | +10 |
| Thickness ≤ 50mm | +5 (additional) |

---

## 7. SAI SCORING SYSTEM

### Formula

Base: 100 points. Penalties subtract, bonuses add. Clamped to [0, 100].

### Penalties

| Code | Points | Trigger |
|------|--------|---------|
| P1 | -30 | Autoportancia exceeded without alternative suggested |
| P1a | -10 | Autoportancia exceeded but alternative provided |
| P2 | -25 | Mathematical inconsistency (subtotals don't add up) |
| P3 | -10 to -20 | Missing prices from KB |
| P4 | -5 to -15 | BOM warnings |
| P5 | -15 to -30 | Critical validation issues |
| P6 | -10 | Unnecessary blocking in pre_cotizacion mode |
| P7 | -5 | Assumptions used but not properly declared |
| P8 | -15 | Zero panels despite valid request data |

### Bonuses

| Code | Points | Trigger |
|------|--------|---------|
| B1 | +5 | Alternative thickness suggested when needed |
| B2 | +2 | Complete client data (name + phone + location) |
| B3 | +3 | Very low structural risk (SRE ≤ 15) |

### Grade Scale

| Grade | Score Range |
|-------|------------|
| A | 95-100 |
| B | 85-94 |
| C | 70-84 |
| D | 60-69 |
| F | < 60 |

### Targets by Mode

| Mode | Minimum SAI |
|------|------------|
| formal | ≥ 95 |
| pre_cotizacion | ≥ 80 |
| informativo | ≥ 60 |

---

## 8. INTEGRATION GUIDE

### With existing MCP Server

The engine can be wrapped as MCP tool handlers:

```python
async def handle_v4_quotation(arguments: dict) -> dict:
    from panelin_v4.engine.quotation_engine import process_quotation
    output = process_quotation(
        text=arguments["text"],
        client_name=arguments.get("client_name"),
    )
    return output.to_dict()
```

### With PDF Generator

```python
from panelin_v4.engine.quotation_engine import process_quotation
from panelin_reports.pdf_generator import generate_quotation_pdf

output = process_quotation(text)
# output.pricing.items has the line items for PDF
# output.bom.items has the BOM for PDF
# output.validation.autoportancia_status for structural notes
```

### With GPT Instructions

The `PROMPT_CORE_V4.md` file contains the complete prompt that teaches the GPT
about the 3-level system, SRE scoring, and non-blocking behavior. Add it to
the GPT instructions or use it as a reference for the system prompt.

### With Wolf API

```python
# After quotation, persist to KB
output = process_quotation(text, client_name="Client")
# output.to_json() can be saved via Wolf API POST /kb/conversations
```

---

## 9. TEST RESULTS

### pytest (34/34 passing)

| Class | Tests | Status |
|-------|-------|--------|
| TestClassifier | 6 | ALL PASS |
| TestParser | 11 | ALL PASS |
| TestSRE | 5 | ALL PASS |
| TestBOM | 4 | ALL PASS |
| TestOrchestrator | 4 | ALL PASS |
| TestSAI | 2 | ALL PASS |
| TestRegressionSuite | 2 | ALL PASS |

### Regression Suite (19/19 passing)

| ID | Category | Description | SAI |
|----|----------|-------------|-----|
| S01 | structural | ISODEC 100mm within capacity | 93 |
| S02 | structural | Missing span, should NOT block | 93 |
| S03 | structural | ISOROOF 30mm exceeds capacity | 73 |
| S04 | structural | Formal mode blocks missing span | 75 |
| B01 | bom | Complete roof BOM 11x5m | 93 |
| B02 | bom | Wall BOM ISOPANEL | 93 |
| B03 | bom | Cumbrera for 2 aguas | 93 |
| P01 | pricing | Positive total for valid request | 93 |
| P02 | pricing | Accessories-only pricing | 85 |
| C01 | commercial | Pre-quote NEVER blocks for span | 93 |
| C02 | commercial | Update request detection | 73 |
| C03 | commercial | Wall needs no span validation | 93 |
| M01 | stress | Mixed wall + roof | 93 |
| M02 | stress | Incomplete (only product) | 73 |
| M03 | stress | Canalon accessories-only | 85 |
| R01 | real_world | Yoana - Isodec 150mm | 93 |
| R02 | real_world | Andres - Isopanel 50mm | 93 |
| R03 | real_world | Mauricio - Isodec 200mm | 93 |
| R04 | real_world | Cristian - Room 4.50x8.50 | 93 |

### Stress Test (30/30)

| Metric | Value |
|--------|-------|
| Processed | 30/30 |
| Blocked | 0 (0.0%) |
| Errors | 0 |
| Avg SAI | 84.5 |
| Min SAI | 70.0 |
| Max SAI | 93.0 |
| Avg Time | 0.17ms |

### Real-World Batch (49 quotations from 2026-02-24)

| Metric | Value |
|--------|-------|
| Total processed | 49/49 |
| Blocked | **0** (0.0%) |
| Total quoted | **$138,772.86** |
| SAI average | 87.9 |
| Formal certified | 41 (83.7%) |
| Technical conditioned | 8 (16.3%) |
| Grade B | 40 |
| Grade C | 7 |
| Grade D | 2 |

---

## 10. GPT PROMPT

The complete GPT prompt is in `panelin_v4/PROMPT_CORE_V4.md`.

Key blocks:
- **Block 1:** Identity (Panelin BMC Assistant Pro v4.0)
- **Block 2:** Auto-classifier (9 request types)
- **Block 3:** SRE calculation (4 components)
- **Block 4:** Level decision (0-30/31-60/61-85/86+)
- **Block 5:** P0 compatibility (formal only)
- **Block 6:** Response format per level
- **Block 7:** Delta flow for updates
- **Block 8:** Configurable defaults
- **Block 9:** Inviolable rules (IVA, KB-only prices, etc.)
- **Block 10:** SAI internal scoring
- **Block 11:** Tone per level
- **Block 12:** Development and audit integration

---

## 11. QUICK START

### Run Tests
```bash
cd /workspace
PYTHONPATH=/workspace python3 -m pytest panelin_v4/tests/test_engine.py -v
```

### Run Regression + Stress
```bash
cd /workspace
PYTHONPATH=/workspace python3 panelin_v4/run_batch_test.py
```

### Single Quotation
```python
import sys; sys.path.insert(0, "/workspace")
from panelin_v4.engine.quotation_engine import process_quotation

output = process_quotation(
    "Isodec 100 mm / 6 paneles de 6.5 mts / techo completo a metal + flete",
    client_name="Juan",
    client_location="Montevideo"
)

print(output.to_json())
```

### Batch Processing
```python
from panelin_v4.engine.quotation_engine import process_batch
from panelin_v4.engine.classifier import OperatingMode

results = process_batch([
    {"text": "Isodec 100 mm / 6 paneles de 5 mts"},
    {"text": "Isopanel 50 mm / 13 paneles de 2.60 mts"},
    {"text": "12 Goteros Frontales 100 mm + 8 Laterales"},
], force_mode=OperatingMode.PRE_COTIZACION)

for r in results:
    print(f"{r.quote_id}: {r.status} | ${r.pricing.get('subtotal_total_usd', 0)}")
```

### SAI Evaluation
```python
from panelin_v4.evaluator.sai_engine import calculate_sai, calculate_batch_sai

sai = calculate_sai(output)
print(f"SAI: {sai.score} ({sai.grade}) - {'PASS' if sai.passed else 'FAIL'}")

# Batch SAI
summary = calculate_batch_sai(results)
print(f"Average SAI: {summary['average']}, Pass rate: {summary['pass_rate']}%")
```

---

## 12. KNOWN LIMITATIONS & ROADMAP

### Current Limitations

1. **HIANSA panels** not in KB pricing -- classified but can't be priced
2. **Waterproofing products** (HM-Rubber) classified but not quotable
3. **BC-30 conventional sheets** classified but outside panel KB
4. **Dimension ambiguity**: `5 m largo x 11 m ancho` - width vs length depends
   on context (parser treats first value as width, second as length)
5. **Multi-option requests** (e.g., "3 options: 150, 200, 250mm") parsed as
   single thickness (first match) -- multi-variant support is future work
6. **Panel pricing** depends on `bromyros_pricing_master.json` data structure;
   if format changes, `_find_panel_price_m2` needs updating

### Roadmap

**P0 - Immediate:**
- Integrate as MCP tool handler for production use
- Connect to PDF generator for formal quotation output

**P1 - Short term:**
- Multi-variant quotation (generate 2-3 options automatically)
- OCR/plano integration (extract dimensions from images)
- WhatsApp template auto-generation for missing data

**P2 - Medium term:**
- Historical quotation comparison engine
- Automatic optimization suggestions (waste reduction)
- CRM integration for client data persistence

**P3 - Long term:**
- Self-learning from human corrections
- Predictive pricing anomaly detection
- Multi-project bundle optimization

---

*Generated: 2026-02-25 | Panelin v4.0.0 | Branch: cursor/panelin-4-0-architecture-85ce*
