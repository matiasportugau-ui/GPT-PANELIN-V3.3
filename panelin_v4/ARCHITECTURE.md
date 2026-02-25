# Panelin v4.0 - Architecture Documentation

## Vision

Panelin v4.0 is an **Autonomous Technical-Commercial Quotation Engine** for BMC
construction panel systems. It replaces rigid blocking behavior with intelligent
risk classification, enabling the commercial team to move fast while maintaining
structural integrity.

**Design Principles:**
1. **Never block sales unnecessarily** - classify risk, don't prohibit
2. **Separation of concerns** - calculation, validation, and presentation are independent
3. **Deterministic calculations** - all math uses Python, never LLM inference
4. **Explicit assumptions** - every default value is declared in the output
5. **Measurable quality** - every quotation gets a SAI score (0-100)
6. **Evolutionary** - the system detects patterns and improves over time

---

## Architecture Overview

```
INPUT TEXT
    ↓
┌─────────────────┐
│  1. Classifier   │  → Determines request type & operating mode
└────────┬────────┘
         ↓
┌─────────────────┐
│  2. Parser       │  → Converts text to structured QuoteRequest
└────────┬────────┘
         ↓
┌─────────────────┐
│  3. SRE Engine   │  → Calculates Structural Risk Score (0-100)
└────────┬────────┘
         ↓
┌─────────────────┐
│  4. BOM Engine   │  → Generates Bill of Materials
└────────┬────────┘
         ↓
┌─────────────────┐
│  5. Pricing      │  → Values items from KB (never invents)
└────────┬────────┘
         ↓
┌─────────────────┐
│  6. Validation   │  → Multi-layer checks (non-blocking in pre mode)
└────────┬────────┘
         ↓
┌─────────────────┐
│  7. SAI Score    │  → Quality index for the quotation
└────────┬────────┘
         ↓
    OUTPUT JSON
```

---

## Module Details

### 1. Classifier (`engine/classifier.py`)

Classifies requests into types and determines the operating mode.

**Request Types:**
| Type | Description |
|------|-------------|
| `roof_system` | Complete roof installation |
| `wall_system` | Wall/facade panels |
| `room_complete` | Full room (walls + roof) |
| `accessories_only` | Only accessories/profiles |
| `update` | Modify existing quotation |
| `waterproofing` | Waterproofing products |
| `conventional_sheet` | Standard metal sheets |
| `post_sale` | Claims / post-sale |
| `mixed` | Multiple types combined |

**Operating Modes:**
| Mode | Blocks? | Use Case |
|------|---------|----------|
| `informativo` | Never | Quick info, ranges |
| `pre_cotizacion` | Never | Internal run, batch, ML/WA |
| `formal` | If CRITICAL | PDF, JSON contractual |

### 2. Parser (`engine/parser.py`)

Converts free-form Spanish text into a canonical `QuoteRequest` object.
Tolerant to noise, abbreviations, comma decimals, and ambiguity.

**Never raises exceptions.** Missing data is recorded in `incomplete_fields`.

**Detects:**
- Product family (ISODEC, ISOROOF, ISOPANEL, ISOWALL, ISOFRIG, HIANSA)
- Thickness (mm/cm with auto-conversion)
- Panel counts and lengths (`6 p. de 6,5 mts`, `3 paneles de 2,30 m + 1 panel de 3,05 m`)
- Dimensions (`7 x 10`, `5 m largo x 11 m ancho`)
- Structure type (H°, metal, madera)
- Roof type (2 aguas, 4 aguas, mariposa)
- Phone numbers, shipping requests, accessories

### 3. SRE Engine (`engine/sre_engine.py`)

**S**tructural **R**isk **E**ngine - the core innovation of v4.0.

Replaces binary blocking with a risk score:

```
SRE = R_datos + R_autoportancia + R_geometria + R_sistema
```

| Component | Range | What it measures |
|-----------|-------|------------------|
| R_datos | 0-40 | Data completeness (span, thickness, dimensions) |
| R_autoportancia | 0-50 | Structural capacity vs requested span |
| R_geometria | 0-15 | Geometric complexity (4 aguas, mariposa, >12m) |
| R_sistema | 0-15 | System sensitivity (ISOROOF > ISODEC PIR > EPS) |

**Quotation Levels:**
| SRE Score | Level | Action |
|-----------|-------|--------|
| 0-30 | Formal Certified | Full validation, PDF ready |
| 31-60 | Technical Conditioned | Valid with warnings |
| 61-85 | Commercial Quick | Pre-quote with assumptions |
| 86+ | Technical Block | Requires engineering review |

### 4. BOM Engine (`engine/bom_engine.py`)

Generates Bill of Materials using parametric rules from `bom_rules.json`.

**Accessory Selection Priority:**
1. Exact family match (e.g., ISODEC gotero)
2. Exact thickness match
3. Sub-family compatible
4. UNIVERSAL fallback

**Never** uses first-match. Always follows priority chain.

**Supports:**
- 6 construction systems (techo_isodec_eps/pir, techo_isoroof_3g, pared_isopanel_eps, pared_isowall_pir, pared_isofrig_pir)
- Structure-specific fixation (metal vs hormigon vs madera)
- Roof geometry accessories (cumbrera for 2+ aguas)
- System inheritance (PIR inherits from EPS with overrides)

### 5. Pricing Engine (`engine/pricing_engine.py`)

**Rules:**
- Prices come EXCLUSIVELY from `accessories_catalog.json` and `bromyros_pricing_master.json`
- All catalog prices include IVA 22% -- NEVER adds IVA on top
- NEVER calculates price as cost × margin
- If price not found: explicit error in `missing_prices`, never invents
- unit_base: `unidad → qty × price`, `ml → qty × largo × price`, `m² → area × price`

### 6. Validation Engine (`engine/validation_engine.py`)

Multi-layer validation with non-blocking behavior in pre mode.

| Layer | Checks |
|-------|--------|
| A - Integrity | SKU exists, price exists, unit coherent |
| B - Technical | Autoportancia, thickness compatible, BOM warnings |
| C - Commercial | Shipping, fixings completeness |
| D - Mathematical | Subtotal/total consistency |

**Key behavior:**
- In `pre_cotizacion`: CRITICAL issues are downgraded to WARNING (except math errors)
- In `formal`: CRITICAL issues prevent formal emission
- `autoportancia_status`: validated / not_verified / not_applicable / exceeded / near_limit

### 7. Quotation Orchestrator (`engine/quotation_engine.py`)

Coordinates all engines in sequence. Entry points:

```python
# Single quotation
output = process_quotation(text, force_mode=None)

# Batch processing
outputs = process_batch([{"text": "..."}, ...])
```

**Default assumptions** (applied only in non-formal mode):
- `span_m`: 1.5m residential default
- `structure_type`: metal for techo, metal for pared, hormigon for camara
- `width_m`: derived from panel_count × ancho_util when possible

---

## Evaluator System

### SAI Engine (`evaluator/sai_engine.py`)

**S**ystem **A**ccuracy **I**ndex - quality score (0-100) per quotation.

**Penalties:**
| Code | Points | Trigger |
|------|--------|---------|
| P1 | -30 | Autoportancia exceeded without alternative |
| P2 | -25 | Mathematical inconsistency |
| P3 | -10/20 | Missing prices from KB |
| P4 | -5/15 | BOM warnings |
| P5 | -15/30 | Critical validation issues |
| P6 | -10 | Unnecessary blocking in pre mode |
| P7 | -5 | Undeclared assumptions |
| P8 | -15 | Zero panels with valid request |

**Bonuses:**
| Code | Points | Trigger |
|------|--------|---------|
| B1 | +5 | Alternative thickness suggested |
| B2 | +2 | Complete client data |
| B3 | +3 | Very low structural risk |

**Targets:** Formal ≥ 95, Pre ≥ 80, Informativo ≥ 60

### Regression Suite (`evaluator/regression_suite.py`)

19 expert test cases covering:
- **Structural**: autoportancia limits, span validation
- **BOM**: completeness, cumbrera for 2 aguas, tacos for hormigon
- **Pricing**: positive totals, accessories-only
- **Commercial**: non-blocking in pre mode, update detection
- **Real-world**: actual batch quotation requests

### Stress Test Runner (`evaluator/stress_test_runner.py`)

30 mixed requests (40% incomplete, 30% ambiguous, 20% updates, 10% complete).

Measures: processing time, SAI distribution, blocking rate, error rate.

---

## Data Files

### `data/default_assumptions.json`

Configurable defaults for missing data. Every assumption is explicitly declared
in the quotation output for audit trail.

```json
{
  "span_defaults": {"residencial": 1.5, "galpon": 2.0},
  "structure_defaults": {"techo": "metal", "pared": "metal"},
  "sre_thresholds": {"level_3_max": 30, "level_2_max": 60},
  "sai_minimum": {"formal": 95, "pre_cotizacion": 80}
}
```

---

## Key Metrics (Current)

| Metric | Value |
|--------|-------|
| Unit tests | 34/34 passing |
| Regression pass rate | 94.7% (18/19) |
| Stress test blocking rate | 0% |
| Stress test error rate | 0% |
| Average SAI (stress) | 85.6 |
| Processing time | < 0.4ms per quotation |

---

## Comparison: v3.3 vs v4.0

| Aspect | v3.3 | v4.0 |
|--------|------|------|
| Missing span | Blocks | Classifies risk, uses default |
| Validation | Coupled to calculation | Separate engine |
| Modes | Single (formal) | 3 levels (info/pre/formal) |
| Metrics | None | SAI scoring per quotation |
| Testing | Manual | 34 automated + regression + stress |
| Batch processing | Not supported | Built-in |
| Blocking behavior | Binary | Risk-based 4-level |
| Speed | ~100ms | < 0.4ms |

---

## Integration with Existing System

Panelin v4.0 is designed to **complement** the existing architecture:

- **MCP Server**: The engine can be wrapped as MCP tool handlers
- **PDF Generator**: `QuotationOutput.to_dict()` provides structured data for `panelin_reports/pdf_generator.py`
- **GPT Config**: The classifier and SRE can inform the GPT's decision-making
- **Wolf API**: Quotation outputs can be persisted via existing KB write endpoints
- **quotation_calculator_v3.py**: Core math functions are preserved and enhanced

The v4.0 engine adds an intelligent orchestration layer on top of the existing
deterministic calculation engine, rather than replacing it.
