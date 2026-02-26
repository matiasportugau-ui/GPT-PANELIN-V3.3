"""
Panelin Wolf API — Google Sheets Integration Routes
=====================================================
Reads/writes to the "Administrador de Cotizaciones" spreadsheet.
v1.0.0 — 2026-02-26
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger("panelin.sheets")

router = APIRouter(prefix="/sheets", tags=["Google Sheets"])

SPREADSHEET_ID = os.environ.get("SHEETS_SPREADSHEET_ID", "")
TAB_2026 = os.environ.get("SHEETS_TAB_2026", "Administrador de Cotizaciones 2026")
TAB_2025 = os.environ.get("SHEETS_TAB_2025", "2.0 -  Administrador de Cotizaciones")

COLUMN_MAP = {
      "asignado": 1, "estado": 2, "fecha": 3, "cliente": 4,
      "origen": 5, "telefono": 6, "direccion": 7, "consulta": 8, "comentarios": 9,
}
VALID_ESTADOS = ["Pendiente", "Asignado", "Enviado", "Listo"]
VALID_ORIGENES = ["WA", "ML", "EM", "CL", "AM", "LO", "LL", "IN", "FB", "EE", "EC"]
VALID_ASIGNADOS = ["MA", "MO", "RA", "SPRT", "TIN", "Ref."]

_gc = None
_spreadsheet = None


def _get_spreadsheet():
      global _gc, _spreadsheet
      if _spreadsheet is None:
                try:
                              import gspread
                              from google.auth import default as google_auth_default
                              creds, project = google_auth_default(
                                  scopes=["https://www.googleapis.com/auth/spreadsheets"]
                              )
                              _gc = gspread.authorize(creds)
                              if not SPREADSHEET_ID:
                                                raise ValueError("SHEETS_SPREADSHEET_ID environment variable not set")
                                            _spreadsheet = _gc.open_by_key(SPREADSHEET_ID)
                              logger.info(f"Connected to spreadsheet: {_spreadsheet.title}")
except Exception as e:
            logger.error(f"Failed to connect to Google Sheets: {e}")
            raise HTTPException(status_code=503, detail=f"Sheets connection failed: {str(e)}")
    return _spreadsheet


def _get_worksheet(tab_name: str = None):
      ss = _get_spreadsheet()
      tab = tab_name or TAB_2026
      try:
                return ss.worksheet(tab)
except Exception as e:
        logger.error(f"Tab '{tab}' not found: {e}")
        raise HTTPException(status_code=404, detail=f"Tab '{tab}' not found")


def _row_to_dict(row_values: list, row_number: int) -> dict:
      return {
                "row_number": row_number,
                "asignado": row_values[0] if len(row_values) > 0 else "",
                "estado": row_values[1] if len(row_values) > 1 else "",
                "fecha": row_values[2] if len(row_values) > 2 else "",
                "cliente": row_values[3] if len(row_values) > 3 else "",
                "origen": row_values[4] if len(row_values) > 4 else "",
                "telefono": row_values[5] if len(row_values) > 5 else "",
                "direccion": row_values[6] if len(row_values) > 6 else "",
                "consulta": row_values[7] if len(row_values) > 7 else "",
                "comentarios": row_values[8] if len(row_values) > 8 else "",
      }


class ConsultationCreate(BaseModel):
      cliente: str = Field(..., description="Client name")
      origen: str = Field(..., description="Channel: WA, ML, EM, CL, AM, LO, LL, IN, FB, EE, EC")
      consulta: str = Field(..., description="Technical description")
      telefono: Optional[str] = Field(None)
      direccion: Optional[str] = Field(None)
      asignado: Optional[str] = Field(None)
      fecha: Optional[str] = Field(None, description="DD-MM")
      comentarios: Optional[str] = Field(None)


class QuotationLineAdd(BaseModel):
      row_number: Optional[int] = Field(None)
      cliente: str = Field(...)
      consulta: str = Field(...)
      estado: str = Field("Enviado")
      comentarios: Optional[str] = Field(None)
      origen: Optional[str] = Field(None)
      telefono: Optional[str] = Field(None)
      direccion: Optional[str] = Field(None)
      asignado: Optional[str] = Field(None)


class RowUpdate(BaseModel):
      row_number: int = Field(...)
      estado: Optional[str] = Field(None)
      asignado: Optional[str] = Field(None)
      comentarios: Optional[str] = Field(None)
      consulta: Optional[str] = Field(None)
      telefono: Optional[str] = Field(None)
      direccion: Optional[str] = Field(None)


@router.get("/consultations")
async def read_consultations(
      tab: Optional[str] = Query(None),
      estado: Optional[str] = Query(None),
      origen: Optional[str] = Query(None),
      asignado: Optional[str] = Query(None),
      cliente: Optional[str] = Query(None),
      fecha: Optional[str] = Query(None),
      limit: int = Query(50, ge=1, le=200),
      skip_header: int = Query(2, description="Header rows to skip")
):
      ws = _get_worksheet(tab)
      all_rows = ws.get_all_values()
      results = []
      for i, row in enumerate(all_rows):
                row_num = i + 1
                if row_num <= skip_header:
                              continue
                          if not any(cell.strip() for cell in row[:8]):
                                        continue
                                    entry = _row_to_dict(row, row_num)
                if estado and entry["estado"].strip() != estado.strip():
                              continue
                          if origen and entry["origen"].strip().upper() != origen.strip().upper():
                                        continue
                                    if asignado and entry["asignado"].strip().upper() != asignado.strip().upper():
                                                  continue
                                              if cliente and cliente.lower() not in entry["cliente"].lower():
                                                            continue
                                                        if fecha and entry["fecha"].strip() != fecha.strip():
                                                                      continue
                                                                  results.append(entry)
                if len(results) >= limit:
                              break
                      return {"tab": tab or TAB_2026, "total_results": len(results),
                    "filters_applied": {k: v for k, v in {"estado": estado, "origen": origen,
                    "asignado": asignado, "cliente": cliente, "fecha": fecha}.items() if v},
                    "consultations": results}


@router.post("/consultations")
async def add_consultation(data: ConsultationCreate):
      if data.origen and data.origen.upper() not in VALID_ORIGENES:
                raise HTTPException(400, f"Invalid origen '{data.origen}'. Valid: {VALID_ORIGENES}")
            ws = _get_worksheet()
    fecha = data.fecha or datetime.now(timezone.utc).strftime("%d-%m")
    new_row = [data.asignado or "", "Pendiente", fecha, data.cliente,
                              data.origen.upper() if data.origen else "", data.telefono or "",
                              data.direccion or "", data.consulta, data.comentarios or ""]
    all_rows = ws.get_all_values()
    last_data_row = 2
    for i, row in enumerate(all_rows):
              if i < 2:
                            continue
                        if len(row) > 3 and row[3].strip():
                                      last_data_row = i + 1
                              append_row = last_data_row + 1
    ws.update(f"A{append_row}:I{append_row}", [new_row])
    logger.info(f"Added consultation at row {append_row}: {data.cliente}")
    return {"success": True, "row_number": append_row,
                        "message": f"Consultation added for '{data.cliente}' at row {append_row}",
                        "data": _row_to_dict(new_row, append_row)}


@router.post("/quotation_line")
async def add_quotation_line(data: QuotationLineAdd):
      ws = _get_worksheet()
    fecha = datetime.now(timezone.utc).strftime("%d-%m")
    if data.row_number:
              row_num = data.row_number
        current = ws.row_values(row_num)
        updates = {}
        if data.estado:
                      updates[f"B{row_num}"] = data.estado
                  if data.comentarios:
                                existing = current[8] if len(current) > 8 else ""
                                sep = " | " if existing else ""
                                updates[f"I{row_num}"] = f"{existing}{sep}[Cotizado {fecha}] {data.comentarios}"
                            if data.asignado:
                                          updates[f"A{row_num}"] = data.asignado
                                      for cell, value in updates.items():
                                                    ws.update_acell(cell, value)
                                                return {"success": True, "action": "updated", "row_number": row_num,
                                                                        "message": f"Row {row_num} updated for '{data.cliente}'"}
else:
        new_row = [data.asignado or "", data.estado or "Enviado", fecha, data.cliente,
                                      (data.origen or "").upper(), data.telefono or "", data.direccion or "",
                                      data.consulta, data.comentarios or ""]
        all_rows = ws.get_all_values()
        last_data_row = 2
        for i, row in enumerate(all_rows):
                      if i < 2:
                                        continue
                                    if len(row) > 3 and row[3].strip():
                                                      last_data_row = i + 1
                                              append_row = last_data_row + 1
        ws.update(f"A{append_row}:I{append_row}", [new_row])
        return {"success": True, "action": "appended", "row_number": append_row,
                                "message": f"Quotation line added for '{data.cliente}' at row {append_row}"}


@router.patch("/update_row")
async def update_row(data: RowUpdate):
      ws = _get_worksheet()
    try:
              current = ws.row_values(data.row_number)
        if not current or not any(cell.strip() for cell in current[:8]):
                      raise HTTPException(404, f"Row {data.row_number} is empty")
except HTTPException:
        raise
except Exception as e:
        raise HTTPException(400, f"Error reading row {data.row_number}: {str(e)}")
    updates = {}
    if data.estado:
              if data.estado not in VALID_ESTADOS:
                            raise HTTPException(400, f"Invalid estado '{data.estado}'. Valid: {VALID_ESTADOS}")
                        updates[f"B{data.row_number}"] = data.estado
    if data.asignado:
              updates[f"A{data.row_number}"] = data.asignado
    if data.consulta:
              updates[f"H{data.row_number}"] = data.consulta
    if data.telefono:
              updates[f"F{data.row_number}"] = data.telefono
    if data.direccion:
              updates[f"G{data.row_number}"] = data.direccion
    if data.comentarios:
              updates[f"I{data.row_number}"] = data.comentarios
    if not updates:
              raise HTTPException(400, "No fields to update")
    for cell, value in updates.items():
              ws.update_acell(cell, value)
    return {"success": True, "row_number": data.row_number,
                        "fields_updated": list(updates.keys())}


@router.get("/row/{row_number}")
async def get_row(row_number: int, tab: Optional[str] = None):
      ws = _get_worksheet(tab)
    try:
              values = ws.row_values(row_number)
        if not values or not any(cell.strip() for cell in values[:8]):
                      raise HTTPException(404, f"Row {row_number} is empty")
        return _row_to_dict(values, row_number)
except HTTPException:
        raise
except Exception as e:
        raise HTTPException(400, f"Error reading row: {str(e)}")


@router.get("/search")
async def search_clients(
      q: str = Query(..., description="Search query"),
      tab: Optional[str] = None,
      limit: int = Query(20, ge=1, le=100)
):
      ws = _get_worksheet(tab)
    all_rows = ws.get_all_values()
    q_lower = q.lower()
    results = []
    for i, row in enumerate(all_rows):
              if i < 2:
                            continue
                        if not any(cell.strip() for cell in row[:8]):
                                      continue
                                  cliente = row[3].lower() if len(row) > 3 else ""
        consulta = row[7].lower() if len(row) > 7 else ""
        if q_lower in cliente or q_lower in consulta:
                      results.append(_row_to_dict(row, i + 1))
            if len(results) >= limit:
                              break
                  return {"query": q, "total_results": len(results), "results": results}


@router.get("/stats")
async def get_sheet_stats(tab: Optional[str] = None):
      ws = _get_worksheet(tab)
    all_rows = ws.get_all_values()
    stats = {"total_rows": 0, "by_estado": {}, "by_origen": {}, "by_asignado": {}}
    for i, row in enumerate(all_rows):
              if i < 2:
                            continue
                        if not any(cell.strip() for cell in row[:8]):
                                      continue
                                  stats["total_rows"] += 1
        estado = row[1].strip() if len(row) > 1 else "unknown"
        origen = row[4].strip() if len(row) > 4 else "unknown"
        asig = row[0].strip() if len(row) > 0 else "unknown"
        stats["by_estado"][estado] = stats["by_estado"].get(estado, 0) + 1
        if origen:
                      stats["by_origen"][origen] = stats["by_origen"].get(origen, 0) + 1
        if asig:
                      stats["by_asignado"][asig] = stats["by_asignado"].get(asig, 0) + 1
    return stats
