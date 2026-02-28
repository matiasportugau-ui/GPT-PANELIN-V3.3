# GUÍA DE IMPLEMENTACIÓN — GPT Panelín v6
## Cómo configurar el Custom GPT en OpenAI

---

## Arquitectura del sistema

El prompt de 14.5K chars del archivo anterior NO cabe en el campo Instructions de OpenAI (límite: 8000 chars). La solución es dividirlo estratégicamente:

```
┌─────────────────────────────────────────────────┐
│           CUSTOM GPT — OpenAI Editor             │
├─────────────────────────────────────────────────┤
│                                                   │
│  Instructions (8000 chars máx)                    │
│  ┌─────────────────────────────────────────┐     │
│  │ 01_INSTRUCCIONES_GPT.md                 │     │
│  │ → Rol, flujo, reglas, validaciones      │     │
│  │ → 4.456 chars ✅                        │     │
│  └─────────────────────────────────────────┘     │
│                                                   │
│  Knowledge Files (sin límite práctico)            │
│  ┌─────────────────────────────────────────┐     │
│  │ KB_PRECIOS.md        (5.6K chars)       │     │
│  │ → Precios PVP + Costos de todos los     │     │
│  │   paneles, accesorios y fijaciones      │     │
│  ├─────────────────────────────────────────┤     │
│  │ KB_FORMULAS.md       (3.8K chars)       │     │
│  │ → Fórmulas de cantidades, desperdicio,  │     │
│  │   autoportancia, largos máximos         │     │
│  ├─────────────────────────────────────────┤     │
│  │ KB_ESTRUCTURA_JSON.md (8.0K chars)      │     │
│  │ → Template JSON, datos empresa, lista   │     │
│  │   comentarios, nombres estándar         │     │
│  └─────────────────────────────────────────┘     │
│                                                   │
│  Capabilities                                     │
│  ☑ Code Interpreter (para leer Knowledge)        │
│  ☐ Web Browsing                                  │
│  ☐ DALL·E                                        │
│                                                   │
└─────────────────────────────────────────────────┘
          │
          ▼ genera JSON
┌─────────────────────────────────────────────────┐
│         panelin_pdf_v6.py                         │
│  → Recibe JSON                                    │
│  → Genera PDF Cotización (cliente)                │
│  → Genera PDF Costeo (interno)                    │
└─────────────────────────────────────────────────┘
```

---

## Paso a paso

### 1. Crear el GPT
- Ir a https://chat.openai.com/gpts/editor
- Click en "Create"

### 2. Pestaña "Configure"

**Name:**
```
BMC Uruguay - Cotizador Panelín v6
```

**Description:**
```
Asistente de ventas y cotización de paneles aislantes termoacústicos. Genera presupuestos en formato JSON para ISODEC, ISOROOF, ISOPANEL, ISOWALL e ISOFRIG con precios, costos y márgenes.
```

**Instructions:**
Copiar TODO el contenido de `01_INSTRUCCIONES_GPT.md` (4.456 chars — cabe holgado en los 8.000 del límite).

**Knowledge:**
Subir los 3 archivos:
1. `KB_PRECIOS.md`
2. `KB_FORMULAS.md`
3. `KB_ESTRUCTURA_JSON.md`

**Conversation Starters:**
```
Necesito cotizar un techo de 6x4 metros en ISODEC 100mm
```
```
Cotización completa: 8 paneles ISOROOF 80mm de 5m a madera, con canalón
```
```
¿Qué panel me recomendás para una pared de 12 metros?
```
```
¿Cuál es la diferencia entre ISODEC EPS y PIR?
```

**Capabilities:**
- ☑ Code Interpreter (necesario para leer archivos Knowledge)
- ☐ Web Browsing (no necesario)
- ☐ DALL·E Image Generation (no necesario)

### 3. Guardar
- Visibilidad: "Only me" para testing
- Probar con los 4 casos de prueba abajo
- Si todo OK → cambiar a "Anyone with a link" para equipo

---

## Casos de prueba

### Test 1: Cotización ISOROOF simple
**Input:** "Necesito 4 paneles ISOROOF 80mm de 5 metros, fijación a madera"

**Verificar:**
- precio_m2 = 51.73 (no inventado)
- costo_m2 = 44.98
- ancho_util_m = 1.00
- Sistema caballetes (sin varilla ni tuercas)
- Incluye silicona, caballetes, tornillos aguja, tornillos T1
- Advertencia: largo 5m > autoportancia 4m

### Test 2: Cotización ISODEC a metal
**Input:** "Cotizar ISODEC EPS 150mm, 10 paneles de 7 metros, fijación a metal"

**Verificar:**
- precio_m2 = 42.48, costo_m2 = 36.94
- ancho_util_m = 1.12
- Sistema varilla 3/8" + tuercas
- Factor desperdicio 1.12 en cálculo de accesorios
- Sin advertencia de autoportancia (7m < 7.5m)

### Test 3: Validación de autoportancia
**Input:** "ISOROOF 30mm de 4 metros"

**Verificar:**
- Debe advertir: 4m > 2.8m de autoportancia
- Sugerir apoyos intermedios o espesor mayor

### Test 4: JSON completo
**Input:** Confirmar cualquier cotización y pedir el JSON

**Verificar:**
- Estructura correcta según KB_ESTRUCTURA_JSON.md
- cotizacion.numero = null
- Todos los campos de costo presentes
- Comentarios con autoportancia correcta
- Datos empresa = fijos (Metalog SAS, etc.)

---

## Mantenimiento

### Actualizar precios
Editar `KB_PRECIOS.md` y re-subir al GPT. No tocar Instructions.

### Agregar producto nuevo
1. Agregar a `KB_PRECIOS.md` (precios y costos)
2. Agregar autoportancia a `KB_FORMULAS.md` si aplica
3. Agregar nombre estándar a `KB_ESTRUCTURA_JSON.md`
4. Re-subir los 3 archivos

### Cambiar reglas de negocio
Editar `01_INSTRUCCIONES_GPT.md` y actualizar en Instructions del GPT.

### Cambiar datos empresa
Editar `KB_ESTRUCTURA_JSON.md` en la sección empresa.
