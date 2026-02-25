# IVA Architecture Decision Record

**Date**: 2026-02-25
**Status**: DECIDED
**Decision**: Option A — Prices ex-IVA, IVA added at total

---

## Context

The system has two pricing sources with different IVA treatment:

| Source | IVA Treatment | Used By |
|--------|--------------|---------|
| `KB_PRECIOS.md` / `pricing_v6.csv` | Prices are **ex-IVA** (PVP neto) | v6 GPT, PDF generator |
| `accessories_catalog.json` / `bom_rules.json` | Prices **include IVA 22%** | Old BOM engine |

Using both simultaneously risks double-taxing accessories.

## Decision

**All v6 pricing is ex-IVA.** The PDF generator adds IVA 22% at the total level.

### Rules

1. All prices in `KB_PRECIOS.md`, `pricing_v6.csv`, and `accessories_pricing_v6.csv` are **ex-IVA**
2. The v6 JSON fields `precio_m2`, `precio_ml`, `precio_unit` are **ex-IVA** sale prices
3. The v6 JSON fields `costo_m2`, `costo_ml`, `costo_real` are **ex-IVA** internal costs
4. `panelin_pdf_v6.py` calculates: `IVA = subtotal * 0.22`, `Total = subtotal + IVA`
5. `accessories_catalog.json` prices (IVA-inclusive) must be divided by 1.22 before use in v6 context

### Migration Note

When converting from `accessories_catalog.json` to v6 pricing:
```
v6_price = catalog_price_iva_inc / 1.22
```

This was applied in `kb/accessories_pricing_v6.csv` where ISODEC accessory costs were derived from catalog prices.
