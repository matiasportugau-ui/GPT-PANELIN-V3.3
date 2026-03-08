"""
sheet_mover.py — API endpoints para mover filas entre tabs de Cotizaciones
POST /cotizaciones/mover_esperando  — Mueve filas incompletas a Esperando Respuesta
POST /cotizaciones/scan_admin       — Scan completo: enviados + incompletos
"""

import os
import logging
from typing import List

import gspread
from fastapi import APIRouter, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

logger = logging.getLogger("panelin.mover")

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

SHEET_ID = os.getenv("SHEETS_COTIZACIONES_ID", "1RHJ1eQlCWMcWY5NKkHCsH5F5XavC9yebh97bruJilbs")

_gc = None
_spreadsheet = None


async def verify_api_key(api_key: str = Security(api_key_header)):
      import hmac
      expected = os.getenv("WOLF_API_KEY", "")
      if not expected:
          raise HTTPException(status_code=503, detail="WOLF_API_KEY not configured")
      if not api_key or not hmac.compare_digest(api_key, expected):
          raise HTTPException(status_code=401, detail="Invalid API Key")
      return api_key


def get_spreadsheet():
      global _gc, _spreadsheet
    if _spreadsheet:
              return _spreadsheet
          try:
                    _gc = gspread.service_account()
except Exception:
        from google.auth import default
        creds, _ = default(scopes=[
                      "https://www.googleapis.com/auth/spreadsheets",
                      "https://www.googleapis.com/auth/drive"
        ])
        _gc = gspread.authorize(creds)
    _spreadsheet = _gc.open_by_key(SHEET_ID)
    return _spreadsheet


ADMIN_TO_ESPERANDO = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 7: 7}
ESPERANDO_COLS = 8
HEADER_ROWS = 2
REQUIRED_FIELDS = {3: "Cliente", 5: "Telefono", 7: "Consulta"}


def _map_row(source, mapping, target_cols):
      target = [""] * target_cols
    for src_idx, dst_idx in mapping.items():
              if src_idx < len(source):
                            target[dst_idx] = source[src_idx]
                    return target


class MoveResult(BaseModel):
      action: str
    rows_moved: int
    details: List[str]


router = APIRouter(tags=["Sheet Mover"])


@router.post("/cotizaciones/mover_esperando", response_model=MoveResult)
async def mover_a_esperando(api_key: str = Depends(verify_api_key)):
      """Scan Admin for incomplete rows and move to Esperando Respuesta."""
    try:
              ss = get_spreadsheet()
        admin_ws = ss.worksheet("Admin.")
        esperando_ws = ss.worksheet("Esperando Respuesta")

        all_vals = admin_ws.get_all_values()
        rows_to_move = []

        for i, row in enumerate(all_vals):
                      if i < HEADER_ROWS:
                                        continue
                                    has_data = any(c.strip() for c in row[:10])
            if not has_data:
                              continue
                          estado = row[1].strip().lower() if len(row) > 1 else ""
            if estado in ("enviado", "confirmado", "cotizado"):
                              continue
                          missing = []
            for col_idx, field_name in REQUIRED_FIELDS.items():
                              if col_idx >= len(row) or not row[col_idx].strip():
                                                    missing.append(field_name)
                                            if missing:
                                                              rows_to_move.append((i, row, missing))

        if not rows_to_move:
                      return MoveResult(action="mover_esperando", rows_moved=0,
                                                                      details=["Todas las filas tienen datos completos."])

        details = []
        moved = 0
        for idx, row, missing in reversed(rows_to_move):
                      cliente = row[3].strip() if len(row) > 3 else "Sin nombre"
            esp_row = _map_row(row, ADMIN_TO_ESPERANDO, ESPERANDO_COLS)
            esp_row[1] = f"Pendiente (falta: {', '.join(missing)})"
            insert_at = HEADER_ROWS + 1
            esperando_ws.insert_row(esp_row, index=insert_at, value_input_option="USER_ENTERED")
            admin_ws.delete_rows(idx + 1)
            moved += 1
            details.append(f"'{cliente}' -> Esperando Respuesta (falta: {', '.join(missing)})")
            logger.info(f"Moved '{cliente}' to Esperando (missing: {missing})")

        return MoveResult(action="mover_esperando", rows_moved=moved, details=details)

except Exception as e:
        logger.error(f"Error moviendo a Esperando: {e}", exc_info=True)
        raise HTTPException(500, f"Error: {str(e)}")


@router.post("/cotizaciones/scan_admin", response_model=MoveResult)
async def scan_admin(api_key: str = Depends(verify_api_key)):
      """Full scan: move incompletos to Esperando Respuesta."""
    try:
              ss = get_spreadsheet()
        admin_ws = ss.worksheet("Admin.")
        esperando_ws = ss.worksheet("Esperando Respuesta")

        all_vals = admin_ws.get_all_values()
        to_esperando = []
        enviados_count = 0
        ok_count = 0

        for i, row in enumerate(all_vals):
                      if i < HEADER_ROWS:
                                        continue
                                    has_data = any(c.strip() for c in row[:10])
            if not has_data:
                              continue
            estado = row[1].strip().lower() if len(row) > 1 else ""
            if estado == "enviado":
                              enviados_count += 1
                continue
            if estado in ("confirmado", "cotizado"):
                              continue
            missing = []
            for col_idx, field_name in REQUIRED_FIELDS.items():
                              if col_idx >= len(row) or not row[col_idx].strip():
                                                    missing.append(field_name)
                                            if missing:
                                                              to_esperando.append((i, row, missing))
else:
                ok_count += 1

        details = []
        moved = 0

        if enviados_count > 0:
                      details.append(f"Nota: {enviados_count} filas con Estado=Enviado (trigger automatico las mueve)")

        for idx, row, missing in reversed(to_esperando):
                      cliente = row[3].strip() if len(row) > 3 else "Sin nombre"
            esp_row = _map_row(row, ADMIN_TO_ESPERANDO, ESPERANDO_COLS)
            esp_row[1] = f"Pendiente (falta: {', '.join(missing)})"
            esperando_ws.insert_row(esp_row, index=HEADER_ROWS + 1, value_input_option="USER_ENTERED")
            admin_ws.delete_rows(idx + 1)
            moved += 1
            details.append(f"Movido: '{cliente}' -> Esperando (falta: {', '.join(missing)})")

        if moved == 0 and enviados_count == 0:
                      details.append(f"Admin limpio: {ok_count} filas completas, sin incompletos.")

        return MoveResult(action="scan_admin", rows_moved=moved, details=details)

except Exception as e:
        logger.error(f"Error en scan: {e}", exc_info=True)
        raise HTTPException(500, f"Error: {str(e)}")
