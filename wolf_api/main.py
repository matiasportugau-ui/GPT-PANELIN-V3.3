"""
Wolf API - FastAPI Backend for Panelin Knowledge Base
v3.0.0 — 2026-02-26
"""

import logging
import os
import json
import hmac
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Security, Query, status
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from .pdf_cotizacion import router as pdf_router
from .sheet_mover import router as mover_router
from .pdf_drive_integration import router as pdf_drive_router

logger = logging.getLogger(__name__)
app = FastAPI(
    title="Panelin Wolf API",
    description="Complete API for BMC Uruguay — quotations, KB persistence, Google Sheets",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

_cors_origins_raw = os.environ.get("CORS_ORIGINS", "")
_cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pdf_router)
app.include_router(mover_router)
app.include_router(pdf_drive_router)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
WOLF_API_KEY = os.environ.get("WOLF_API_KEY", "")

def require_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> None:
    if not WOLF_API_KEY:
        raise HTTPException(503, "WOLF_API_KEY not configured")
    if not api_key or not hmac.compare_digest(api_key, WOLF_API_KEY):
        raise HTTPException(401, "Invalid or missing X-API-Key")


KB_GCS_BUCKET = os.environ.get("KB_GCS_BUCKET", "")
_storage_client = None
_bucket = None


def _get_gcs_bucket():
    global _storage_client, _bucket
    if _bucket is None:
        if not KB_GCS_BUCKET:
            raise HTTPException(503, "KB_GCS_BUCKET not configured")
        try:
            from google.cloud import storage
            _storage_client = storage.Client()
            _bucket = _storage_client.bucket(KB_GCS_BUCKET)
        except Exception as e:
            raise HTTPException(503, f"GCS connection failed: {e}")
    return _bucket

def _append_jsonl(blob_path: str, record: dict) -> dict:
    bucket = _get_gcs_bucket()
    blob = bucket.blob(blob_path)
    existing = ""
    if blob.exists():
        existing = blob.download_as_text()
    line = json.dumps(record, ensure_ascii=False, default=str)
    new_content = existing + line + "\n"
    blob.upload_from_string(new_content, content_type="application/jsonl")
    return {"bucket": KB_GCS_BUCKET, "blob": blob_path}


CATALOG = {}


def _load_catalog():
    global CATALOG
    try:
        bucket = storage_client.bucket(KB_GCS_BUCKET)
        blob = bucket.blob("catalog.json")
        CATALOG = json.loads(blob.download_as_text())
        logger.info(f"Loaded catalog from GCS: {len(CATALOG)} products")
    except Exception as e:
        logger.warning(f"Catalog not found in GCS: {e}")
        catalog_path = os.environ.get("CATALOG_PATH", "catalog.json")
        if os.path.exists(catalog_path):
            with open(catalog_path) as f:
                CATALOG = json.load(f)
            logger.info(f"Loaded catalog from local: {len(CATALOG)} products")
        else:
            logger.warning("Catalog not found anywhere — /find_products will return empty")


@app.on_event("startup")
async def startup():
    _load_catalog()


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/ready")
async def ready_check():
    return {
        "status": "ready",
        "version": "3.0.1",
        "gcs_configured": bool(KB_GCS_BUCKET),
        "sheets_configured": bool(os.environ.get("SHEETS_SPREADSHEET_ID", "")),
    }

class QuoteRequest(BaseModel):
    product_id: str = Field(..., description="Product ID")
    length_m: float = Field(..., ge=0.5, le=14.0)
    width_m: float = Field(..., ge=0.5, le=50.0)
    quantity: int = Field(1, ge=1)
    discount_percent: float = Field(0.0, ge=0, le=30)
    include_accessories: bool = Field(False)
    include_tax: bool = Field(True)
    installation_type: str = Field("techo")


class ProductSearchRequest(BaseModel):
    query: str = Field(..., min_length=3)
    max_results: int = Field(5, ge=1, le=20)


class ProductPriceRequest(BaseModel):
    product_id: str


@app.post("/calculate_quote")
async def api_calculate_quote(req: QuoteRequest, _=Security(require_api_key)):
    product = CATALOG.get(req.product_id)
    if not product:
        raise HTTPException(404, f"Product not found: {req.product_id}")
    price = float(product.get("price_usd", 0))
    area = req.length_m * req.width_m
    subtotal = price * area * req.quantity
    discount = subtotal * (req.discount_percent / 100)
    total = subtotal - discount
    if not req.include_tax:
        total = total / 1.22
    return {
        "product_id": req.product_id,
        "unit_price": price,
        "area_m2": area,
        "quantity": req.quantity,
        "subtotal": round(subtotal, 2),
        "discount": round(discount, 2),
        "total": round(total, 2),
        "tax_included": req.include_tax,
    }

@app.post("/find_products")
async def api_find_products(req: ProductSearchRequest, _=Security(require_api_key)):
    query_lower = req.query.lower()
    results = []
    for pid, pdata in CATALOG.items():
        searchable = f"{pid} {pdata.get('name', '')} {pdata.get('description', '')}".lower()
        if any(term in searchable for term in query_lower.split()):
            results.append({"product_id": pid, **pdata})
            if len(results) >= req.max_results:
                break
    return {"query": req.query, "results": results, "count": len(results)}


@app.post("/product_price")
async def api_product_price(req: ProductPriceRequest, _=Security(require_api_key)):
    product = CATALOG.get(req.product_id)
    if not product:
        raise HTTPException(404, f"Product not found: {req.product_id}")
    return {"product_id": req.product_id, **product}


@app.post("/check_availability")
async def api_check_availability(req: ProductPriceRequest, _=Security(require_api_key)):
    product = CATALOG.get(req.product_id)
    if not product:
        raise HTTPException(404, f"Product not found: {req.product_id}")
    return {
        "product_id": req.product_id,
        "available": product.get("available", True),
        "stock": product.get("stock", "consultar"),
    }


# ─── Technical Validation & Product Data Endpoints ────────────────────
# These endpoints enable the GPT to be a pure API router — no KB data needed.

_BMC_KB: Optional[dict] = None
_BOM_RULES: Optional[dict] = None


def _load_bmc_kb() -> dict:
    """Load BMC_Base_Conocimiento for product specs and formulas."""
    global _BMC_KB
    if _BMC_KB is None:
        kb_path = os.environ.get("BMC_KB_PATH", "BMC_Base_Conocimiento_GPT-2.json")
        if os.path.exists(kb_path):
            with open(kb_path, encoding="utf-8") as f:
                _BMC_KB = json.load(f)
        else:
            _BMC_KB = {}
            logger.warning(f"BMC KB not found at {kb_path}")
    return _BMC_KB


def _load_bom_rules() -> dict:
    """Load BOM rules for autoportancia tables."""
    global _BOM_RULES
    if _BOM_RULES is None:
        rules_path = os.environ.get("BOM_RULES_PATH", "bom_rules.json")
        if os.path.exists(rules_path):
            with open(rules_path, encoding="utf-8") as f:
                _BOM_RULES = json.load(f)
        else:
            _BOM_RULES = {}
            logger.warning(f"BOM rules not found at {rules_path}")
    return _BOM_RULES


def _find_autoportancia(familia: str, sub_familia: str, thickness_mm: int) -> Optional[dict]:
    """Look up autoportancia entry from BOM rules tables."""
    rules = _load_bom_rules()
    tables = rules.get("autoportancia", {}).get("tablas", {})
    # Build lookup key: ISODEC_EPS, ISOROOF_3G, ISOPANEL_EPS, etc.
    key = f"{familia}_{sub_familia}".upper()
    if familia.upper() == "ISOROOF":
        key = "ISOROOF_3G"
    return tables.get(key, {}).get(str(thickness_mm))


def _find_product_specs(familia: str, thickness_mm: int) -> Optional[dict]:
    """Look up product specs from BMC KB."""
    kb = _load_bmc_kb()
    products = kb.get("products", {})
    # Try exact familia key first
    prod = products.get(familia)
    if not prod:
        # Try common aliases
        aliases = {
            "ISODEC": "ISODEC_EPS", "ISOPANEL": "ISOPANEL_EPS",
            "ISOROOF": "ISOROOF_3G", "ISOWALL": "ISOWALL_PIR",
            "ISOFRIG": "ISOFRIG_PIR",
        }
        prod = products.get(aliases.get(familia.upper(), ""))
    if not prod:
        # Search all products
        for key, val in products.items():
            if familia.upper() in key.upper():
                prod = val
                break
    if not prod:
        return None
    espesores = prod.get("espesores", {})
    esp_data = espesores.get(str(thickness_mm))
    if not esp_data:
        return None
    return {**esp_data, "_product": prod}


def _suggest_alternatives(familia: str, sub_familia: str, span_m: float) -> list:
    """Find thicknesses that support the given span."""
    rules = _load_bom_rules()
    tables = rules.get("autoportancia", {}).get("tablas", {})
    key = f"{familia}_{sub_familia}".upper()
    if familia.upper() == "ISOROOF":
        key = "ISOROOF_3G"
    family_table = tables.get(key, {})
    alternatives = []
    for thick_str, data in family_table.items():
        max_span = data.get("luz_max_m", 0)
        if max_span >= span_m:
            alternatives.append({
                "thickness_mm": int(thick_str),
                "max_span_m": max_span,
                "safe_span_m": round(max_span * 0.85, 2),
                "peso_kg_m2": data.get("peso_kg_m2"),
            })
    alternatives.sort(key=lambda x: x["thickness_mm"])
    return alternatives


class AutoportanciaRequest(BaseModel):
    familia: str = Field(..., description="Product family: ISODEC, ISOROOF, ISOPANEL, ISOWALL, ISOFRIG")
    sub_familia: str = Field("EPS", description="Sub-family: EPS, PIR, 3G")
    thickness_mm: int = Field(..., ge=20, le=250, description="Panel thickness in mm")
    span_m: float = Field(..., gt=0, le=20, description="Project span between supports in meters")


@app.post("/validate_autoportancia")
async def validate_autoportancia(req: AutoportanciaRequest, _=Security(require_api_key)):
    """Validate if a panel can span the requested distance.

    Returns ok/warning/blocked status with safety margins and alternatives.
    """
    entry = _find_autoportancia(req.familia, req.sub_familia, req.thickness_mm)
    if not entry:
        raise HTTPException(
            404,
            f"No autoportancia data for {req.familia} {req.sub_familia} {req.thickness_mm}mm. "
            f"Check /product_catalog for available products.",
        )

    max_span = entry["luz_max_m"]
    safe_span = round(max_span * 0.85, 2)  # 15% safety margin

    if req.span_m <= safe_span:
        status = "ok"
    elif req.span_m <= max_span:
        status = "warning"
    else:
        status = "blocked"

    result = {
        "valid": status != "blocked",
        "status": status,
        "familia": req.familia,
        "sub_familia": req.sub_familia,
        "thickness_mm": req.thickness_mm,
        "requested_span_m": req.span_m,
        "max_span_m": max_span,
        "safe_span_m": safe_span,
        "peso_kg_m2": entry.get("peso_kg_m2"),
        "margin_percent": round((1 - req.span_m / max_span) * 100, 1) if max_span > 0 else 0,
    }

    if status == "warning":
        result["recommendation"] = (
            f"La luz de {req.span_m}m está entre el límite seguro ({safe_span}m) y el máximo absoluto ({max_span}m). "
            f"Recomendamos un espesor mayor o un apoyo intermedio."
        )
        result["alternatives"] = _suggest_alternatives(req.familia, req.sub_familia, req.span_m)
    elif status == "blocked":
        result["recommendation"] = (
            f"La luz de {req.span_m}m excede el máximo de {max_span}m para {req.familia} {req.thickness_mm}mm. "
            f"Se requiere un espesor mayor o estructura de apoyo adicional."
        )
        result["alternatives"] = _suggest_alternatives(req.familia, req.sub_familia, req.span_m)

    return result


@app.get("/product_specs/{product_id}")
async def get_product_specs(product_id: str, _=Security(require_api_key)):
    """Get technical specifications for a product.

    Accepts product_id in formats: ISODEC_EPS_100mm, ISD100EPS, etc.
    Returns autoportancia, thermal coefficients, dimensions, fixing system.
    """
    # Try to find in CATALOG first for metadata
    catalog_entry = CATALOG.get(product_id, {})

    # Parse product_id to extract familia + thickness
    familia = catalog_entry.get("familia", "")
    thickness = catalog_entry.get("thickness_mm")
    sub_familia = catalog_entry.get("sub_familia", "EPS")

    # If not found in catalog, try parsing the key (e.g. ISODEC_EPS_100mm)
    if not familia or thickness is None:
        parts = product_id.replace("mm", "").split("_")
        if len(parts) >= 2:
            familia_candidates = ["_".join(parts[:2]), parts[0]]
            for fc in familia_candidates:
                for fkey in ["ISODEC_EPS", "ISODEC_PIR", "ISOROOF_3G", "ISOPANEL_EPS",
                             "ISOWALL_PIR", "ISOFRIG_PIR"]:
                    if fc.upper() == fkey:
                        familia = fkey
                        break
                if familia:
                    break
            try:
                thickness = int(parts[-1])
            except (ValueError, IndexError):
                pass

    if not familia or thickness is None:
        raise HTTPException(404, f"Cannot resolve product specs for '{product_id}'")

    # Split familia key for BMC lookup
    familia_base = familia.split("_")[0]
    specs = _find_product_specs(familia, thickness)

    # Get autoportancia from BOM rules
    sub = sub_familia or (familia.split("_")[1] if "_" in familia else "EPS")
    auto_entry = _find_autoportancia(familia_base, sub, thickness)

    result = {
        "product_id": product_id,
        "familia": familia_base,
        "sub_familia": sub,
        "thickness_mm": thickness,
        "name": catalog_entry.get("name", f"{familia} {thickness}mm"),
    }

    if specs:
        prod = specs.pop("_product", {})
        result.update({
            "autoportancia_m": specs.get("autoportancia"),
            "coef_termico": specs.get("coeficiente_termico"),
            "resistencia_termica": specs.get("resistencia_termica"),
            "ancho_util_m": prod.get("ancho_util"),
            "sistema_fijacion": prod.get("sistema_fijacion"),
            "tipo": prod.get("tipo"),
            "ignifugo": prod.get("ignifugo"),
            "precio_usd_m2": specs.get("precio"),
        })
    elif auto_entry:
        result.update({
            "autoportancia_m": auto_entry.get("luz_max_m"),
            "peso_kg_m2": auto_entry.get("peso_kg_m2"),
        })

    if catalog_entry:
        result["price_usd"] = catalog_entry.get("price_usd")
        result["unit"] = catalog_entry.get("unit")

    return result


@app.get("/product_catalog")
async def get_product_catalog(
    tipo: Optional[str] = Query(None, description="Filter by type: Panel, Accesorio, etc."),
    familia: Optional[str] = Query(None, description="Filter by family: ISODEC, ISOROOF, etc."),
    _=Security(require_api_key),
):
    """Get a slim listing of all products available in the catalog.

    Optionally filter by tipo (Panel, Accesorio) or familia (ISODEC, ISOROOF).
    """
    products = []
    for pid, p in CATALOG.items():
        if tipo and p.get("tipo", "").lower() != tipo.lower():
            continue
        if familia and familia.lower() not in p.get("familia", "").lower():
            continue
        products.append({
            "product_id": pid,
            "name": p.get("name"),
            "familia": p.get("familia"),
            "sub_familia": p.get("sub_familia"),
            "tipo": p.get("tipo"),
            "thickness_mm": p.get("thickness_mm"),
            "unit": p.get("unit"),
            "price_usd": p.get("price_usd"),
        })
    return {"total": len(products), "products": products}


@app.get("/business_rules")
async def get_business_rules(_=Security(require_api_key)):
    """Get current business rules and policies.

    Returns IVA rate, currency, derivation policy, shipping defaults, etc.
    """
    kb = _load_bmc_kb()
    reglas = kb.get("reglas_negocio", {})
    return {
        "iva_rate": reglas.get("iva", 0.22),
        "iva_included_in_prices": True,
        "currency": reglas.get("moneda", "USD"),
        "min_roof_slope_pct": 7,
        "default_shipping_usd": 280.0,
        "derivation_policy": "internal_only",
        "derivation_rule": reglas.get("derivacion", {}).get("regla_oro",
            "NUNCA derivar a proveedor externo. SIEMPRE derivar a agentes de ventas BMC Uruguay."),
        "service_scope": "materials_and_advisory_only",
        "official_website": "https://bmcuruguay.com.uy",
        "phone_format": "09XXXXXXX (9 dígitos) or +598XXXXXXXX",
        "required_for_formal_quote": ["nombre", "telefono", "direccion_obra"],
        "audio_transcription": False,
    }


class CompareOptionsRequest(BaseModel):
    option_a_product_id: str = Field(..., description="First product ID (e.g. ISODEC_EPS_100mm)")
    option_b_product_id: str = Field(..., description="Second product ID (e.g. ISODEC_EPS_150mm)")
    area_m2: float = Field(..., gt=0, le=10000, description="Project area in m²")
    usage: str = Field("residencial", description="Usage type: residencial or comercial")


@app.post("/compare_options")
async def compare_options(req: CompareOptionsRequest, _=Security(require_api_key)):
    """Compare two panel options: pricing, thermal performance, and energy savings.

    Returns the price difference, thermal resistance comparison, estimated annual
    energy savings in USD, and payback period.
    """
    # Get specs for both options
    cat_a = CATALOG.get(req.option_a_product_id)
    cat_b = CATALOG.get(req.option_b_product_id)
    if not cat_a:
        raise HTTPException(404, f"Product not found: {req.option_a_product_id}")
    if not cat_b:
        raise HTTPException(404, f"Product not found: {req.option_b_product_id}")

    price_a = float(cat_a.get("price_usd", 0))
    price_b = float(cat_b.get("price_usd", 0))

    # Get thermal data from BMC KB
    kb = _load_bmc_kb()
    ref = kb.get("datos_referencia_uruguay", {})
    kwh_price = ref.get("precio_kwh_uruguay", {}).get(req.usage, 0.12)
    calef = ref.get("estacion_calefaccion", {})
    grados_dia = calef.get("grados_dia_promedio", 8)
    horas_dia = calef.get("horas_dia_promedio", 12)
    dias_estacion = calef.get("meses", 9) * 30

    # Try to get thermal resistance for both
    familia_a = cat_a.get("familia", "").split(" ")[0]
    familia_b = cat_b.get("familia", "").split(" ")[0]
    thick_a = cat_a.get("thickness_mm")
    thick_b = cat_b.get("thickness_mm")

    res_a = None
    res_b = None

    if familia_a and thick_a:
        specs_a = _find_product_specs(familia_a, int(thick_a))
        if specs_a:
            res_a = specs_a.get("resistencia_termica")

    if familia_b and thick_b:
        specs_b = _find_product_specs(familia_b, int(thick_b))
        if specs_b:
            res_b = specs_b.get("resistencia_termica")

    result = {
        "option_a": {
            "product_id": req.option_a_product_id,
            "name": cat_a.get("name"),
            "price_usd_m2": price_a,
            "total_usd": round(price_a * req.area_m2, 2),
            "thickness_mm": thick_a,
            "resistencia_termica": res_a,
        },
        "option_b": {
            "product_id": req.option_b_product_id,
            "name": cat_b.get("name"),
            "price_usd_m2": price_b,
            "total_usd": round(price_b * req.area_m2, 2),
            "thickness_mm": thick_b,
            "resistencia_termica": res_b,
        },
        "area_m2": req.area_m2,
        "price_diff_per_m2": round(abs(price_b - price_a), 2),
        "price_diff_total": round(abs(price_b - price_a) * req.area_m2, 2),
    }

    # Calculate energy savings if thermal data available
    if res_a is not None and res_b is not None and res_a != res_b:
        diff = abs(res_b - res_a)
        annual_savings = round(
            req.area_m2 * diff * grados_dia * kwh_price * horas_dia * dias_estacion, 2
        )
        cheaper = "a" if price_a <= price_b else "b"
        better_thermal = "b" if (res_b or 0) > (res_a or 0) else "a"
        price_premium = abs(price_b - price_a) * req.area_m2
        payback = round(price_premium / annual_savings, 1) if annual_savings > 0 and cheaper != better_thermal else 0

        result["energy_comparison"] = {
            "thermal_resistance_diff_m2kw": round(diff, 2),
            "better_insulation": req.option_b_product_id if better_thermal == "b" else req.option_a_product_id,
            "annual_energy_savings_usd": annual_savings,
            "usage": req.usage,
            "kwh_price_usd": kwh_price,
            "heating_season_days": dias_estacion,
            "payback_years": payback,
            "recommendation": (
                f"El panel con mayor espesor ofrece mejor aislamiento (R={max(res_a, res_b)} vs R={min(res_a, res_b)}). "
                f"Ahorro energético estimado: USD {annual_savings}/año. "
                + (f"Retorno de inversión: {payback} años." if payback > 0 else "")
            ),
        }
    else:
        result["energy_comparison"] = {
            "available": False,
            "reason": "Thermal resistance data not available for one or both products.",
        }

    return result


@app.post("/kb/conversations")
async def persist_conversation(data: dict, _=Security(require_api_key)):
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "client_id": data.get("client_id", "unknown"),
        "summary": data.get("summary", ""),
        "quotation_ref": data.get("quotation_ref"),
        "products_discussed": data.get("products_discussed", []),
        "date": data.get("date", now),
        "stored_at": now,
    }
    gcs = await run_in_threadpool(_append_jsonl, "kb/conversations.jsonl", record)
    return {"ok": True, "stored_at": now, "gcs": gcs}


@app.post("/kb/corrections")
async def register_correction(data: dict, _=Security(require_api_key)):
    now = datetime.now(timezone.utc).isoformat()
    src = data.get("source_file", "")
    cid = f"cor-{hashlib.md5(f'{src}{now}'.encode()).hexdigest()[:12]}"
    record = {
        "correction_id": cid,
        "source_file": src,
        "field_path": data.get("field_path", ""),
        "old_value": data.get("old_value", ""),
        "new_value": data.get("new_value", ""),
        "reason": data.get("reason", ""),
        "reported_by": data.get("reported_by", "panelin_gpt"),
        "date": now,
        "status": "pending",
    }
    gcs = await run_in_threadpool(_append_jsonl, "kb/corrections.jsonl", record)
    return {"ok": True, "correction_id": cid, "stored_at": now, "gcs": gcs}

@app.post("/kb/customers")
async def save_customer(data: dict, _=Security(require_api_key)):
    now = datetime.now(timezone.utc).isoformat()
    raw_id = data.get("phone", data.get("name", "unknown"))
    cust_id = f"cust-{hashlib.md5(raw_id.encode()).hexdigest()[:12]}"
    blob_path = f"kb/customers/{cust_id}.json"
    bucket = _get_gcs_bucket()
    blob = bucket.blob(blob_path)
    existing = {}
    if blob.exists():
        existing = json.loads(blob.download_as_text())
    customer = {
        **existing,
        "customer_id": cust_id,
        "name": data.get("name", existing.get("name", "")),
        "phone": data.get("phone", existing.get("phone", "")),
        "address": data.get("address", existing.get("address", "")),
        "city": data.get("city", existing.get("city", "")),
        "department": data.get("department", existing.get("department", "")),
        "notes": data.get("notes", existing.get("notes", "")),
        "last_interaction": now,
        "updated_at": now,
    }
    blob.upload_from_string(
        json.dumps(customer, ensure_ascii=False, indent=2),
        content_type="application/json",
    )
    return {"ok": True, "customer_id": cust_id, "stored_at": now}

@app.get("/kb/customers")
async def lookup_customer(search: str = Query(..., min_length=2), _=Security(require_api_key)):
    bucket = _get_gcs_bucket()
    search_lower = search.lower()
    results = []
    for blob in bucket.list_blobs(prefix="kb/customers/"):
        if not blob.name.endswith(".json"):
            continue
        try:
            cdata = json.loads(blob.download_as_text())
            haystack = f"{cdata.get('name','')} {cdata.get('phone','')} {cdata.get('city','')}".lower()
            if search_lower in haystack:
                results.append(cdata)
        except Exception:
            continue
    return {"ok": True, "customers": results, "count": len(results)}

SHEETS_ID = os.environ.get("SHEETS_SPREADSHEET_ID", "")
SHEETS_TAB_2026 = os.environ.get("SHEETS_TAB_2026", "Administrador de Cotizaciones 2026")
SHEETS_TAB_2025 = os.environ.get("SHEETS_TAB_2025", "2.0 -  Administrador de Cotizaciones")
SHEETS_TAB_ADMIN = os.environ.get("SHEETS_TAB_ADMIN", "Admin.")
_gc = None
_spreadsheet = None


def _get_spreadsheet():
    global _gc, _spreadsheet
    if _spreadsheet is None:
        if not SHEETS_ID:
            raise HTTPException(503, "SHEETS_SPREADSHEET_ID not configured")
        try:
            import gspread
            from google.auth import default as gauth_default
            creds, _ = gauth_default(scopes=["https://www.googleapis.com/auth/spreadsheets"])
            _gc = gspread.authorize(creds)
            _spreadsheet = _gc.open_by_key(SHEETS_ID)
        except Exception as e:
            raise HTTPException(503, f"Sheets connection failed: {e}")
    return _spreadsheet


def _get_worksheet(tab=None):
    ss = _get_spreadsheet()
    tab_name = tab or SHEETS_TAB_2026
    try:
        return ss.worksheet(tab_name)
    except Exception:
        raise HTTPException(404, f"Tab '{tab_name}' not found")


def _get_admin_worksheet():
    """Get the Admin tab for write operations (new consultations, quotation lines)."""
    ss = _get_spreadsheet()
    tab_name = SHEETS_TAB_ADMIN.strip()
    try:
        return ss.worksheet(tab_name)
    except Exception:
        # Fallback to default tab if Admin not found
        logger.warning(f"Admin tab '{tab_name}' not found, falling back to default")
        return _get_worksheet()


def _row_to_dict(row, row_number):
    return {
        "row_number": row_number,
        "asignado": row[0] if len(row) > 0 else "",
        "estado": row[1] if len(row) > 1 else "",
        "fecha": row[2] if len(row) > 2 else "",
        "cliente": row[3] if len(row) > 3 else "",
        "origen": row[4] if len(row) > 4 else "",
        "telefono": row[5] if len(row) > 5 else "",
        "direccion": row[6] if len(row) > 6 else "",
        "consulta": row[7] if len(row) > 7 else "",
        "comentarios": row[8] if len(row) > 8 else "",
    }


def _find_last_data_row(all_rows):
    last = 2
    for i, row in enumerate(all_rows):
        if i < 2:
            continue
        if len(row) > 3 and row[3].strip():
            last = i + 1
    return last

@app.get("/sheets/consultations")
async def read_consultations(
    tab: Optional[str] = None,
    estado: Optional[str] = None,
    origen: Optional[str] = None,
    asignado: Optional[str] = None,
    cliente: Optional[str] = None,
    fecha: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    _=Security(require_api_key),
):
    ws = await run_in_threadpool(_get_worksheet, tab)
    all_rows = await run_in_threadpool(ws.get_all_values)
    results = []
    for i, row in enumerate(all_rows):
        if i < 2 or not any(c.strip() for c in row[:8]):
            continue
        entry = _row_to_dict(row, i + 1)
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
    return {"tab": tab or SHEETS_TAB_2026, "total_results": len(results), "consultations": results}

@app.post("/sheets/consultations")
async def add_consultation(data: dict, _=Security(require_api_key)):
    ws = await run_in_threadpool(_get_admin_worksheet)
    fecha = data.get("fecha") or datetime.now(timezone.utc).strftime("%d-%m")
    new_row = [
        data.get("asignado", ""), "Pendiente", fecha,
        data.get("cliente", ""), (data.get("origen", "")).upper(),
        data.get("telefono", ""), data.get("direccion", ""),
        data.get("consulta", ""), data.get("comentarios", ""),
    ]
    all_rows = await run_in_threadpool(ws.get_all_values)
    r = _find_last_data_row(all_rows) + 1
    await run_in_threadpool(ws.update, f"A{r}:I{r}", [new_row])
    return {"success": True, "row_number": r, "data": _row_to_dict(new_row, r)}


@app.post("/sheets/quotation_line")
async def add_quotation_line(data: dict, _=Security(require_api_key)):
    ws = await run_in_threadpool(_get_admin_worksheet)
    fecha = datetime.now(timezone.utc).strftime("%d-%m")
    row_num = data.get("row_number")
    if row_num:
        current = await run_in_threadpool(ws.row_values, row_num)
        if data.get("estado"):
            await run_in_threadpool(ws.update_acell, f"B{row_num}", data["estado"])
        if data.get("comentarios"):
            old = current[8] if len(current) > 8 else ""
            sep = " | " if old else ""
            await run_in_threadpool(
                ws.update_acell, f"I{row_num}",
                f"{old}{sep}[Cotizado {fecha}] {data['comentarios']}",
            )
        return {"success": True, "action": "updated", "row_number": row_num}
    else:
        new_row = [
            data.get("asignado", ""), data.get("estado", "Enviado"), fecha,
            data.get("cliente", ""), (data.get("origen", "")).upper(),
            data.get("telefono", ""), data.get("direccion", ""),
            data.get("consulta", ""), data.get("comentarios", ""),
        ]
        all_rows = await run_in_threadpool(ws.get_all_values)
        r = _find_last_data_row(all_rows) + 1
        await run_in_threadpool(ws.update, f"A{r}:I{r}", [new_row])
        return {"success": True, "action": "appended", "row_number": r}

@app.patch("/sheets/update_row")
async def update_row(data: dict, _=Security(require_api_key)):
    ws = await run_in_threadpool(_get_worksheet)
    rn = data.get("row_number")
    if not rn:
        raise HTTPException(400, "row_number is required")
    col_map = {
        "estado": "B", "asignado": "A", "consulta": "H",
        "telefono": "F", "direccion": "G", "comentarios": "I",
        "cotizacion": "J",
    }
    updated = []
    for field, col in col_map.items():
        if data.get(field):
            await run_in_threadpool(ws.update_acell, f"{col}{rn}", data[field])
            updated.append(field)
    if not updated:
        raise HTTPException(400, "No fields to update")
    return {"success": True, "row_number": rn, "fields_updated": updated}


@app.post("/sheets/set_cotizacion_url")
async def set_cotizacion_url(data: dict, api_key: str = Security(require_api_key)):
    """Write a PDF/Drive URL into Column J (Cotizacion) for a given row."""
    rn = data.get("row_number")
    url = data.get("url", "")
    if not rn:
        raise HTTPException(400, "row_number is required")
        if not url:
            raise HTTPException(400, "url is required")
            tab = data.get("tab")
            if tab:
                ws = await run_in_threadpool(_get_worksheet, tab)
            else:
                ws = await run_in_threadpool(_get_admin_worksheet)
                await run_in_threadpool(ws.update_acell, f"J{rn}", url)
                return {"success": True, "row_number": rn, "column": "J", "url_written": url}
                
@app.get("/sheets/row/{row_number}")
async def get_row(row_number: int, tab: Optional[str] = None, _=Security(require_api_key)):
    ws = await run_in_threadpool(_get_worksheet, tab)
    values = await run_in_threadpool(ws.row_values, row_number)
    if not values:
        raise HTTPException(404, f"Row {row_number} is empty")
    return _row_to_dict(values, row_number)

@app.get("/sheets/search")
async def search_sheets(
    q: str = Query(..., min_length=2),
    tab: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    _=Security(require_api_key),
):
    ws = await run_in_threadpool(_get_worksheet, tab)
    all_rows = await run_in_threadpool(ws.get_all_values)
    q_lower = q.lower()
    results = []
    for i, row in enumerate(all_rows):
        if i < 2:
            continue
        cliente = row[3].lower() if len(row) > 3 else ""
        consulta = row[7].lower() if len(row) > 7 else ""
        if q_lower in cliente or q_lower in consulta:
            results.append(_row_to_dict(row, i + 1))
            if len(results) >= limit:
                break
    return {"query": q, "total_results": len(results), "results": results}


@app.get("/sheets/stats")
async def get_sheet_stats(tab: Optional[str] = None, _=Security(require_api_key)):
    ws = await run_in_threadpool(_get_worksheet, tab)
    all_rows = await run_in_threadpool(ws.get_all_values)
    stats = {"total_rows": 0, "by_estado": {}, "by_origen": {}, "by_asignado": {}}
    for i, row in enumerate(all_rows):
        if i < 2 or not any(c.strip() for c in row[:8]):
            continue
        stats["total_rows"] += 1
        e = row[1].strip() if len(row) > 1 else ""
        o = row[4].strip() if len(row) > 4 else ""
        a = row[0].strip() if len(row) > 0 else ""
        if e:
            stats["by_estado"][e] = stats["by_estado"].get(e, 0) + 1
        if o:
            stats["by_origen"][o] = stats["by_origen"].get(o, 0) + 1
        if a:
            stats["by_asignado"][a] = stats["by_asignado"].get(a, 0) + 1
    return stats


# ─── Multi-Sheet Inspector (Admin-Hub) ────────────────────────────────
@app.get("/sheets/inspect", tags=["admin-hub"])
async def inspect_sheet(
    sheet_id: str = Query(..., description="Google Sheets ID to inspect"),
    _=Security(require_api_key)
):
    """Inspect any Google Sheet shared with the service account."""
    try:
        _get_spreadsheet()
        target = await run_in_threadpool(_gc.open_by_key, sheet_id)
        worksheets = await run_in_threadpool(lambda: target.worksheets())
        result = {
            "sheet_id": sheet_id,
            "title": target.title,
            "url": f"https://docs.google.com/spreadsheets/d/{sheet_id}",
            "tab_count": len(worksheets),
            "tabs": []
        }
        for ws in worksheets:
            tab = {"name": ws.title, "gid": ws.id, "rows_alloc": ws.row_count, "cols_alloc": ws.col_count}
            try:
                vals = await run_in_threadpool(ws.get_all_values)
                tab["rows_used"] = len(vals)
                tab["headers"] = vals[0] if vals else []
                tab["sample"] = vals[1:6] if len(vals) > 1 else []
            except Exception as e:
                tab["error"] = str(e)
            result["tabs"].append(tab)
        return result
    except Exception as e:
        raise HTTPException(500, f"Cannot inspect sheet {sheet_id}: {e}")
