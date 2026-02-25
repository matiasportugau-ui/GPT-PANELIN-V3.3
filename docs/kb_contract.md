# KB Contract (Panelin Studio — ChatOps Automation Pack v1)

## /kb/catalog.csv
Columnas:
- sku (string, único)
- name (string)
- category (panels | accessories | consumables)
- unit (m2 | m | unit)
- pack_qty (número, default 1)
- is_placeholder (bool)
- notes (string)

Reglas:
- Un SKU representa 1 unidad de su `unit` (m2/m/unit).
- `pack_qty` se usa si el SKU se vende por pack; el motor debe convertir qty a packs si se configura (no implementado en starter).

## /kb/pricing.csv
Columnas:
- sku
- currency (ARS/USD/etc)
- price (number) -> en starter puede estar vacío
- vat_included (true/false)
- valid_from / valid_to (opcional)
- source (PLACEHOLDER/PROVIDER/etc)
- notes

Hard-stop:
- Si un SKU requerido por BOM no tiene precio -> "No tengo esa información en mi base de conocimiento".

## /kb/autoportancia.csv
Objetivo: validar que para HORIZONTAL exista un match:
(panel_family, thickness_mm, span_m <= span_m_max, load_class)
Si no matchea -> hard-stop AUTO_PORTANCIA_NO_MATCH.
