# PANELÍN v6 — Implementación en Google AI Studio
## Guía paso a paso para crear la app de cotización BMC Uruguay

---

## Arquitectura

```
┌──────────────────────────────────────────────────────────────┐
│              GOOGLE AI STUDIO — Gemini App                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  System Instructions (sin límite práctico)                   │
│  ┌────────────────────────────────────────────────┐          │
│  │ SYSTEM_INSTRUCTION.md                          │          │
│  │ → Rol, flujo, reglas, validaciones, fórmulas,  │          │
│  │   precios, estructura JSON — TODO en uno       │          │
│  │ → ~22K chars (Gemini soporta hasta 32K+)       │          │
│  └────────────────────────────────────────────────┘          │
│                                                              │
│  Archivos adjuntos (Knowledge / Context)                     │
│  ┌────────────────────────────────────────────────┐          │
│  │ EJEMPLO_COTIZACION.json     (JSON de ejemplo)  │          │
│  │ TABLA_PRECIOS_COMPLETA.csv  (precios en CSV)   │          │
│  └────────────────────────────────────────────────┘          │
│                                                              │
│  Modelo: Gemini 2.0 Flash / Pro                              │
│  Temperature: 0.2 (baja para precisión en precios)           │
│  Safety: Default                                             │
│                                                              │
└──────────────────────────────────────────────────────────────┘
          │
          ▼ genera JSON
┌──────────────────────────────────────────────────────────────┐
│         panelin_pdf_v6.py (externo)                          │
│  → Recibe JSON del chat                                      │
│  → Genera PDF Cotización (cliente)                           │
│  → Genera PDF Costeo (interno)                               │
└──────────────────────────────────────────────────────────────┘
```

### Diferencia clave vs OpenAI GPT

| Aspecto | OpenAI Custom GPT | Google AI Studio |
|---------|-------------------|------------------|
| System Instructions | 8,000 chars máx | 32,000+ chars (sin límite práctico) |
| Knowledge files | Archivos separados con RAG | Todo en System Instructions + adjuntos |
| Ventaja | RAG búsqueda semántica | Contexto completo siempre disponible |
| Riesgo | RAG puede no encontrar dato | Contexto largo puede diluir atención |
| Code Interpreter | Sí (cálculos) | Sí (Code Execution en Gemini) |

**Ventaja de Google AI Studio**: Como no hay límite de 8K, podemos meter TODO (instrucciones + precios + fórmulas + estructura JSON) en un único System Instruction. Esto elimina el riesgo de RAG miss.

---

## Paso a paso

### 1. Ir a Google AI Studio
- URL: https://aistudio.google.com
- Login con cuenta Google

### 2. Crear nuevo Prompt / Chat
- Click en **"Create new"** → **"Chat prompt"**

### 3. Configurar modelo
- **Model**: `Gemini 2.0 Flash` (rápido y preciso) o `Gemini 2.0 Pro` (más razonamiento)
- **Temperature**: `0.2` (baja — queremos precisión en precios, no creatividad)
- **Top P**: `0.8`
- **Top K**: `40`
- **Max output tokens**: `8192`
- **Safety settings**: Default

### 4. System Instructions
- Copiar TODO el contenido de `SYSTEM_INSTRUCTION.md` en el campo "System instructions"
- Este archivo contiene:
  - Rol y personalidad
  - Flujo de cotización (8 pasos)
  - Tabla completa de precios (paneles, accesorios, fijaciones)
  - Fórmulas de cálculo
  - Estructura JSON de salida
  - Validaciones obligatorias
  - Datos fijos de empresa

### 5. Adjuntar archivos (opcional pero recomendado)
- Subir `EJEMPLO_COTIZACION.json` como ejemplo de referencia
- Subir `TABLA_PRECIOS_COMPLETA.csv` como backup de datos

### 6. Probar con casos de test
Ver sección "Casos de prueba" abajo.

### 7. Publicar como App (opcional)
- Google AI Studio permite generar una API key para integrar via API
- También se puede exportar como Vertex AI Agent

---

## Casos de prueba

### Test 1: ISOROOF simple a madera
**Input:** "Necesito 4 paneles ISOROOF 80mm de 5 metros, fijación a madera"

**Verificar:**
- precio_m2 = 51.73
- costo_m2 = 44.98
- ancho_util_m = 1.00
- Sistema caballetes (sin varilla ni tuercas)
- Advertencia: largo 5m > autoportancia 4m

### Test 2: ISODEC a metal
**Input:** "Cotizar ISODEC EPS 150mm, 10 paneles de 7 metros, fijación a metal"

**Verificar:**
- precio_m2 = 42.48, costo_m2 = 36.94
- ancho_util_m = 1.12
- Sistema varilla 3/8" + tuercas
- Sin advertencia (7m < 7.5m autoportancia)

### Test 3: Autoportancia
**Input:** "ISOROOF 30mm de 4 metros"

**Verificar:**
- Debe advertir: 4m > 2.8m de autoportancia

### Test 4: Cotización completa con JSON
**Input:** Confirmar cualquier cotización y pedir el JSON

**Verificar:**
- Estructura correcta según template
- cotizacion.numero = null
- Todos los campos de costo presentes
- Comentarios con autoportancia correcta

### Test 5: Desde área (nuevo en v6)
**Input:** "Techo de 6x4 metros en ISODEC 100mm"

**Verificar:**
- Convierte: 4 paneles de 6m (ROUNDUP(4/1.12) = 4)
- O 6 paneles de 4m según orientación
- Pregunta orientación si no está claro

---

## Mantenimiento

### Actualizar precios
Editar la sección "PRECIOS Y COSTOS" dentro de `SYSTEM_INSTRUCTION.md` y pegar nuevamente en AI Studio.

### Agregar producto nuevo
1. Agregar a la tabla de precios en `SYSTEM_INSTRUCTION.md`
2. Agregar autoportancia si aplica
3. Agregar nombre estándar
4. Re-pegar en AI Studio

### Diferencia con OpenAI
En OpenAI, los precios están en un archivo Knowledge separado. En Google AI Studio, todo está en el System Instruction. Esto significa que actualizar precios requiere re-pegar todo el System Instruction, pero a cambio el modelo SIEMPRE tiene acceso a todos los datos.

---

## Archivos incluidos en este paquete

| Archivo | Propósito | Dónde va |
|---------|-----------|----------|
| `SYSTEM_INSTRUCTION.md` | Instrucciones completas para Gemini | Campo "System instructions" de AI Studio |
| `EJEMPLO_COTIZACION.json` | JSON de ejemplo (cotización real) | Adjunto en el chat (opcional) |
| `TABLA_PRECIOS_COMPLETA.csv` | Precios en formato CSV | Adjunto en el chat (opcional) |
| `README_IMPLEMENTACION.md` | Esta guía | Referencia (no subir) |
