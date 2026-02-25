# BMC URUGUAY — ESTRUCTURA JSON PARA GENERADOR PDF v6

Este documento define la estructura JSON exacta que Panelín debe generar para alimentar el motor `panelin_pdf_v6.py`. El motor genera DOS documentos: PDF de cotización para el cliente y PDF interno de costeo con márgenes.

---

## ESTRUCTURA COMPLETA

```json
{
  "empresa": {
    "nombre": "BMC Uruguay",
    "email": "info@bmcuruguay.com.uy",
    "web": "www.bmcuruguay.com.uy",
    "telefono": "4222 4031",
    "ciudad": "Maldonado, Uy.",
    "logo_path": null,
    "contacto_dudas": "092 663 245",
    "banco_titular": "Metalog SAS",
    "banco_rut": "120403430012",
    "banco_cuenta": "110520638-00002",
    "banco_tipo": "Caja de Ahorro - BROU."
  },

  "cotizacion": {
    "numero": null,
    "fecha": "DD/MM/AAAA",
    "titulo": "NOMBRE DEL PRODUCTO PRINCIPAL",
    "validez_dias": 10,
    "imagen_path": null
  },

  "cliente": {
    "nombre": "NOMBRE COMPLETO DEL CLIENTE",
    "direccion": "DIRECCIÓN DE LA OBRA",
    "telefono": "TELÉFONO DE CONTACTO"
  },

  "paneles": [],
  "accesorios": [],
  "anclaje": [],

  "traslado": {
    "incluido": false,
    "costo": null,
    "costo_real": null,
    "nota": "Traslado sin cotizar"
  },

  "comentarios": []
}
```

---

## DETALLE DE CADA SECCIÓN

### empresa (FIJO — no modificar)
Estos datos son SIEMPRE iguales. Copiar tal cual en cada cotización.

### cotizacion
| Campo | Tipo | Descripción |
|-------|------|-------------|
| numero | null | Dejar en null, el sistema auto-genera (COT-YYYYMMDD-XXXX) |
| fecha | string | Fecha del día en formato DD/MM/AAAA |
| titulo | string | Nombre del producto principal. Ej: "Isoroof 80 mm", "Isodec EPS 150mm" |
| validez_dias | int | Siempre 10 |
| imagen_path | null | Ruta a imagen del producto si existe, sino null |

### cliente
| Campo | Tipo | Descripción |
|-------|------|-------------|
| nombre | string | Nombre completo del cliente |
| direccion | string | Dirección de la obra (no domicilio personal) |
| telefono | string | Teléfono o celular de contacto |

### paneles[] — DINÁMICO
Cada largo distinto es una fila separada, aunque sea el mismo producto. Un presupuesto puede tener 1 fila o 20 filas.

```json
{
  "nombre": "ISOROOF - Gris ó Terracota – 80mm",
  "seccion": "Paneles Aislantes 3G",
  "largo_m": 5.01,
  "cantidad": 3,
  "ancho_util_m": 1.0,
  "precio_m2": 51.73,
  "costo_m2": 44.98
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| nombre | string | Nombre completo con espesor y color |
| seccion | string | Categoría para agrupar: "Paneles Aislantes 3G", "Paneles ISODEC", "Paneles ISOPANEL", etc. |
| largo_m | float | Largo de cada panel en metros (con decimales) |
| cantidad | int | Cantidad de paneles de ese largo |
| ancho_util_m | float | Ancho útil: ISOROOF=1.00, ISODEC=1.12, ISOPANEL/ISOWALL=1.10 |
| precio_m2 | float | Precio de VENTA por m² (consultar KB_PRECIOS.md) |
| costo_m2 | float | Costo INTERNO por m² (consultar KB_PRECIOS.md) — para doc de costeo |

### accesorios[] — DINÁMICO
Solo incluir los accesorios que el proyecto NECESITA. No todos llevan canalón, babeta o limahoya.

```json
{
  "nombre": "Gotero Frontal Simple 80 mm",
  "largo_m": 3.03,
  "cantidad": 6,
  "precio_ml": 6.60,
  "costo_ml": 4.31
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| nombre | string | Nombre del accesorio con medida si aplica |
| largo_m | float | Largo de cada barra/pieza en metros |
| cantidad | int | Cantidad de barras (usar ROUNDUP en fórmulas) |
| precio_ml | float | Precio de VENTA por metro lineal |
| costo_ml | float | Costo INTERNO por metro lineal — si no se conoce, usar PVP/1.20 como estimación |

### anclaje[] — DINÁMICO
Varía completamente según sistema de fijación (metal vs madera) y tipo de panel.

```json
{
  "nombre": "Silicona Neutra (Pomo)",
  "especificacion": "400 g.",
  "cantidad": 24,
  "precio_unit": 6.08,
  "costo_real": 2.42
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| nombre | string | Nombre del ítem |
| especificacion | string | Medida, peso, tamaño. Si no aplica, string vacío "" |
| cantidad | int o float | Cantidad total de unidades |
| precio_unit | float | Precio de VENTA unitario |
| costo_real | float | Costo INTERNO real por unidad — para doc de costeo |

### traslado
```json
{
  "incluido": false,
  "costo": null,
  "costo_real": null,
  "nota": "Traslado sin cotizar"
}
```

- Si se cotiza flete: `incluido: true`, `costo: VALOR`, `costo_real: COSTO_REAL`
- Si no se cotiza: `incluido: false`, `costo: null`, `nota: "Traslado sin cotizar"`

### comentarios[] — LISTA ESTÁNDAR
Usar esta lista base. El ÚNICO campo variable es la autoportancia en el primer comentario (ajustar según espesor cotizado).

```json
[
  "Ancho útil paneles de Cubierta = 1 m. Autoportancia de techo X m.",
  "<b>Oferta válida por 10 días a partir de la fecha.</b>",
  "Pendiente mínima 7%.",
  "<b>Sujeto a cambios según fábrica.</b>",
  "<b>Entrega de 7 a 45 días, dependemos de producción.</b>",
  "<b>Incluye descuentos de Pago al Contado. Seña del 60% (al confirmar). Saldo del 40% (previo a retiro de fábrica).</b>",
  "<b>Con tarjeta de crédito y en cuotas, sería en $ y a través de Mercado Pago con un recargo de 11,9% (comisión MP).</b>",
  "Retiro sin cargo en Planta Industrial de Bromyros S.A. (Colonia Nicolich, Canelones)",
  "<b>BMC no asume responsabilidad por fallas producidas por no respetar la autoportancia sugerida.</b>",
  "<b>No incluye descarga del material. Se requieren 2 personas.</b>",
  "Opcional: Costo descarga $1500 + IVA / H. Únicamente en ciudad de Maldonado.",
  "Al aceptar esta cotización confirma haber revisado el contenido de la misma en cuanto a medidas, cantidades, colores, valores y tipo de producto.",
  "<b>Nuestro asesoramiento es una guía, en ningún caso sustituye el trabajo profesional de Arq. o Ing.</b>",
  "Al momento de recibir el material corroborar el estado del mismo. Una vez recibido, no aceptamos devolución."
]
```

**Notas sobre comentarios:**
- Ajustar "Autoportancia de techo X m." al valor real del espesor cotizado
- Ajustar "Ancho útil paneles de Cubierta = 1 m." si el producto es ISODEC (1.12m) o ISOPANEL (1.10m)
- Si el producto es para pared (ISOPANEL/ISOWALL), eliminar menciones de pendiente y autoportancia
- Los tags `<b>` son HTML válido — el motor PDF los interpreta como negrita

---

## SECCIONES VÁLIDAS PARA "seccion" EN PANELES

| Producto | Valor de "seccion" |
|----------|--------------------|
| ISOROOF 3G / Plus / Foil | "Paneles Aislantes 3G" |
| ISODEC EPS | "Paneles ISODEC EPS" |
| ISODEC PIR | "Paneles ISODEC PIR" |
| ISOPANEL EPS | "Paneles ISOPANEL" |
| ISOWALL PIR | "Paneles ISOWALL" |
| ISOFRIG SL | "Paneles ISOFRIG" |

---

## NOMBRES ESTÁNDAR PARA PRODUCTOS EN JSON

### Paneles
- `"ISOROOF - Gris ó Terracota – 80mm"`
- `"ISOROOF - Blanco – 50mm"`
- `"ISODEC EPS - 100mm"`
- `"ISODEC PIR - 80mm"`
- `"ISOPANEL EPS - 100mm"`
- `"ISOWALL PIR - 80mm"`
- `"ISOFRIG SL - 80mm"`

### Accesorios ISOROOF
- `"Gotero Frontal Simple XX mm"` (XX = espesor)
- `"Gotero Frontal con Greca XX mm"`
- `"Gotero Lateral XX mm"`
- `"Cumbrera Roof 3G"`
- `"Canalón Doble XXmm"`
- `"Soporte de Canalón"`
- `"Limahoya standar"`

### Accesorios ISODEC
- `"Gotero Frontal ISODEC XXXmm"` (XXX = espesor)
- `"Gotero Lateral ISODEC XXXmm"`
- `"Cumbrera ISODEC"`
- `"Babeta de Empotrar"`
- `"Babeta de Atornillar"`
- `"Canalón ISODEC Kit Completo"`
- `"Soporte de Canalón ISODEC"`
- `"Perfil Aluminio 5852 Anodizado"`

### Fijaciones
- `"Silicona Neutra (Pomo)"`
- `"Caballete Roof Gris o Terracota"`
- `"Tornillos / P. Aguja – P. Mecha"`
- `"Tornillos T1 ½"`
- `"Varilla Roscada 3/8\\""`
- `"Tuerca Galvanizada 3/8\\""`
- `"Arandela Carrocero"`
- `"Arandela Plana"`
- `"Arandela Polipropileno (Tortuga)"`
- `"Membrana Auto-adhesiva (bajo babeta)"`
- `"Espuma PUR Expansiva"`
- `"Taco Expansivo 3/8\\""`
- `"Remache POP"`
