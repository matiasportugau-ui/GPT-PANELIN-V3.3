# MCP Server Usage Examples

This document provides practical examples for using each of the four MCP tools exposed by the Panelin MCP Server.

---

## 🏷️ price_check

### Example 1: Look up price by exact SKU

**Request:**
```json
{
  "tool": "price_check",
  "arguments": {
    "query": "ISODEC-100-1000",
    "filter_type": "sku"
  }
}
```

**Use Case:** Customer asks "How much is ISODEC-100-1000?"

---

### Example 2: Search for products by family

**Request:**
```json
{
  "tool": "price_check",
  "arguments": {
    "query": "ISODEC",
    "filter_type": "family"
  }
}
```

**Use Case:** Browse all ISODEC panel prices

---

### Example 3: Filter by thickness

**Request:**
```json
{
  "tool": "price_check",
  "arguments": {
    "query": "ISOPANEL",
    "filter_type": "family",
    "thickness_mm": 80
  }
}
```

**Use Case:** "Show me 80mm ISOPANEL prices"

---

### Example 4: Natural language search

**Request:**
```json
{
  "tool": "price_check",
  "arguments": {
    "query": "panel aislante para techo industrial",
    "filter_type": "search"
  }
}
```

**Use Case:** Customer describes what they need without knowing the SKU

---

## 🔍 catalog_search

### Example 1: Search by keyword

**Request:**
```json
{
  "tool": "catalog_search",
  "arguments": {
    "query": "isodec",
    "category": "all",
    "limit": 5
  }
}
```

**Use Case:** "Show me ISODEC products"

---

### Example 2: Filter by category

**Request:**
```json
{
  "tool": "catalog_search",
  "arguments": {
    "query": "panel",
    "category": "techo",
    "limit": 10
  }
}
```

**Use Case:** "I need roof panels"

---

### Example 3: Search accessories

**Request:**
```json
{
  "tool": "catalog_search",
  "arguments": {
    "query": "gotero",
    "category": "accesorio",
    "limit": 5
  }
}
```

**Use Case:** "What gutters do you have?"

---

### Example 4: Cold storage products

**Request:**
```json
{
  "tool": "catalog_search",
  "arguments": {
    "query": "camara fria",
    "category": "camara",
    "limit": 5
  }
}
```

**Use Case:** "I'm building a cold storage facility"

---

## 📋 bom_calculate

### Example 1: Industrial roof calculation

**Request:**
```json
{
  "tool": "bom_calculate",
  "arguments": {
    "product_family": "ISODEC",
    "thickness_mm": 100,
    "core_type": "EPS",
    "usage": "techo",
    "length_m": 12.0,
    "width_m": 6.0
  }
}
```

**Use Case:** "I need a complete quotation for a 12m x 6m industrial roof with 100mm ISODEC EPS panels"

**Response includes:**
- Panel quantities
- Fixation requirements (screws, washers, PVC turtles)
- Accessories (front gutters, lateral gutters, ridge caps)
- Sealants (silicone, butyl tape)
- Load-bearing validation results
- Total quantities and subtotals

---

### Example 2: Facade wall calculation

**Request:**
```json
{
  "tool": "bom_calculate",
  "arguments": {
    "product_family": "ISOPANEL",
    "thickness_mm": 80,
    "core_type": "EPS",
    "usage": "pared",
    "length_m": 15.0,
    "width_m": 3.5
  }
}
```

**Use Case:** "Quote me a 15m x 3.5m facade with 80mm ISOPANEL"

---

### Example 3: Cold storage chamber

**Request:**
```json
{
  "tool": "bom_calculate",
  "arguments": {
    "product_family": "ISOFRIG",
    "thickness_mm": 100,
    "core_type": "PIR",
    "usage": "camara",
    "length_m": 8.0,
    "width_m": 5.0
  }
}
```

**Use Case:** "I need a complete BOM for an 8m x 5m cold storage chamber with 100mm ISOFRIG PIR"

---

### Example 4: Lightweight roof

**Request:**
```json
{
  "tool": "bom_calculate",
  "arguments": {
    "product_family": "ISOROOF",
    "thickness_mm": 50,
    "core_type": "EPS",
    "usage": "techo",
    "length_m": 20.0,
    "width_m": 8.0
  }
}
```

**Use Case:** "Generate BOM for a 20m x 8m lightweight roof with ISOROOF 50mm"

---

## 🐛 report_error

### Example 1: Report incorrect price

**Request:**
```json
{
  "tool": "report_error",
  "arguments": {
    "kb_file": "accessories_catalog.json",
    "field": "items[32].price_usd",
    "wrong_value": "45.00",
    "correct_value": "47.50",
    "source": "user_correction",
    "notes": "Customer confirmed price with supplier on 2026-02-12"
  }
}
```

**Use Case:** Customer reports that the price shown doesn't match what they were quoted

---

### Example 2: Report missing product

**Request:**
```json
{
  "tool": "report_error",
  "arguments": {
    "kb_file": "bromyros_pricing_master.json",
    "field": "data.products[index_to_find].sku",
    "wrong_value": "null",
    "correct_value": "Product should exist: ISODEC EPS 120mm with SKU ISODEC_EPS_120",
    "source": "validation_check",
    "notes": "Product exists in catalog but missing from pricing data. Note: data.products is an array; specify the actual index or search criteria."
  }
}
```

**Use Case:** Automated validation discovers missing data

**Note:** The `bromyros_pricing_master.json` file stores products under `data.products` as an array. Use the appropriate array index or search pattern in the field path.

---

### Example 3: Report technical specification error

**Request:**
```json
{
  "tool": "report_error",
  "arguments": {
    "kb_file": "bom_rules.json",
    "field": "autoportancia.tablas.80.3500",
    "wrong_value": "4.5",
    "correct_value": "4.8",
    "source": "web_verification",
    "notes": "Verified against manufacturer technical sheet - BMC website updated 2026-02"
  }
}
```

**Use Case:** Load-bearing capacity table has outdated value

---

### Example 4: Report catalog inconsistency

**Request:**
```json
{
  "tool": "report_error",
  "arguments": {
    "kb_file": "shopify_catalog_v1.json",
    "field": "products_by_handle.isopanel-80.description",
    "wrong_value": "Panel with 75mm thickness",
    "correct_value": "Panel with 80mm thickness",
    "source": "audit",
    "notes": "Description mentions wrong thickness - should be 80mm not 75mm"
  }
}
```

**Use Case:** Manual audit finds description mismatch

---

## 🔄 Chaining Multiple Tools

### Scenario: Complete quotation workflow

1. **Search for product:**
```json
{"tool": "catalog_search", "arguments": {"query": "isodec", "category": "techo"}}
```

2. **Check price:**
```json
{"tool": "price_check", "arguments": {"query": "ISODEC-100-1000", "filter_type": "sku"}}
```

3. **Calculate BOM:**
```json
{
  "tool": "bom_calculate",
  "arguments": {
    "product_family": "ISODEC",
    "thickness_mm": 100,
    "core_type": "EPS",
    "usage": "techo",
    "length_m": 12.0,
    "width_m": 6.0
  }
}
```

4. **Report any errors found:**
```json
{
  "tool": "report_error",
  "arguments": {
    "kb_file": "accessories_catalog.json",
    "field": "items[15].stock_status",
    "wrong_value": "in_stock",
    "correct_value": "out_of_stock",
    "source": "user_correction",
    "notes": "Customer called warehouse - item is back-ordered"
  }
}
```

---

## 📝 Notes

- All prices returned include IVA 22% (Uruguay tax)
- Prices are in USD
- BOM calculations use parametric rules from `bom_rules.json`
- Load-bearing capacity validation is automatic in BOM calculations
- Error reports are persisted to `corrections_log.json`

---

**For more information, see:**
- [MCP Server Documentation](README.md#-mcp-server)
- [MCP Quick Start Guide](MCP_QUICK_START.md)
- [Tool Schemas](mcp/tools/)
