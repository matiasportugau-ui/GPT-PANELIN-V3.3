# Guía de Modificación de Pesos (kg) para GPT-PANELIN

**Fecha:** 2026-02-17  
**Versión:** 1.0  
**Repositorio:** GPT-PANELIN-V3.3

---

## Resumen Ejecutivo

✅ **SÍ - El GPT puede modificar valores de peso (kg) en el catálogo**

El sistema GPT-PANELIN tiene capacidad completa para modificar valores de peso (kg) en el catálogo de productos a través de dos mecanismos autorizados y auditados. Este documento explica cómo funciona esta capacidad y cómo utilizarla.

---

## 1. Dónde se Almacenan los Datos de Peso

### 1.1 Ubicación en el Catálogo

Los datos de peso se encuentran en `shopify_catalog_v1.json`, dentro de cada variante de producto:

```json
{
  "products_by_handle": {
    "product-example": {
      "variants": [
        {
          "sku": "CONBPVC",
          "grams": 1000,
          "weight_unit": "kg",
          ...
        }
      ]
    }
  }
}
```

**Campos de peso:**
- `grams`: Peso en gramos (ej: 1000 = 1 kg)
- `weight_unit`: Unidad de medida (normalmente "kg")

### 1.2 Propósito de los Datos de Peso

Estos datos representan el **peso de envío** de los productos y se utilizan para:
- Cálculo de costos de transporte
- Logística y planificación de entregas
- Integración con sistemas de fulfillment de Shopify

---

## 2. Mecanismos de Modificación

El GPT puede modificar valores de peso mediante **dos métodos autorizados**:

### 2.1 Método 1: Wolf API - register_correction

**Herramienta MCP:** `register_correction`  
**Archivo Handler:** `mcp/handlers/wolf_kb_write.py`  
**Requiere:** Contraseña de escritura KB

#### Cuándo Usar Este Método
- Correcciones puntuales de peso detectadas durante conversaciones
- Actualizaciones basadas en información de proveedores
- Correcciones de errores en catálogo

#### Parámetros Requeridos

```json
{
  "source_file": "shopify_catalog_v1.json",
  "field_path": "products_by_handle['product-handle'].variants[0].grams",
  "old_value": "1000",
  "new_value": "1200",
  "reason": "Actualización de proveedor - nuevo peso de empaque",
  "password": "***"
}
```

#### Ejemplo de Uso en Conversación

**Usuario:** "El producto CONBPVC ahora pesa 1.2 kg en lugar de 1 kg"

**GPT:** "Voy a registrar esta corrección de peso. Por favor, proporcióname la contraseña de escritura KB para autorizar el cambio."

*[Usuario proporciona contraseña]*

```
Llamando a register_correction:
- Archivo: shopify_catalog_v1.json
- Campo: products_by_handle['embudo-conector-de-bajada-pvc-para-canaleta-100mm'].variants[0].grams
- Valor anterior: "1000"
- Valor nuevo: "1200"
- Razón: "Actualización del proveedor BECAM - nuevo peso de empaque"
- Contraseña: [proporcionada por usuario]
```

**Resultado:**
- ✅ Corrección registrada en Wolf API
- ✅ ID de corrección generado (ej: `cor-20260217142530`)
- ✅ Timestamp almacenado para auditoría

---

### 2.2 Método 2: Flujo de Gobernanza - validate_correction + commit_correction

**Herramientas MCP:** `validate_correction` + `commit_correction`  
**Archivo Handler:** `mcp/handlers/governance.py`  
**Requiere:** Confirmación explícita del usuario

#### Cuándo Usar Este Método
- Cambios que pueden afectar cotizaciones existentes
- Modificaciones que requieren análisis de impacto
- Cambios que necesitan aprobación formal

#### Flujo de Trabajo

**Paso 1: Validar Corrección**

```json
{
  "kb_file": "shopify_catalog_v1.json",
  "field": "products_by_handle['product-handle'].variants[0].grams",
  "current_value": "1000",
  "proposed_value": "1200",
  "source": "proveedor_update",
  "notes": "Actualización de peso por cambio en empaque"
}
```

**El sistema responde con:**
- ✅ Validación del campo (existe/no existe)
- ✅ Comparación de valor actual vs esperado
- ✅ Análisis de impacto en últimas 50 cotizaciones
- ✅ ID de cambio para commit

**Paso 2: Confirmar y Aplicar**

```json
{
  "change_id": "CHG-A1B2C3D4E5F6",
  "confirm": true
}
```

**El sistema responde con:**
- ✅ Corrección aplicada a `corrections_log.json`
- ✅ Resumen de impacto en cotizaciones
- ✅ Total de correcciones pendientes

---

## 3. Archivos Autorizados para Modificación

Los valores de peso **SOLO** pueden modificarse en archivos de la lista blanca:

✅ **Archivos permitidos:**
- `shopify_catalog_v1.json` ← **Contiene datos de peso**
- `bromyros_pricing_master.json`
- `bromyros_pricing_gpt_optimized.json`
- `accessories_catalog.json`
- `bom_rules.json`
- `BMC_Base_Conocimiento_GPT-2.json`
- `perfileria_index.json`

❌ **Archivos NO autorizados:**
- Cualquier otro archivo JSON será rechazado por seguridad

---

## 4. Seguridad y Auditoría

### 4.1 Medidas de Seguridad

✅ **Contraseña requerida**: Todas las operaciones de escritura requieren `WOLF_KB_WRITE_PASSWORD`  
✅ **Validación de entrada**: Los campos y valores son validados antes de aplicar cambios  
✅ **Lista blanca de archivos**: Solo archivos autorizados pueden ser modificados  
✅ **Registro de auditoría**: Todas las modificaciones quedan registradas con timestamp

### 4.2 Trazabilidad

Cada modificación de peso queda registrada con:
- **ID único** (ej: `COR-001`, `cor-20260217142530`)
- **Timestamp** (ISO 8601 UTC)
- **Archivo fuente** y **campo modificado**
- **Valores anterior y nuevo**
- **Razón del cambio**
- **Quién lo reportó** (opcional)

**Ubicación de logs:**
- Wolf API: Base de datos KB
- Gobernanza: `corrections_log.json` (raíz del repositorio)

---

## 5. Limitaciones Actuales

### 5.1 No Modificación Directa de Archivos

❌ El GPT **NO puede editar directamente** los archivos JSON  
✅ El GPT **SÍ puede registrar correcciones** que luego se aplican al sistema

### 5.2 Análisis de Impacto Enfocado en Precios

⚠️ El análisis de impacto actual está diseñado para cambios de **precios**, no de pesos.

**Implicación para pesos:**
- El sistema analizará las últimas 50 cotizaciones
- Buscará referencias al producto modificado
- Pero el "impacto monetario" puede ser $0.00 si solo cambió el peso

**Recomendación:** Verificar manualmente el impacto en:
- Costos de transporte
- Planificación logística
- Capacidades de carga

---

## 6. Casos de Uso Prácticos

### 6.1 Actualización de Peso por Cambio de Proveedor

**Escenario:** El proveedor BECAM cambió el empaque del embudo conector de 1 kg a 1.2 kg

**Solución:**
1. Usuario informa el cambio al GPT
2. GPT solicita contraseña de escritura KB
3. GPT llama a `register_correction` con:
   - `source_file`: "shopify_catalog_v1.json"
   - `field_path`: ruta al campo `grams` del producto
   - `old_value`: "1000"
   - `new_value`: "1200"
   - `reason`: "Actualización de proveedor BECAM - nuevo peso de empaque"

### 6.2 Corrección de Error en Catálogo

**Escenario:** Se detecta que un producto tiene peso incorrecto (error de carga inicial)

**Solución:**
1. Usuario o GPT detecta la inconsistencia
2. Usar flujo de gobernanza para análisis de impacto:
   - `validate_correction` → obtener `change_id`
   - Revisar análisis de impacto
   - `commit_correction` para aplicar

### 6.3 Actualización Masiva de Pesos

**Escenario:** Múltiples productos cambiaron de peso simultáneamente

**Solución:**
1. Registrar cada corrección individualmente con `register_correction`
2. O desarrollar un script batch (fuera del GPT) para aplicar múltiples cambios
3. Todas las correcciones quedan auditadas en Wolf API

---

## 7. Preguntas Frecuentes (FAQ)

### ¿El GPT puede modificar el peso de un producto en tiempo real?

❌ **NO directamente**. El GPT puede **registrar la corrección** que luego debe aplicarse al catálogo.

✅ **SÍ mediante autorización**. Con la contraseña correcta, el GPT registra la corrección en Wolf API para su aplicación.

### ¿Qué sucede con las cotizaciones existentes si cambio un peso?

Las cotizaciones existentes **no se recalculan automáticamente**. El análisis de impacto muestra cuántas cotizaciones referencian el producto, pero los pesos no afectan directamente el cálculo de precios (solo el transporte).

### ¿Puedo modificar cualquier campo del catálogo?

✅ **SÍ**, siempre que:
1. El archivo esté en la lista blanca
2. Tengas la contraseña de escritura KB
3. Sigas el formato correcto de `field_path`

Campos modificables incluyen: `grams`, `weight_unit`, precios, SKUs, descripciones, etc.

### ¿Cómo encuentro el field_path correcto para un producto?

**Formato:** `products_by_handle['handle-del-producto'].variants[índice].campo`

**Ejemplo:**
```
products_by_handle['embudo-conector-de-bajada-pvc-para-canaleta-100mm'].variants[0].grams
```

Para encontrar el handle correcto:
1. Buscar en `shopify_catalog_v1.json`
2. O consultar `shopify_catalog_index_v1.csv`

### ¿La modificación de peso afecta el cálculo de cotizaciones?

**No directamente**. Las cotizaciones de paneles se calculan por:
- Área en m²
- Precio por m² o m (según producto)
- Accesorios y fijaciones

El peso solo afecta:
- Cálculo de transporte (cuando se incluye)
- Logística y planificación

---

## 8. Ejemplos de Código

### 8.1 Estructura del Catálogo con Pesos

```json
{
  "products_by_handle": {
    "embudo-conector-de-bajada-pvc-para-canaleta-100mm": {
      "handle": "embudo-conector-de-bajada-pvc-para-canaleta-100mm",
      "title": "Embudo Conector de Bajada PVC para Canaleta (100mm)",
      "vendor": "BMC URUGUAY",
      "variants": [
        {
          "sku": "CONBPVC",
          "grams": 1000,           ← Peso en gramos
          "weight_unit": "kg",     ← Unidad de medida
          "requires_shipping": true,
          "taxable": true
        }
      ]
    }
  }
}
```

### 8.2 Ejemplo Completo de Corrección

```python
# Llamada al handler desde MCP
await handle_register_correction({
    "source_file": "shopify_catalog_v1.json",
    "field_path": "products_by_handle['embudo-conector-de-bajada-pvc-para-canaleta-100mm'].variants[0].grams",
    "old_value": "1000",
    "new_value": "1200",
    "reason": "Actualización de proveedor BECAM - nuevo empaque más pesado",
    "reported_by": "Juan Pérez - Logística",
    "password": os.getenv("WOLF_KB_WRITE_PASSWORD")
})

# Respuesta esperada
{
    "ok": True,
    "contract_version": "1.0.0",
    "correction_id": "cor-20260217142530",
    "stored_at": "2026-02-17T14:25:30.123456Z"
}
```

---

## 9. Guía de Implementación para Desarrolladores

### 9.1 Agregar Soporte para Modificación de Peso en la UI

Si deseas crear una interfaz para que usuarios no técnicos modifiquen pesos:

1. **Endpoint backend** que valide la contraseña
2. **Formulario** que solicite:
   - Handle del producto
   - Índice de variante
   - Nuevo peso en kg
   - Razón del cambio
3. **Llamada al MCP tool** `register_correction`
4. **Confirmación** con ID de corrección

### 9.2 Script Batch para Actualizaciones Masivas

```python
import asyncio
from mcp.handlers.wolf_kb_write import handle_register_correction

# Lista de actualizaciones
updates = [
    {
        "handle": "producto-1",
        "variant_idx": 0,
        "new_weight": 1200,
        "reason": "Actualización proveedor Q1 2026"
    },
    # ... más productos
]

async def batch_update_weights(updates, password):
    for update in updates:
        field_path = f"products_by_handle['{update['handle']}'].variants[{update['variant_idx']}].grams"
        result = await handle_register_correction({
            "source_file": "shopify_catalog_v1.json",
            "field_path": field_path,
            "old_value": str(current_weight),  # Obtener del catálogo
            "new_value": str(update['new_weight']),
            "reason": update['reason'],
            "password": password
        })
        print(f"Producto {update['handle']}: {result}")

# Ejecutar
asyncio.run(batch_update_weights(updates, "contraseña-segura"))
```

---

## 10. Recomendaciones de Seguridad

### 10.1 Protección de Contraseña

✅ **SIEMPRE** establecer `WOLF_KB_WRITE_PASSWORD` en producción  
❌ **NUNCA** usar el valor por defecto `"mywolfy"` en producción  
✅ Usar contraseñas fuertes (16+ caracteres, alfanuméricos + símbolos)  
✅ Rotar contraseña cada 90 días  
✅ Limitar acceso solo a personal autorizado

### 10.2 Auditoría

✅ Revisar periódicamente `corrections_log.json`  
✅ Verificar que todas las correcciones tengan razones válidas  
✅ Investigar correcciones anómalas o no autorizadas  
✅ Mantener respaldos del catálogo antes de aplicar cambios masivos

---

## 11. Próximos Pasos y Mejoras

### 11.1 Mejoras Planificadas

1. **Análisis de impacto específico para peso**
   - Calcular impacto en costos de transporte
   - Alertar si cambios exceden capacidades de carga

2. **Validación de rangos de peso**
   - Definir rangos razonables por tipo de producto
   - Alertar sobre cambios extremos (>50% diferencia)

3. **Sincronización automática con Shopify**
   - Aplicar correcciones directamente a Shopify vía API
   - Mantener sincronización bidireccional

4. **Dashboard de correcciones**
   - Visualizar historial de cambios de peso
   - Filtrar por producto, fecha, usuario
   - Generar reportes de auditoría

### 11.2 Documentación Adicional

Para más información sobre el sistema de correcciones, consultar:
- [WOLF_KB_WRITE_ACCESS_VERIFICATION.md](WOLF_KB_WRITE_ACCESS_VERIFICATION.md) - Verificación de acceso de escritura
- [WOLF_WRITE_ACCESS_QUICK_GUIDE.md](WOLF_WRITE_ACCESS_QUICK_GUIDE.md) - Guía rápida de escritura
- [README.md](README.md) - Documentación principal del sistema

---

## 12. Contacto y Soporte

Para preguntas sobre modificación de pesos en el catálogo:

- **Repositorio:** [GPT-PANELIN-V3.3](https://github.com/matiasportugau-ui/GPT-PANELIN-V3.3)
- **Documentación:** Ver sección MCP Tools en README.md
- **Issues:** Crear issue en GitHub con etiqueta `weight-modification`

---

**Última actualización:** 2026-02-17  
**Autor:** GitHub Copilot Coding Agent  
**Versión del documento:** 1.0
