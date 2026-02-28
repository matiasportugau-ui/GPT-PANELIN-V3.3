# BMC URUGUAY — FÓRMULAS DE CÁLCULO DE CANTIDADES

---

## 1. CÁLCULO DE PANELES

### Precio total por fila
```
TOTAL_LINEA = LARGO_m × ANCHO_UTIL_m × CANTIDAD × PRECIO_M2
```

### Total m² del presupuesto
```
TOTAL_M2 = Σ (LARGO_m × ANCHO_UTIL_m × CANTIDAD) para cada fila
```

### Ancho útil por producto
| Producto | Ancho útil |
|----------|------------|
| ISOROOF 3G / Plus / Foil / Colonial | 1.00m |
| ISODEC EPS / PIR | 1.12m |
| ISOPANEL EPS | 1.10m |
| ISOWALL PIR | 1.10m |
| ISOFRIG SL | 1.10m |

---

## 2. AUTOPORTANCIA Y APOYOS

### Tabla de autoportancia
| Producto | 30mm | 40mm | 50mm | 80mm | 100mm | 120mm | 150mm | 200mm | 250mm |
|----------|------|------|------|------|-------|-------|-------|-------|-------|
| ISOROOF 3G | 2.8m | 3.0m | 3.3m | 4.0m | — | — | — | — | — |
| ISOROOF Plus | — | — | — | 4.0m | — | — | — | — | — |
| ISOROOF Foil | 2.8m | — | 3.3m | — | — | — | — | — | — |
| ISODEC EPS | — | — | — | — | 5.5m | — | 7.5m | 9.1m | 10.4m |
| ISODEC PIR | — | — | 3.5m | 5.5m | — | 7.6m | — | — | — |

**NOTA:** ISOPANEL/ISOWALL/ISOFRIG son productos de pared — NO aplica autoportancia. La validación de autoportancia solo aplica para productos de techo (ISODEC/ISOROOF).

### Cálculo de apoyos intermedios
```
APOYOS = ROUNDUP((LARGO_PANEL / AUTOPORTANCIA) + 1)
```

Si LARGO > AUTOPORTANCIA → se necesitan apoyos intermedios (correas adicionales).

---

## 3. FACTORES DE DESPERDICIO

| Producto | Factor | Descripción |
|----------|--------|-------------|
| ISODEC EPS | 1.12 | 12% desperdicio |
| ISODEC PIR techo | 1.12 | 12% desperdicio |
| ISOROOF | 1.00 | Sin desperdicio adicional |
| ISOFRIG SL | 1.10 | 10% desperdicio |
| ISOFRIG Cámara (paredes) | 1.14 | 14% desperdicio |

---

## 4. FÓRMULAS DE ACCESORIOS

### Gotero Frontal
```
ML_FRENTE = CANTIDAD_PANELES × ANCHO_UTIL × FACTOR_DESPERDICIO
CANTIDAD_BARRAS = ROUNDUP(ML_FRENTE / LARGO_BARRA)
Largo estándar barra: 3.03m
```

### Gotero Lateral
```
CANTIDAD_BARRAS = ROUNDUP((LARGO_PANEL × 2) / LARGO_BARRA)
Largo estándar barra: 3.00m
```

### Cumbrera
```
ML_CUMBRERA = ANCHO_CUBIERTA_M
CANTIDAD_BARRAS = ROUNDUP(ML_CUMBRERA / 3.03)
Largo estándar barra: 3.03m (ISODEC) / 3.00m (ISOROOF)
Nota: si hay dos aguas, multiplicar por 2
```

### Perfil Aluminio 5852 (solo ISODEC)
```
CANTIDAD_BARRAS = ROUNDUP(((CANT × DESP × 2) + (LARGO × 2)) / 6.8)
Largo estándar barra: 6.80m
```

### Babeta (atornillar o empotrar)
```
ML_BABETA = (CANT × DESP) + (LARGO × 2)
CANTIDAD_BARRAS = ROUNDUP(ML_BABETA / 3.00)
Largo estándar barra: 3.00m
```

### Canalón
```
CANTIDAD_BARRAS = ROUNDUP(CANTIDAD_PANELES × FACTOR_DESPERDICIO / 3)
```

### Soporte de Canalón
```
ML_CANALON = CANT_BARRAS_CANALON × LARGO_BARRA_CANALON
SOPORTES = max(1, ROUNDUP(ML_CANALON / 3))
Regla: 1 soporte cada 3m de canalón, mínimo 1
```

---

## 5. FÓRMULAS DE FIJACIONES

### Silicona
```
POMOS = ROUNDUP(M2_TOTAL / 8)
M2_TOTAL incluye: paneles + perfiles + babetas
```

### Sistema Varilla (ISODEC/ISOPANEL a metal)

#### Puntos de fijación
```
PUNTOS = ((CANT_PANELES × APOYOS × 2) + (LARGO × 2 / 2.5))
```

#### Varillas roscadas
```
VARILLAS_METROS = ROUNDUP(PUNTOS / 4)
```

#### Tuercas
```
TUERCAS = PUNTOS × 2
```

#### Arandelas
```
ARANDELAS_CARROCERO = PUNTOS
ARANDELAS_PLANAS = PUNTOS
ARANDELAS_TORTUGA = PUNTOS
```

### Sistema Caballete (ISOROOF a madera)

#### Caballetes
```
CABALLETES = ROUNDUP((CANT × 3 × (LARGO/2.9 + 1)) + ((LARGO × 2) / 0.3))
```

#### Tornillos aguja / punta mecha
```
TORNILLOS_AGUJA = misma cantidad que CABALLETES
```

### Tornillos T1 (para accesorios, todos los sistemas)
```
TORNILLOS_T1 = TOTAL_BARRAS_PERFILES × 20
(20 tornillos por barra de perfil/accesorio)
```

---

## 6. LARGO MÁXIMO DE FABRICACIÓN

| Producto | Largo máximo |
|----------|-------------|
| ISODEC EPS | 14.0m |
| ISODEC PIR | 14.0m |
| ISOROOF 3G | 8.5m |
| ISOROOF Plus | 8.5m |
| ISOROOF Foil | 8.5m |
| ISOROOF Colonial | 8.5m |
| ISOPANEL EPS | 12.0m |
| ISOWALL PIR | 12.0m |
| ISOFRIG SL | 12.0m |

---

## 7. CÁLCULO DE TOTALES (lo hace el motor PDF, no el GPT)

```
SUBTOTAL = SUM(todas las líneas de paneles + accesorios + anclaje + traslado)
IVA = SUBTOTAL × 0.22
TOTAL_MATERIALES = SUBTOTAL + IVA
TOTAL_FINAL = TOTAL_MATERIALES
```

Para costeo interno:
```
COSTO_TOTAL = SUM(costo de cada línea)
MARGEN_$ = SUBTOTAL - COSTO_TOTAL
MARGEN_% = MARGEN_$ / COSTO_TOTAL × 100
```
