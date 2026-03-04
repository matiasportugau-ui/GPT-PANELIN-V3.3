"""
Panelin Agno — Google Sheets CRM Integration Tools

Wraps the existing Wolf API Sheets endpoints as Agno tools
so the agent can read/write to the CRM spreadsheet.
"""

from __future__ import annotations

import json
from typing import Optional


def sheets_read_consultations(
    estado: Optional[str] = None,
    cliente: Optional[str] = None,
    limit: int = 20,
) -> str:
    """Lee las consultas del CRM (Google Sheets) con filtros opcionales.

    Args:
        estado: Filtrar por estado (Pendiente, Enviado, Cerrado, etc.).
        cliente: Filtrar por nombre de cliente (búsqueda parcial).
        limit: Máximo de resultados (default 20).

    Returns:
        JSON con la lista de consultas encontradas.
    """
    import gspread
    from google.auth import default as gauth_default
    import os

    sheet_id = os.environ.get("SHEETS_SPREADSHEET_ID", "")
    tab = os.environ.get("SHEETS_TAB_2026", "Administrador de Cotizaciones 2026")

    if not sheet_id:
        return json.dumps({"error": "SHEETS_SPREADSHEET_ID no configurado"})

    try:
        creds, _ = gauth_default(scopes=["https://www.googleapis.com/auth/spreadsheets"])
        gc = gspread.authorize(creds)
        ss = gc.open_by_key(sheet_id)
        ws = ss.worksheet(tab)
        all_rows = ws.get_all_values()
    except Exception as e:
        return json.dumps({"error": f"No se pudo acceder a Sheets: {e}"})

    results = []
    for i, row in enumerate(all_rows):
        if i < 2 or not any(c.strip() for c in row[:8]):
            continue
        entry = {
            "fila": i + 1,
            "asignado": row[0] if len(row) > 0 else "",
            "estado": row[1] if len(row) > 1 else "",
            "fecha": row[2] if len(row) > 2 else "",
            "cliente": row[3] if len(row) > 3 else "",
            "origen": row[4] if len(row) > 4 else "",
            "telefono": row[5] if len(row) > 5 else "",
            "consulta": row[7] if len(row) > 7 else "",
        }
        if estado and entry["estado"].strip() != estado.strip():
            continue
        if cliente and cliente.lower() not in entry["cliente"].lower():
            continue
        results.append(entry)
        if len(results) >= limit:
            break

    return json.dumps({"total": len(results), "consultas": results}, ensure_ascii=False, indent=2)


def sheets_add_consultation(
    cliente: str,
    telefono: str = "",
    consulta: str = "",
    origen: str = "PANELIN",
    direccion: str = "",
) -> str:
    """Agrega una nueva consulta al CRM (Google Sheets).

    Args:
        cliente: Nombre del cliente.
        telefono: Teléfono de contacto.
        consulta: Descripción de la consulta.
        origen: Origen de la consulta (PANELIN, WEB, WHATSAPP, etc.).
        direccion: Dirección de la obra.

    Returns:
        JSON con confirmación y número de fila asignada.
    """
    import gspread
    from google.auth import default as gauth_default
    from datetime import datetime, timezone
    import os

    sheet_id = os.environ.get("SHEETS_SPREADSHEET_ID", "")
    tab = os.environ.get("SHEETS_TAB_ADMIN", "Admin.")

    if not sheet_id:
        return json.dumps({"error": "SHEETS_SPREADSHEET_ID no configurado"})

    try:
        creds, _ = gauth_default(scopes=["https://www.googleapis.com/auth/spreadsheets"])
        gc = gspread.authorize(creds)
        ss = gc.open_by_key(sheet_id)
        ws = ss.worksheet(tab)
    except Exception as e:
        return json.dumps({"error": f"No se pudo acceder a Sheets: {e}"})

    fecha = datetime.now(timezone.utc).strftime("%d-%m")
    new_row = ["", "Pendiente", fecha, cliente, origen.upper(), telefono, direccion, consulta, ""]

    all_rows = ws.get_all_values()
    last = 2
    for i, row in enumerate(all_rows):
        if i < 2:
            continue
        if len(row) > 3 and row[3].strip():
            last = i + 1
    row_num = last + 1

    ws.update(f"A{row_num}:I{row_num}", [new_row])
    return json.dumps({"ok": True, "fila": row_num, "cliente": cliente}, ensure_ascii=False)


def sheets_search(query: str, limit: int = 20) -> str:
    """Busca en el CRM por nombre de cliente o contenido de consulta.

    Args:
        query: Texto a buscar (mínimo 2 caracteres).
        limit: Máximo de resultados.

    Returns:
        JSON con resultados de búsqueda.
    """
    import gspread
    from google.auth import default as gauth_default
    import os

    sheet_id = os.environ.get("SHEETS_SPREADSHEET_ID", "")
    tab = os.environ.get("SHEETS_TAB_2026", "Administrador de Cotizaciones 2026")

    if not sheet_id:
        return json.dumps({"error": "SHEETS_SPREADSHEET_ID no configurado"})

    try:
        creds, _ = gauth_default(scopes=["https://www.googleapis.com/auth/spreadsheets"])
        gc = gspread.authorize(creds)
        ss = gc.open_by_key(sheet_id)
        ws = ss.worksheet(tab)
        all_rows = ws.get_all_values()
    except Exception as e:
        return json.dumps({"error": f"No se pudo acceder a Sheets: {e}"})

    q_lower = query.lower()
    results = []
    for i, row in enumerate(all_rows):
        if i < 2:
            continue
        cliente = row[3].lower() if len(row) > 3 else ""
        consulta = row[7].lower() if len(row) > 7 else ""
        if q_lower in cliente or q_lower in consulta:
            results.append({
                "fila": i + 1,
                "cliente": row[3] if len(row) > 3 else "",
                "estado": row[1] if len(row) > 1 else "",
                "consulta": row[7] if len(row) > 7 else "",
            })
            if len(results) >= limit:
                break

    return json.dumps({"query": query, "total": len(results), "resultados": results}, ensure_ascii=False, indent=2)
