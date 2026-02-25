"""
Panelin API - Vercel Serverless Entrypoint
============================================

Minimal FastAPI application for Vercel deployment.
Exposes health check and Panelin v4.0 quotation engine endpoints.
"""

import sys
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

app = FastAPI(
    title="Panelin API",
    description="BMC Uruguay - Panelin Quotation Engine v4.0",
    version="4.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "service": "Panelin API",
        "version": "4.0.0",
        "status": "ok",
        "engine": "panelin_v4",
    }


@app.get("/api/health")
async def health():
    return {"status": "healthy", "version": "4.0.0"}


@app.post("/api/quote")
async def quote(payload: dict):
    """Process a quotation request through the Panelin v4.0 engine.

    Body: {"text": "Isodec 100 mm / 6 paneles...", "client_name": "...", "client_location": "..."}
    """
    try:
        from panelin_v4.engine.quotation_engine import process_quotation
        from panelin_v4.engine.classifier import OperatingMode

        text = payload.get("text", "")
        if not text:
            return {"ok": False, "error": "Missing 'text' field"}

        mode_str = payload.get("mode", "pre_cotizacion")
        mode_map = {
            "informativo": OperatingMode.INFORMATIVO,
            "pre_cotizacion": OperatingMode.PRE_COTIZACION,
            "formal": OperatingMode.FORMAL,
        }
        mode = mode_map.get(mode_str, OperatingMode.PRE_COTIZACION)

        output = process_quotation(
            text=text,
            force_mode=mode,
            client_name=payload.get("client_name"),
            client_phone=payload.get("client_phone"),
            client_location=payload.get("client_location"),
        )

        return {"ok": True, "data": output.to_dict()}

    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/quote/batch")
async def quote_batch(payload: dict):
    """Process multiple quotation requests in batch.

    Body: {"requests": [{"text": "..."}, ...], "mode": "pre_cotizacion"}
    """
    try:
        from panelin_v4.engine.quotation_engine import process_batch
        from panelin_v4.engine.classifier import OperatingMode

        requests = payload.get("requests", [])
        if not requests:
            return {"ok": False, "error": "Missing 'requests' field"}

        mode_str = payload.get("mode", "pre_cotizacion")
        mode_map = {
            "informativo": OperatingMode.INFORMATIVO,
            "pre_cotizacion": OperatingMode.PRE_COTIZACION,
            "formal": OperatingMode.FORMAL,
        }
        mode = mode_map.get(mode_str, OperatingMode.PRE_COTIZACION)

        outputs = process_batch(requests, force_mode=mode)

        return {
            "ok": True,
            "count": len(outputs),
            "data": [o.to_dict() for o in outputs],
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}
