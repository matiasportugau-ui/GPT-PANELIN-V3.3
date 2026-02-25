"""Panelin API — Vercel FastAPI entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Panelin API", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"service": "Panelin API", "version": "4.0.0", "status": "ok"}


@app.get("/api/health")
def health():
    return {"status": "healthy"}


@app.post("/api/quote")
def quote(payload: dict):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from panelin_v4.engine.quotation_engine import process_quotation
        from panelin_v4.engine.classifier import OperatingMode
        text = payload.get("text", "")
        if not text:
            return {"ok": False, "error": "Missing 'text' field"}
        mode_map = {
            "informativo": OperatingMode.INFORMATIVO,
            "pre_cotizacion": OperatingMode.PRE_COTIZACION,
            "formal": OperatingMode.FORMAL,
        }
        mode = mode_map.get(payload.get("mode", "pre_cotizacion"), OperatingMode.PRE_COTIZACION)
        output = process_quotation(
            text=text, force_mode=mode,
            client_name=payload.get("client_name"),
            client_phone=payload.get("client_phone"),
            client_location=payload.get("client_location"),
        )
        return {"ok": True, "data": output.to_dict()}
    except Exception as e:
        return {"ok": False, "error": str(e)}
