# Panelin SOP de consolidación (sin backend)

Este documento define comandos operativos internos para control de contexto y continuidad.

## Comandos soportados

- `/estado`: resume objetivo actual, riesgos y próximos pasos.
- `/checkpoint`: guarda un resumen de avances, decisiones y pendientes.
- `/consolidar`: integra contexto disperso en un único estado operativo.
- `/evaluar_ventas`: dispara evaluación técnica/comercial del vendedor según historial.
- `/entrenar`: genera plan de entrenamiento por brechas detectadas.
- `/pdf`: prepara datos para generación de cotización en PDF.

## Flujo recomendado

1. Identificar objetivo y faltantes del cliente.
2. Ejecutar `/estado` para verificar contexto.
3. Usar `/checkpoint` antes de cambios relevantes.
4. Aplicar `/consolidar` cuando haya múltiples cotizaciones o iteraciones.
5. Cerrar con checklist de consistencia (precios Nivel 1, fórmulas KB, IVA incluido).

## Reglas

- No inventar datos fuera de KB.
- Priorizar archivos Nivel 1 ante conflictos.
- Mantener trazabilidad de cambios entre checkpoint y consolidación.
