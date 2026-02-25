# KB Contract (mínimo viable)

## 1) catalog.csv (obligatorio)
Campos:
- sku_id (único, estable)
- family (ej: ISOWALL / ISOROOF / UNIVERSAL)
- system (VERTICAL/HORIZONTAL/ALL)
- product_type (panel/accessory/profile/fastener/sealant)
- thickness_mm (si aplica)
- unit_sale (m2/ml/u)
- description
- active (true/false)

Reglas:
- No se permiten SKUs duplicados.
- unit_sale debe ser consistente con pricing.price_unit.

## 2) pricing.csv (obligatorio para cotización)
Campos:
- sku_id (FK a catalog)
- currency
- price (num) — si falta y se necesita: hard-stop "No tengo esa información en mi base de conocimiento"
- price_unit (m2/ml/u)
- iva_rate (ej 0.21)
- effective_from / effective_to (opcional)

## 3) autoportancia.csv (obligatorio para techo)
Campos mínimos:
- family, thickness_mm, support_condition, span_m_max, load_kPa (+ opcionales pendiente)
Si no hay match aplicable: hard-stop de autoportancia.
