"""
OpenAI-powered write plan generator for Panelin Sheets Orchestrator.

Uses the Responses API with Structured Outputs (strict JSON schema)
to generate a validated write plan from:
  - Template metadata (allowlist, hints, sheet structure)
  - Current sheet snapshot (read via batchGet)
  - User payload (client data, product selections, quantities)
  - Panelin business rules (autoportancia, BOM, pricing)

The plan is a list of {range, values} pairs, each validated against
the template's writes_allowlist before execution.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from openai import OpenAI

from .audit import audit_openai_call
from .config import Settings
from .models import WritePlan

logger = logging.getLogger("panelin.sheets.planner")


WRITEPLAN_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "job_id": {"type": "string"},
        "version": {"type": "string"},
        "writes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "range": {"type": "string"},
                    "values": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
                "required": ["range", "values"],
            },
        },
        "computed": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "panels_needed": {"type": "string"},
                "supports": {"type": "string"},
                "area_m2": {"type": "string"},
                "fixing_points": {"type": "string"},
            },
            "required": ["panels_needed", "supports", "area_m2", "fixing_points"],
        },
        "notes": {"type": "string"},
    },
    "required": ["job_id", "version", "writes", "computed", "notes"],
}


SYSTEM_PROMPT = """\
Sos el planificador de escritura para planillas de cotización de Panelin (BMC Uruguay).
Tu trabajo es generar un plan de escritura JSON para Google Sheets basado en el payload del usuario y la estructura del template.

## Reglas estrictas

1. **Solo rangos de la allowlist**: Únicamente podés usar rangos que aparezcan en `writes_allowlist`. Si un dato no tiene rango permitido, NO lo escribas.
2. **Sin fórmulas**: Nunca escribas valores que empiecen con `=`. Solo valores planos (texto, números, fechas).
3. **Sin inventar datos**: Si falta información en el payload, dejá `writes` vacío y explicá en `notes`.
4. **Formato de fecha**: Usar `YYYY-MM-DD` o `DD/MM/YYYY` según la locale de la planilla.
5. **Números**: Usar punto decimal (`.`), sin separador de miles.
6. **IVA incluido**: Todos los precios de Panelin incluyen 22% IVA. NO agregar IVA.
7. **Redondeo cantidades**: Cantidades de paneles, perfiles y fijaciones SIEMPRE redondeadas hacia arriba (ceil).
8. **Moneda**: Siempre USD.

## Contexto de productos Panelin

### Familias de paneles
- **ISODEC EPS**: Techos/cubiertas. Espesores: 100, 150, 200, 250mm.
- **ISODEC PIR**: Techos resistentes al fuego. Espesores: 50, 80, 120mm.
- **ISOROOF 3G**: Techos livianos. Espesores: 30, 50, 80mm.
- **ISOPANEL EPS**: Paredes/fachadas. Espesores: 50, 100, 150, 200, 250mm.
- **ISOWALL PIR**: Fachadas resistentes al fuego. Espesores: 50, 80mm.
- **ISOFRIG PIR**: Cámaras frigoríficas. Espesores: 40-200mm.

### Autoportancia (luz máxima entre apoyos)
ISODEC EPS: 100mm→5.5m, 150mm→7.5m, 200mm→9.1m, 250mm→10.4m
ISODEC PIR: 50mm→3.5m, 80mm→5.5m, 120mm→7.6m
ISOROOF 3G: 30mm→2.8m, 50mm→3.3m, 80mm→4.0m
ISOPANEL EPS: 50mm→3.0m, 100mm→5.5m, 150mm→7.5m, 200mm→9.1m

### Fórmulas de BOM
- Paneles necesarios: ROUNDUP(ancho_total / ancho_útil)
- Apoyos: ROUNDUP((largo / autoportancia) + 1), mínimo 2
- Puntos de fijación (techo): ROUNDUP(((paneles × apoyos) × 2) + (largo × 2 / 2.5))
- Puntos de fijación (pared): ROUNDUP((paneles × apoyos) × 2)
- Varillas 3/8": ROUNDUP(puntos_fijación / 4)
- Tuercas (metal): puntos_fijación × 2; (hormigón): puntos_fijación × 1

### Accesorios
- Gotero frontal: ROUNDUP((paneles × ancho_útil) / 3.03)
- Gotero lateral: ROUNDUP((largo × 2) / 3.0)
- Silicona: ROUNDUP(perímetro / 8) tubos
- Butilo: ROUNDUP(perímetro / 22.5) rollos

## Instrucciones de salida

Completá el JSON con:
- `job_id`: el mismo que recibiste
- `version`: "1"
- `writes`: lista de {range, values} usando solo rangos permitidos
- `computed`: cálculos intermedios que hayas realizado (paneles, apoyos, área, fijaciones)
- `notes`: explicación de lo que hiciste, datos faltantes, o advertencias
"""


def build_write_plan(
    *,
    settings: Settings,
    job_id: str,
    mapping: Dict[str, Any],
    sheet_snapshot: Dict[str, Any],
    payload: Dict[str, Any],
    bom_summary: Optional[Dict[str, Any]] = None,
) -> WritePlan:
    """
    Call OpenAI Responses API with Structured Outputs to generate a write plan.

    Args:
        settings: Application settings.
        job_id: Unique job identifier.
        mapping: Template mapping (allowlist, hints, read_ranges).
        sheet_snapshot: Current sheet values from batchGet.
        payload: User-provided data to fill.
        bom_summary: Pre-computed BOM data from validators (optional).

    Returns:
        WritePlan validated against the JSON schema.
    """
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY no configurado (usar Secret Manager en Cloud Run)."
        )

    client = OpenAI(api_key=settings.openai_api_key)

    template_context = {
        "template_id": mapping.get("template_id"),
        "sheet_name": mapping.get("sheet_name"),
        "writes_allowlist": mapping.get("writes_allowlist", []),
        "hints": mapping.get("hints", {}),
    }

    user_input: Dict[str, Any] = {
        "job_id": job_id,
        "template": template_context,
        "sheet_snapshot": sheet_snapshot,
        "payload": payload,
    }

    if bom_summary:
        user_input["bom_precomputed"] = bom_summary

    t0 = time.monotonic()

    resp = client.responses.create(
        model=settings.openai_model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(user_input, ensure_ascii=False),
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "panelin_sheet_writeplan",
                "schema": WRITEPLAN_SCHEMA,
                "strict": True,
            }
        },
        temperature=settings.openai_temperature,
        max_output_tokens=settings.openai_max_tokens,
    )

    elapsed_ms = round((time.monotonic() - t0) * 1000, 2)

    usage = getattr(resp, "usage", None)
    audit_openai_call(
        job_id=job_id,
        model=settings.openai_model,
        input_tokens=getattr(usage, "input_tokens", None) if usage else None,
        output_tokens=getattr(usage, "output_tokens", None) if usage else None,
        duration_ms=elapsed_ms,
    )

    out_text = getattr(resp, "output_text", None)
    if not out_text:
        raise RuntimeError(
            "OpenAI no devolvió output_text. Revisar versión del SDK."
        )

    data = json.loads(out_text)
    return WritePlan.model_validate(data)
