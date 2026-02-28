# DATA CONSISTENCY REPORT — Panelin v6 Knowledge Base
## Cross-Reference Audit | Feb 25, 2026

### Files Analyzed
| # | File | Role |
|---|------|------|
| 1 | `docs/v6/KB_PRECIOS.md` | Canonical price list (PVP & Costo, ex-IVA) |
| 2 | `kb/pricing_v6.csv` | Structured panel pricing |
| 3 | `kb/accessories_pricing_v6.csv` | Structured accessory/fixation pricing |
| 4 | `kb/autoportancia.csv` | Autoportancia/span table |
| 5 | `rules/formulas_v6.json` | Calculation formulas & reference data |
| 6 | `tests/test_real_quotation_COT20250508.yaml` | Real quotation test case |
| 7 | `bom_rules.json` | BOM parametric rules (autoportancia section) |
| 8 | `accessories_catalog.json` | BROMYROS supplier catalog (IVA-inclusive) |

---

## SECTION 1 — Panel Prices: KB_PRECIOS.md vs pricing_v6.csv

**Result: FULLY CONSISTENT — all 30 product rows match exactly.**

Every panel product across all families (ISODEC EPS, ISODEC PIR, ISOROOF 3G,
ISOROOF Plus, ISOROOF Foil, ISOROOF Colonial, ISOPANEL EPS, ISOWALL PIR,
ISOFRIG SL) has identical PVP/m2, Costo/m2, autoportancia, ancho_util, and
waste_factor values between `KB_PRECIOS.md` and `pricing_v6.csv`.

No panel-level price discrepancies found.

---

## SECTION 2 — Autoportancia: Cross-Reference Across 5 Sources

Five files carry autoportancia data. The table below flags every gap and mismatch.

| Product | Thickness | KB_PRECIOS | pricing_v6.csv | autoportancia.csv | bom_rules.json | formulas_v6.json | Status |
|---------|-----------|------------|----------------|-------------------|----------------|------------------|--------|
| ISODEC EPS | 100mm | 5.5 | 5.5 | 5.5 | 5.5 | 5.5 | OK |
| ISODEC EPS | 150mm | 7.5 | 7.5 | 7.5 | 7.5 | 7.5 | OK |
| ISODEC EPS | 200mm | 9.1 | 9.1 | 9.1 | 9.1 | 9.1 | OK |
| ISODEC EPS | 250mm | 10.4 | 10.4 | 10.4 | 10.4 | 10.4 | OK |
| ISODEC PIR | 50mm | 3.5 | 3.5 | 3.5 | 3.5 | 3.5 | OK |
| ISODEC PIR | 80mm | 5.5 | 5.5 | 5.5 | 5.5 | 5.5 | OK |
| ISODEC PIR | 120mm | 7.6 | 7.6 | 7.6 | 7.6 | 7.6 | OK |
| ISOROOF 3G | 30mm | 2.8 | 2.8 | 2.8 | 2.8 | 2.8 | OK |
| **ISOROOF 3G** | **40mm** | **3.0** | **3.0** | **MISSING** | **MISSING** | **3.0** | **DISCREPANCY** |
| ISOROOF 3G | 50mm | 3.3 | 3.3 | 3.3 | 3.3 | 3.3 | OK |
| ISOROOF 3G | 80mm | 4.0 | 4.0 | 4.0 | 4.0 | 4.0 | OK |
| **ISOROOF Plus** | **80mm** | **4.0** | **4.0** | **MISSING** | **MISSING** | **MISSING** | **DISCREPANCY** |
| **ISOROOF Foil** | **30mm** | **2.8** | **2.8** | **MISSING** | **MISSING** | **MISSING** | **DISCREPANCY** |
| **ISOROOF Foil** | **50mm** | **3.3** | **3.3** | **MISSING** | **MISSING** | **MISSING** | **DISCREPANCY** |
| **ISOROOF Colonial** | **40mm** | **—** | **—** | **MISSING** | **MISSING** | **MISSING** | **MISSING EVERYWHERE** |
| ISOPANEL EPS | 50mm | — | — | 3.0 | 3.0 | — | Partial |
| ISOPANEL EPS | 100mm | — | — | 5.5 | 5.5 | — | Partial |
| ISOPANEL EPS | 150mm | — | — | 7.5 | 7.5 | — | Partial |
| ISOPANEL EPS | 200mm | — | — | 9.1 | 9.1 | — | Partial |
| **ISOPANEL EPS** | **250mm** | **—** | **—** | **MISSING** | **MISSING** | **—** | **MISSING EVERYWHERE** |
| **ISOWALL PIR** | **50mm** | **—** | **—** | **MISSING** | **MISSING** | **MISSING** | **MISSING EVERYWHERE** |
| **ISOWALL PIR** | **80mm** | **—** | **—** | **MISSING** | **MISSING** | **MISSING** | **MISSING EVERYWHERE** |
| **ISOFRIG SL** | **40–180mm** | **—** | **—** | **MISSING** | **MISSING** | **MISSING** | **MISSING EVERYWHERE** |

### Autoportancia Discrepancies Summary

1. **ISOROOF 3G 40mm** — Present in KB_PRECIOS (3.0m), pricing_v6.csv (3.0m),
   and formulas_v6.json (3.0m), but **missing** from `autoportancia.csv` and
   `bom_rules.json`. The BOM engine cannot validate spans for this thickness.

2. **ISOROOF Plus 80mm** — Autoportancia (4.0m) exists in KB_PRECIOS and
   pricing_v6.csv only. Missing from the three downstream files
   (`autoportancia.csv`, `bom_rules.json`, `formulas_v6.json`).

3. **ISOROOF Foil 30mm/50mm** — Same pattern: values in KB + CSV but absent
   from autoportancia.csv, bom_rules.json, and formulas_v6.json.

4. **ISOROOF Colonial 40mm** — Autoportancia not defined in ANY file. No span
   validation possible.

5. **ISOPANEL EPS** — autoportancia.csv and bom_rules.json have values for
   50–200mm, but KB_PRECIOS, pricing_v6.csv, and formulas_v6.json do not.
   Additionally, **250mm is missing from all autoportancia sources** despite
   being a valid product in the pricing tables.

6. **ISOWALL PIR, ISOFRIG SL** — No autoportancia data in any source file.

---

## SECTION 3 — Real Quotation COT-20250508: Price Analysis

### Panel Price: $49.67/m2 vs KB's $51.73/m2

| Field | Quotation Value | KB_PRECIOS Value | Match? |
|-------|-----------------|------------------|--------|
| Product | ISOROOF 3G 80mm | ISOROOF 3G 80mm | OK |
| Costo/m2 | $44.98 | $44.98 | OK |
| PVP/m2 | **$49.67** | **$51.73** | **MISMATCH: -$2.06/m2** |
| Ancho útil | 1.00m | 1.00m | OK |
| Autoportancia | 4.0m | 4.0m | OK |
| Total m2 | 132.57 | — | — |

### Explanation of the $49.67 vs $51.73 Discrepancy

The KB standard margin for ISOROOF panels is **15%** (factor ×1.15):
- $44.98 × 1.15 = **$51.73** (matches KB_PRECIOS PVP)

The quotation used a **reduced margin of 10.4%**:
- $44.98 × 1.104 = **$49.65 ≈ $49.67** (matches quotation)

The test file itself confirms `margen_paneles_pct: 10.4` — the operator applied
a non-standard discount. This means $49.67 does NOT correspond to any standard
price table entry; it is a negotiated/overridden price.

### Impact on Financials

| Metric | At KB Standard ($51.73) | At Actual ($49.67) | Delta |
|--------|-------------------------|---------------------|-------|
| Panel revenue (132.57 m2) | $6,857.79 | $6,584.87 | -$272.92 |
| Panel margin % | 15.0% | 10.4% | -4.6pp |
| Panel margin USD | $894.72 | $621.80 | -$272.92 |

### Autoportancia Violation

The quotation includes a 6.01m panel that exceeds the 4.0m autoportancia limit
for ISOROOF 3G 80mm. The test file correctly expects a `hard_stop` — the
production system should have blocked this, but the operator overrode it.

---

## SECTION 4 — Ancho Útil: Cross-File Consistency

| Product | KB_PRECIOS | pricing_v6.csv | formulas_v6.json | Status |
|---------|------------|----------------|------------------|--------|
| ISODEC EPS | 1.12m | 1.12 | 1.12 | OK |
| ISODEC PIR | 1.12m | 1.12 | 1.12 | OK |
| ISOROOF 3G | 1.00m | 1.00 | 1.00 | OK |
| ISOROOF Plus | 1.00m | 1.00 | 1.00 | OK |
| ISOROOF Foil | 1.00m | 1.00 | 1.00 | OK |
| **ISOROOF Colonial** | **Not stated** | **1.00** | **1.00** | **KB gap** |
| ISOPANEL EPS | 1.10m | 1.10 | 1.10 | OK |
| ISOWALL PIR | 1.10m | 1.10 | 1.10 | OK |
| **ISOFRIG SL** | **Not stated** | **(empty)** | **Not listed** | **MISSING** |

### Ancho Útil Issues

1. **ISOROOF Colonial** — KB_PRECIOS.md does not explicitly state ancho útil
   (every other ISOROOF variant says "Ancho útil: 1.00m"). The CSV and formulas
   file use 1.00 — likely correct but undocumented in the canonical KB.

2. **ISOFRIG SL** — Ancho útil is **missing from all three sources**. The
   pricing_v6.csv has empty fields for `ancho_util_m`, `largo_max_m`, and
   `waste_factor` for all ISOFRIG rows. The formulas_v6.json `ancho_util`
   section omits ISOFRIG entirely.

---

## SECTION 5 — Missing/Incomplete Product Data

### Products with Missing Cost Information

| Product | PVP Present? | Costo Present? | Files Affected |
|---------|-------------|----------------|----------------|
| ISOPANEL EPS 50mm | Yes ($41.88) | **No** (—) | KB_PRECIOS, pricing_v6.csv |
| ISOPANEL EPS 100mm | Yes ($46.00) | **No** | KB_PRECIOS, pricing_v6.csv |
| ISOPANEL EPS 150mm | Yes ($51.50) | **No** | KB_PRECIOS, pricing_v6.csv |
| ISOPANEL EPS 200mm | Yes ($57.00) | **No** | KB_PRECIOS, pricing_v6.csv |
| ISOPANEL EPS 250mm | Yes ($62.50) | **No** | KB_PRECIOS, pricing_v6.csv |

The GPT engine cannot calculate margins or internal costeo for any ISOPANEL
quotation. Five SKUs are affected.

### ISOROOF Accessories: Missing Cost Data

All ISOROOF accessories in KB_PRECIOS have `costo/ml = "—"` and
accessories_pricing_v6.csv has empty `cost_ml`:

| Accessory | PVP/ml | Costo/ml | Note |
|-----------|--------|----------|------|
| Gotero Frontal Simple | 6.60 | — | KB suggests 20% margin estimation |
| Gotero Frontal con Greca | — | — | PVP also missing |
| Gotero Lateral ISOROOF | 9.48 | — | |
| Cumbrera Roof 3G | 13.20 | — | |
| Canalón Doble 80mm | 27.81 | — | |
| Soporte Canalón ISOROOF | 4.23 | — | |
| Limahoya estándar | 7.40 | — | |

KB_PRECIOS notes: "usar estimación de margen 20% (PVP / 1.20)" for missing
costs. But this is an approximation, not actual cost data.

### ISOFRIG SL: Systematically Incomplete in CSV

All ISOFRIG rows in `pricing_v6.csv` are missing:
- `ancho_util_m` — empty
- `autoportancia_m` — empty
- `largo_max_m` — empty
- `waste_factor` — empty

The KB_PRECIOS.md does provide waste factors (1.10 for techo, 1.14 for cámara)
but these are not reflected in the CSV.

### Gotero Frontal con Greca — Completely Missing Pricing

KB_PRECIOS lists "Gotero Frontal con Greca" with both PVP and Costo as "—".
accessories_pricing_v6.csv confirms: pvp_ml and cost_ml are both empty.
The accessories_catalog.json does have a price (GFCGR30: $7.24/ml IVA-inc)
but this is not reflected in the quotation knowledge base.

---

## SECTION 6 — Accessory/Fixation Prices: accessories_catalog.json vs KB_PRECIOS.md

**Critical architectural note:** `accessories_catalog.json` prices are
IVA-inclusive (22%) from the BROMYROS supplier. `KB_PRECIOS.md` lists PVP
prices that are ex-IVA (IVA is added at the total level). These are **two
different pricing layers** — but `bom_rules.json` states "Los precios se
obtienen de accessories_catalog.json", creating ambiguity about which source
the engine should use.

### ISODEC Accessories Comparison

To compare, catalog prices are converted to ex-IVA (÷1.22).

| Item | KB PVP/ml (ex-IVA) | Catalog /ml (IVA-inc) | Catalog /ml (ex-IVA) | Delta % |
|------|--------------------|-----------------------|----------------------|---------|
| Gotero Frontal 100mm | 5.22 | 6.31 | 5.17 | -0.9% |
| Gotero Lateral 100mm | 6.92 | 8.45 | 6.92 | 0.0% |
| Perfil Aluminio 5852 | 9.30 | 11.35 | 9.30 | **0.0%** |
| Cumbrera ISODEC | 7.86 | 9.49 | 7.78 | -1.0% |
| Babeta Atornillar | 4.06 | 4.96 | 4.06 | 0.0% |
| Babeta Empotrar | 4.06 | 4.96 | 4.06 | 0.0% |
| Canalón ISODEC 100mm | 23.18 | 28.00 | 22.95 | -1.0% |
| Soporte Canalón ISODEC | 5.31 | 6.48 | 5.31 | 0.0% |

ISODEC accessories are **broadly consistent** (<1% rounding differences).

### ISOROOF Accessories: Structural Price Mismatch

The KB gives **one generic price** per accessory type, but the catalog has
**thickness-specific prices**. This is a design-level inconsistency.

| Item | KB PVP/ml (ex-IVA) | Catalog 30mm (ex-IVA) | Catalog 50mm (ex-IVA) | Catalog 80mm (ex-IVA) |
|------|--------------------|-----------------------|-----------------------|-----------------------|
| Gotero Frontal Simple | 6.60 | 5.22 | 5.53 | **5.82** |
| Gotero Lateral | 9.48 | 7.27 | 7.86 | **8.44** |

The KB's generic price of 6.60/ml for Gotero Frontal Simple does not match
any thickness-specific catalog price. Even the highest (80mm = 5.82 ex-IVA)
is 11.8% lower than the KB's 6.60.

| Item | KB PVP/ml (ex-IVA) | Catalog (ex-IVA) | Delta % | Note |
|------|--------------------|--------------------|---------|------|
| Cumbrera Roof 3G | 13.20 | 11.74 | -11.1% | Catalog largo=3.0m vs KB largo=3.03m |
| Canalón Doble 80mm | 27.81 | 24.49 | -11.9% | |
| Soporte Canalón ISOROOF | 4.23 | 4.37 | **+3.3%** | **Catalog HIGHER than KB PVP** |
| Limahoya estándar | 7.40 | **NOT IN CATALOG** | — | Missing entirely |

**Soporte Canalón ISOROOF** is flagged as an anomaly: the BROMYROS catalog
ex-IVA cost ($4.37) is **higher** than the KB sale price ($4.23), which would
imply a negative margin if the catalog is the cost source.

### Fixation Items: Significant Price Divergences

| Item | KB PVP (ex-IVA) | KB Costo | Catalog (IVA-inc) | Catalog (ex-IVA) | KB vs Cat. ex-IVA |
|------|-----------------|----------|-------------------|------------------|-------------------|
| Silicona Neutra 300ml | 7.11 | 2.42 | 11.58 (600ml) | 9.49 (600ml) | Not comparable (different sizes) |
| Varilla Roscada 3/8" | 2.43 | 1.15 | 3.81 | **3.12** | **Catalog 28% higher than KB PVP** |
| Tuerca Galv. 3/8" | 0.15 | 0.03 | 0.15 | 0.12 | -20% |
| Arandela Carrocero | 2.00 | 0.29 | 2.05 | 1.68 | -16% |
| Arandela Plana | 0.24 | 0.03 | 0.35 | 0.29 | **Catalog 21% higher than KB PVP** |
| Arandela Polipropileno | 1.60 | 0.60 | 1.55 | 1.27 | -21% |
| Membrana Autoadhesiva | 36.20 | 24.10 | 20.28 | **16.62** | **Catalog 54% lower than KB PVP** |
| Taco Expansivo 3/8" | 0.53 | 0.33 | 1.17 | **0.96** | **Catalog 81% higher than KB PVP** |
| Caballete Roof | 0.63 | 0.30 | 0.60 | 0.49 | -22% |

### Critical Fixation Price Anomalies

1. **Varilla Roscada 3/8"** — Catalog ex-IVA ($3.12) is **28% higher** than
   the KB PVP ($2.43). If the catalog is the cost basis, the company is selling
   below cost.

2. **Taco Expansivo 3/8"** — Catalog ex-IVA ($0.96) is **81% higher** than
   the KB PVP ($0.53). Same below-cost concern.

3. **Arandela Plana** — Catalog ex-IVA ($0.29) exceeds KB PVP ($0.24) by 21%.

4. **Membrana Autoadhesiva** — Opposite direction: catalog ex-IVA ($16.62) is
   **54% lower** than KB PVP ($36.20), suggesting the KB may be outdated or the
   catalog is a different product spec.

5. **Caballete Roof** — Catalog IVA-inclusive ($0.60) is lower than KB ex-IVA
   PVP ($0.63). Logically impossible if the catalog is the cost source and
   prices include IVA.

---

## SECTION 7 — Structural/Architectural Issues

### 7.1 — IVA Double-Counting Risk

| Source | IVA Policy |
|--------|------------|
| `accessories_catalog.json` | Prices **include** IVA 22% |
| `bom_rules.json` | "Los precios de accessories_catalog.json YA incluyen IVA. NO sumar IVA adicional." |
| `KB_PRECIOS.md` | Prices are **ex-IVA**; "Total Final = Subtotal + IVA" |
| `formulas_v6.json` | `"iva": "subtotal * 0.22"` |

If the quotation engine uses `accessories_catalog.json` prices (IVA-inclusive)
and then applies `subtotal * 0.22` for IVA, accessories will be **double-taxed
at 22%**. If it uses `KB_PRECIOS.md` prices (ex-IVA), the IVA formula is
correct — but `bom_rules.json` explicitly says to use the catalog.

**This is a critical ambiguity that must be resolved.**

### 7.2 — Cumbrera Roof 3G: Largo Discrepancy

| Source | Largo std |
|--------|-----------|
| KB_PRECIOS.md | 3.03m |
| accessories_pricing_v6.csv | 3.03m |
| accessories_catalog.json | **3.0m** |

The catalog uses 3.0m for the cumbrera bar length, while KB and CSV use 3.03m.
This affects per-meter pricing calculations and quantity estimations.

### 7.3 — Two Pricing Universes

The system has two parallel pricing sources that serve different purposes:

1. **KB_PRECIOS.md + pricing_v6.csv + accessories_pricing_v6.csv** — The GPT
   quotation engine's canonical source. Prices are ex-IVA PVP and internal cost.

2. **accessories_catalog.json** — BROMYROS supplier catalog with IVA-inclusive
   prices. Referenced by `bom_rules.json` for BOM quantity calculations.

These are fundamentally different data layers with different tax treatments,
different granularity (generic vs thickness-specific for ISOROOF accessories),
and non-trivial price deltas. The system needs a clear rule for which source
governs final pricing.

---

## SECTION 8 — Complete Discrepancy Registry

| # | Severity | Category | Description |
|---|----------|----------|-------------|
| 1 | HIGH | Autoportancia | ISOROOF 3G 40mm missing from `autoportancia.csv` and `bom_rules.json` |
| 2 | HIGH | Autoportancia | ISOROOF Plus 80mm missing from `autoportancia.csv`, `bom_rules.json`, `formulas_v6.json` |
| 3 | HIGH | Autoportancia | ISOROOF Foil 30/50mm missing from `autoportancia.csv`, `bom_rules.json`, `formulas_v6.json` |
| 4 | HIGH | Autoportancia | ISOPANEL EPS 250mm missing from `autoportancia.csv` and `bom_rules.json` |
| 5 | HIGH | Architecture | IVA double-counting risk: `bom_rules.json` says use catalog (IVA-inc) but formula adds IVA again |
| 6 | HIGH | Pricing | Varilla Roscada 3/8": catalog ex-IVA ($3.12) > KB PVP ($2.43) — below-cost sale |
| 7 | HIGH | Pricing | Taco Expansivo 3/8": catalog ex-IVA ($0.96) > KB PVP ($0.53) — below-cost sale |
| 8 | MEDIUM | Quotation | COT-20250508 panel price $49.67/m2 uses 10.4% margin, not standard 15% ($51.73) |
| 9 | MEDIUM | Missing Data | ISOPANEL EPS: costo/m2 missing for all 5 thicknesses |
| 10 | MEDIUM | Missing Data | ISOROOF accessories: 7 items have no costo/ml |
| 11 | MEDIUM | Missing Data | ISOFRIG SL: ancho_util, largo_max, waste_factor, autoportancia all missing from CSV |
| 12 | MEDIUM | Missing Data | Gotero Frontal con Greca: PVP and Costo both missing from KB and CSV |
| 13 | MEDIUM | Pricing | ISOROOF accessories: KB uses generic per-type pricing; catalog has thickness-specific prices |
| 14 | MEDIUM | Pricing | Membrana Autoadhesiva: catalog ($16.62 ex-IVA) vs KB PVP ($36.20) — 54% gap |
| 15 | MEDIUM | Pricing | Arandela Plana: catalog ex-IVA ($0.29) > KB PVP ($0.24) — below-cost sale |
| 16 | MEDIUM | Pricing | Soporte Canalón ISOROOF: catalog ex-IVA ($4.37) > KB PVP ($4.23) — negative margin |
| 17 | MEDIUM | Dimension | Cumbrera Roof 3G largo: catalog=3.0m vs KB/CSV=3.03m |
| 18 | LOW | Missing Data | ISOROOF Colonial: autoportancia not defined anywhere |
| 19 | LOW | Missing Data | ISOWALL PIR: autoportancia not defined anywhere |
| 20 | LOW | Missing Data | ISOFRIG SL: autoportancia not defined anywhere |
| 21 | LOW | Missing Data | ISOROOF Colonial: ancho_util not stated in KB_PRECIOS.md |
| 22 | LOW | Missing Data | ISOFRIG SL: ancho_util not stated in KB_PRECIOS.md |
| 23 | LOW | Missing Data | Limahoya estándar: not present in `accessories_catalog.json` |
| 24 | LOW | Pricing | Caballete Roof: catalog IVA-inc ($0.60) < KB ex-IVA PVP ($0.63) — logically inconsistent |
| 25 | LOW | SKU | accessories_catalog.json reuses SKU "6805" for 15+ different items (arandela, soporte, varilla, tuerca, membrana, etc.) |

---

## SECTION 9 — Recommended Actions

### Immediate (blocks quotation accuracy)
1. **Resolve IVA architecture** — Define once whether the engine uses ex-IVA
   (KB_PRECIOS) or IVA-inc (catalog) prices, and ensure formulas match.
2. **Add ISOPANEL EPS costs** — 5 SKUs cannot be costed.
3. **Add ISOROOF accessory costs** — 7 items cannot be margin-checked.
4. **Sync ISOROOF 3G 40mm** into `autoportancia.csv` and `bom_rules.json`.

### Short-term (data quality)
5. Populate ISOFRIG SL metadata in `pricing_v6.csv` (ancho_util, waste_factor, largo_max).
6. Add ISOROOF Plus and Foil to `autoportancia.csv`, `bom_rules.json`, `formulas_v6.json`.
7. Reconcile fixation prices (varilla, taco, arandela) between catalog and KB.
8. Add Limahoya estándar to `accessories_catalog.json`.
9. Fix Cumbrera Roof 3G largo in catalog (3.0 → 3.03m).

### Medium-term (structural)
10. Assign unique SKUs in `accessories_catalog.json` (currently "6805" is reused ~15 times).
11. Introduce thickness-specific ISOROOF accessory pricing in KB_PRECIOS to match catalog granularity.
12. Document the relationship between BROMYROS catalog prices and KB PVP/Costo (markup rules).

---

*Report generated: 2026-02-25 | Analyst: Panelin v6 Consistency Audit*
