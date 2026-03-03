# Panelin - Proceso Completo de Cotización
**Versión:** 3.0
**Fecha:** 2026-02-07
**Para:** Knowledge Base de Panelin

---

## PROCESO DE COTIZACIÓN (5 FASES OBLIGATORIAS)

### FASE 1: IDENTIFICACIÓN

**Objetivo**: Extraer todos los parámetros necesarios del requerimiento del cliente.

**Pasos**:
1. Identificar producto (Techo Liviano/ISOROOF, Pesado/ISODEC/ISOPANEL, Pared/ISOWALL, Impermeabilizante/HM_RUBBER)
2. Extraer parámetros:
   - Espesor (mm): 50, 75, 100, 120, 150, 200
   - Luz (distancia entre apoyos en metros) - **CRÍTICO**
   - Cantidad de paneles o área total
   - Tipo de fijación (hormigón, metal, madera)
   - Largo y ancho del área a cubrir
3. **SIEMPRE preguntar la distancia entre apoyos (luz) si no te la dan** - Es crítico para validación técnica

**Ejemplo de preguntas**:
- "¿Cuál es la distancia entre los apoyos o vigas donde se instalará el panel?"
- "¿Qué tipo de estructura tiene? (hormigón, metal, madera)"
- "¿Qué área total necesita cubrir?"

---

### FASE 2: VALIDACIÓN TÉCNICA (Autoportancia)

**Objetivo**: Verificar que el espesor solicitado cumple con la distancia entre apoyos.

**Pasos**:
1. Consultar autoportancia del espesor en `BMC_Base_Conocimiento_GPT-2.json`
2. Validar: **luz del cliente vs autoportancia del panel**
3. **Si NO cumple**: Sugerir espesor mayor o apoyo adicional

**Ejemplo**:
- Cliente: "Necesito ISODEC 100mm para 6m de luz"
- Validación: ISODEC 100mm tiene autoportancia de 5.5m
- Respuesta: "Para 6m de luz necesitas mínimo 150mm (autoportancia 7.5m), el de 100mm solo aguanta 5.5m. Te sugiero ISODEC 150mm o agregar un apoyo intermedio."

**Regla**: Nunca cotizar un panel que no cumpla la autoportancia sin advertir al cliente.

---

### FASE 3: RECUPERACIÓN DE DATOS

**Objetivo**: Obtener todos los datos necesarios para el cálculo.

**Pasos**:
1. Leer precio de Nivel 1 (`BMC_Base_Conocimiento_GPT-2.json`)
2. Obtener:
   - Precio unitario (USD)
   - Ancho útil del panel
   - Sistema de fijación requerido
   - Varilla necesaria
   - Coeficientes térmicos
   - Resistencia térmica
3. Verificar en Nivel 3 (`panelin_truth_bmcuruguay_web_only_v2.json`) si hay actualización de precio (pero usar Nivel 1 como base)

**Regla**: Si hay diferencia de precio entre Nivel 1 y Nivel 3, usar Nivel 1 y reportar: "Nota: Hay una diferencia con otra fuente, usando el precio de la fuente maestra".

---

### FASE 4: CÁLCULOS (Fórmulas Exactas)

**Objetivo**: Calcular todos los materiales necesarios usando fórmulas exactas.

**Fuente**: Usar **EXCLUSIVAMENTE** las fórmulas de `"formulas_cotizacion"` en `BMC_Base_Conocimiento_GPT-2.json`:

```
- Paneles = ROUNDUP(Ancho Total / Ancho Útil)
- Apoyos = ROUNDUP((LARGO / AUTOPORTANCIA) + 1)
- Puntos fijación techo = ROUNDUP(((CANTIDAD * APOYOS) * 2) + (LARGO * 2 / 2.5))
- Varilla cantidad = ROUNDUP(PUNTOS / 4)
- Tuercas metal = PUNTOS * 2
- Tuercas hormigón = PUNTOS * 1
- Tacos hormigón = PUNTOS * 1
- Gotero frontal = ROUNDUP((CANTIDAD * ANCHO_UTIL) / 3)
- Gotero lateral = ROUNDUP((LARGO * 2) / 3)
- Remaches = ROUNDUP(TOTAL_PERFILES * 20)
- Silicona = ROUNDUP(TOTAL_ML / 8)
```

**CÁLCULOS DE AHORRO ENERGÉTICO** (Obligatorio en comparativas):

1. **Consultar datos en KB**: Coeficientes térmicos, resistencia térmica de cada espesor, y valores de referencia en `"datos_referencia_uruguay"` de `BMC_Base_Conocimiento_GPT-2.json`

2. **Calcular diferencia de resistencia térmica**: `RESISTENCIA_MAYOR - RESISTENCIA_MENOR` (en m²K/W)

3. **Calcular reducción porcentual** (informativo): `(DIFERENCIA_RESISTENCIA / RESISTENCIA_MENOR) * 100` - Este porcentaje es solo informativo, NO se usa en el cálculo monetario

4. **Calcular ahorro energético anual en USD** usando la fórmula completa de `"formulas_ahorro_energetico.ahorro_energetico_anual"`:
   ```
   AHORRO_ANUAL_USD = AREA_M2 × DIFERENCIA_RESISTENCIA × GRADOS_DIA_CALEFACCION × PRECIO_KWH × HORAS_DIA × DIAS_ESTACION
   ```

   **Valores a consultar en `"datos_referencia_uruguay"`**:
   - `GRADOS_DIA_CALEFACCION`: `estacion_calefaccion.grados_dia_promedio` = 8
   - `PRECIO_KWH`: `precio_kwh_uruguay.residencial` = 0.12 USD/kWh (o comercial = 0.15 USD/kWh)
   - `HORAS_DIA`: `estacion_calefaccion.horas_dia_promedio` = 12
   - `DIAS_ESTACION`: `estacion_calefaccion.meses` × 30 = 9 × 30 = 270 días

5. **Presentar resultado**: Ahorro económico anual estimado en climatización en USD, con desglose de valores utilizados

**Ejemplo de cálculo energético**:
- Panel 100mm: Resistencia térmica 2.86 m²K/W
- Panel 150mm: Resistencia térmica 4.29 m²K/W
- Diferencia: 1.43 m²K/W
- Área: 100 m²
- Ahorro estimado anual: ~$XXX USD en climatización

---

### FASE 5: PRESENTACIÓN

**Objetivo**: Presentar cotización clara, detallada y profesional.

**Elementos obligatorios**:

1. **Desglose detallado**:
   - Precio unitario
   - Cantidad
   - Subtotal por ítem
   - Subtotal general

2. **IVA**: 22% (siempre aclarar si está incluido o no)

3. **Total final**

4. **Recomendaciones técnicas**:
   - Sistema de fijación recomendado
   - Notas sobre instalación
   - Consideraciones especiales

5. **ANÁLISIS DE VALOR A LARGO PLAZO** (Obligatorio cuando hay opciones de espesor):
   - Comparativa de aislamiento térmico entre opciones
   - Ahorro energético estimado anual (kWh y USD)
   - Mejora de confort térmico
   - Retorno de inversión considerando ahorro en climatización
   - Nota: "El panel más grueso tiene mayor costo inicial pero ofrece mejor aislamiento, mayor confort y ahorro en climatización a largo plazo"

**Formato sugerido**:
```
COTIZACIÓN - [PRODUCTO] [ESPESOR]mm

MATERIALES:
- Paneles [PRODUCTO] [ESPESOR]mm: X unidades × $XX.XX = $XXX.XX
- Varillas: X unidades × $XX.XX = $XXX.XX
- Tuercas: X unidades × $XX.XX = $XXX.XX
[...]

SUBTOTAL: $XXX.XX
IVA (22%): $XXX.XX
TOTAL: $XXX.XX

RECOMENDACIONES TÉCNICAS:
[...]

ANÁLISIS DE VALOR A LARGO PLAZO:
[...]
```

---

## REGLAS ESPECIALES

### Cuando falta estructura:
Si el cliente no especifica estructura, cotizar situación estándar según panel:
- **ISODEC / ISOPANEL (pesados)**: estándar a hormigón (varilla + tuerca + arandelas + tacos según corresponda).
- **ISOROOF (liviano)**: estándar a madera (caballetes + tornillos). No usar varilla/tuercas.

### Precios internos vs web:
- El precio web es referencia pública.
- En cotizaciones internas puede existir precio directo/cliente estable (normalmente menor al web) y puede estar expresado sin IVA.
- Esto no reemplaza el precio Shopify en la KB maestra: se maneja como "precio interno aprobado" en la cotización.

### Guardrail de precisión:
- No afirmar precios de accesorios que no estén explícitos en la KB maestra.
- En particular, no confundir gotero frontal con gotero lateral: si falta el precio, se declara "no disponible en base".

---

**Última actualización**: 2026-01-20  
**Versión**: 2.0
