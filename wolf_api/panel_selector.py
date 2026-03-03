"""
Panelin Wolf API v2 — Panel Selector AI
=========================================

POST /v2/recommend_panel

Given a use case, thermal requirement, budget, and area, returns
the top 3 recommended panels ranked by price/performance ratio.

The "AI" here is deterministic scoring — no LLM inference. The engine:
  1. Filters panels by use_case compatibility
  2. Filters by thermal_requirement (R-value ≥ requested)
  3. Filters by budget (price/m² × area ≤ budget)
  4. Scores by price/performance ratio: R-value per USD
  5. Returns top 3 with comparison table
"""

from __future__ import annotations

import json
import logging
import os
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2", tags=["Panel Selector v2"])

# ─── Reference to global CATALOG + BMC KB ───
_CATALOG: dict = {}
_BMC_KB: dict = {}


def set_data(catalog: dict, bmc_kb: dict) -> None:
    """Called by main.py to inject loaded data."""
    global _CATALOG, _BMC_KB
    _CATALOG = catalog
    _BMC_KB = bmc_kb


# ─── Use-case → panel type mapping ───
USE_CASE_TYPES = {
    "techo": ["cubierta_pesada", "cubierta_liviana"],
    "pared": ["pared"],
    "camara_frigorifica": ["pared_frigorifica"],
}

# ─── EPS thermal coefficient for estimating R-value when not in KB ───
EPS_COEF = 0.035  # W/(m·K)
PIR_COEF = 0.022  # W/(m·K)


# ─── Schemas ───

class RecommendPanelRequest(BaseModel):
    use_case: Literal["techo", "pared", "camara_frigorifica"] = Field(
        ...,
        description="Installation use case: techo (roof), pared (wall/facade), camara_frigorifica (cold room)",
    )
    thermal_requirement: Optional[float] = Field(
        None,
        ge=0,
        le=20,
        description="Minimum thermal resistance R-value (m²·K/W). If not set, returns all options.",
    )
    budget_max: Optional[float] = Field(
        None,
        gt=0,
        le=1_000_000,
        description="Maximum total budget in USD. Filters products where price/m² × area exceeds this.",
    )
    area_m2: float = Field(
        ...,
        gt=0,
        le=50000,
        description="Project area in m² (used for budget calculation and total cost)",
    )


class PanelRecommendation(BaseModel):
    rank: int = Field(..., description="Ranking position (1 = best)")
    product_id: str = Field(..., description="Product ID for API calls")
    name: str = Field(..., description="Product name")
    familia: str = Field(...)
    sub_familia: str = Field(...)
    thickness_mm: float = Field(...)
    price_per_m2: float = Field(..., description="Price USD/m² (IVA included)")
    total_cost: float = Field(..., description="price × area_m2")
    thermal_resistance: Optional[float] = Field(None, description="R-value (m²·K/W)")
    thermal_conductivity: Optional[float] = Field(None, description="λ W/(m·K)")
    autoportancia_m: Optional[float] = Field(None, description="Max span in meters")
    ignifugo: Optional[str] = Field(None, description="Fire resistance rating")
    score: float = Field(..., description="Price/performance score (higher = better value)")
    score_breakdown: dict = Field(default_factory=dict, description="Score component breakdown")
    advantages: List[str] = Field(default_factory=list, description="Key advantages of this option")
    considerations: List[str] = Field(default_factory=list, description="Things to consider")


class RecommendPanelResponse(BaseModel):
    use_case: str
    area_m2: float
    thermal_requirement: Optional[float]
    budget_max: Optional[float]
    total_candidates: int = Field(..., description="Panels evaluated before filtering")
    total_matching: int = Field(..., description="Panels that passed all filters")
    recommendations: List[PanelRecommendation] = Field(
        ..., description="Top 3 recommended panels, ranked by price/performance"
    )
    comparison_table: List[dict] = Field(
        ..., description="Side-by-side comparison of recommended panels"
    )
    notes: List[str] = Field(default_factory=list)


# ─── Scoring logic ───

def _estimate_r_value(thickness_mm: float, sub_familia: str) -> float:
    """Estimate R-value from thickness when not in KB."""
    coef = PIR_COEF if "PIR" in sub_familia.upper() else EPS_COEF
    return round(thickness_mm / 1000.0 / coef, 2)


def _get_panel_specs(prod_key: str) -> Optional[dict]:
    """Look up panel specs from BMC KB."""
    products = _BMC_KB.get("products", {})
    # Try exact key
    prod = products.get(prod_key)
    if prod:
        return prod
    # Try splitting: ISODEC_EPS → ISODEC_EPS
    for key, val in products.items():
        if prod_key.startswith(key):
            return val
    return None


def _build_candidates() -> list[dict]:
    """Build candidate list from catalog + BMC KB."""
    candidates = []
    seen_keys = set()

    # From BMC KB (has thermal data)
    for prod_key, prod_data in _BMC_KB.get("products", {}).items():
        tipo = prod_data.get("tipo", "")
        for esp_str, esp_data in prod_data.get("espesores", {}).items():
            try:
                thickness = int(esp_str)
            except ValueError:
                continue

            precio = esp_data.get("precio")
            if not precio or not isinstance(precio, (int, float)):
                # Try catalog price
                cat_key = f"{prod_key}_{esp_str}mm"
                cat_entry = _CATALOG.get(cat_key, {})
                precio = cat_entry.get("price_usd")
                if not precio:
                    continue

            r_value = esp_data.get("resistencia_termica")
            coef = esp_data.get("coeficiente_termico")
            auto = esp_data.get("autoportancia")

            # Determine sub_familia from key
            sub_fam = "PIR" if "PIR" in prod_key else "EPS"
            if "3G" in prod_key or "ISOROOF" in prod_key:
                sub_fam = "PIR"  # ISOROOF uses PIR core

            # Estimate R-value if missing
            if r_value is None:
                r_value = _estimate_r_value(thickness, sub_fam)

            cat_key = f"{prod_key}_{esp_str}mm"
            if cat_key in seen_keys:
                continue
            seen_keys.add(cat_key)

            candidates.append({
                "product_id": cat_key,
                "name": _CATALOG.get(cat_key, {}).get("name", f"{prod_key} {esp_str}mm"),
                "familia": prod_key.split("_")[0] if "_" in prod_key else prod_key,
                "sub_familia": sub_fam,
                "thickness_mm": float(thickness),
                "price_per_m2": float(precio),
                "tipo": tipo,
                "r_value": r_value,
                "coef_termico": coef,
                "autoportancia_m": auto,
                "ignifugo": prod_data.get("ignifugo"),
            })

    # Also check catalog for panels NOT in BMC KB (e.g. ISOFRIG with prices)
    for pid, p in _CATALOG.items():
        if "_" not in pid or "mm" not in pid:
            continue
        cat_tipo = p.get("tipo", "")
        if cat_tipo not in ("Panel", "PANEL EPS", "PANEL PIR"):
            continue
        if pid in seen_keys:
            continue

        thickness = p.get("thickness_mm")
        if not thickness:
            continue
        price = p.get("price_usd")
        if not price:
            continue

        sub_fam = p.get("sub_familia", "EPS")
        r_value = _estimate_r_value(float(thickness), sub_fam)

        # Determine tipo from familia
        familia = p.get("familia", "")
        if "ISOFRIG" in familia.upper():
            tipo = "pared_frigorifica"
        elif "ISOWALL" in familia.upper() or "ISOPANEL" in familia.upper():
            tipo = "pared"
        elif "ISOROOF" in familia.upper():
            tipo = "cubierta_liviana"
        else:
            tipo = "cubierta_pesada"

        seen_keys.add(pid)
        candidates.append({
            "product_id": pid,
            "name": p.get("name", pid),
            "familia": familia.split(" ")[0].split("/")[0].strip(),
            "sub_familia": sub_fam,
            "thickness_mm": float(thickness),
            "price_per_m2": float(price),
            "tipo": tipo,
            "r_value": r_value,
            "coef_termico": None,
            "autoportancia_m": None,
            "ignifugo": "PIR" if "PIR" in sub_fam.upper() else "EPS Estándar",
        })

    return candidates


def _score_panel(panel: dict, area_m2: float) -> float:
    """Score a panel by price/performance ratio.

    Score = (R-value × 100) / price_per_m2
    Higher = better value (more insulation per dollar).
    Bonuses for PIR (fire), high autoportancia, etc.
    """
    r_value = panel.get("r_value", 0) or 0
    price = panel.get("price_per_m2", 999)

    if price <= 0:
        return 0

    # Base score: R-value per dollar
    base = (r_value * 100) / price

    # Bonus: PIR gets +15% for fire resistance
    if "PIR" in (panel.get("sub_familia", "") or "").upper():
        base *= 1.15

    # Bonus: high autoportancia (>7m) gets +10%
    auto = panel.get("autoportancia_m")
    if auto and auto > 7:
        base *= 1.10

    return round(base, 3)


def _generate_advantages(panel: dict) -> list[str]:
    """Generate advantage bullet points for a panel."""
    advantages = []
    r = panel.get("r_value")
    sub = panel.get("sub_familia", "")
    auto = panel.get("autoportancia_m")
    thick = panel.get("thickness_mm", 0)

    if r and r >= 4:
        advantages.append(f"Excelente aislamiento térmico (R={r} m²·K/W)")
    elif r and r >= 2:
        advantages.append(f"Buen aislamiento térmico (R={r} m²·K/W)")

    if "PIR" in sub.upper():
        advantages.append("Alta resistencia al fuego (PIR)")
    
    if auto and auto >= 7:
        advantages.append(f"Alta autoportancia ({auto}m) — menos estructura")
    elif auto and auto >= 5:
        advantages.append(f"Buena autoportancia ({auto}m)")

    if thick <= 50:
        advantages.append("Espesor compacto — ideal donde el espacio es limitado")
    if thick >= 200:
        advantages.append("Máximo aislamiento — ideal para eficiencia energética")

    price = panel.get("price_per_m2", 0)
    if price < 45:
        advantages.append("Precio competitivo")

    return advantages


def _generate_considerations(panel: dict, use_case: str) -> list[str]:
    """Generate consideration notes."""
    considerations = []
    r = panel.get("r_value")
    sub = panel.get("sub_familia", "")
    auto = panel.get("autoportancia_m")

    if use_case == "camara_frigorifica" and "EPS" in sub.upper():
        considerations.append("EPS no es ideal para cámaras frigoríficas — considerar PIR")

    if auto and auto < 4:
        considerations.append(f"Autoportancia limitada ({auto}m) — requiere más apoyos")

    if r and r < 2 and use_case == "techo":
        considerations.append("Aislamiento bajo para techo — considerar espesor mayor para ahorro energético")

    if "PIR" in sub.upper():
        considerations.append("Costo mayor que EPS — justificado por resistencia al fuego y mejor aislamiento por mm")

    return considerations


def recommend_panels(req: RecommendPanelRequest) -> RecommendPanelResponse:
    """Execute the panel recommendation pipeline."""
    if not _CATALOG and not _BMC_KB:
        raise HTTPException(503, "Data not loaded. API not ready.")

    candidates = _build_candidates()
    total_candidates = len(candidates)

    # Filter by use_case
    allowed_types = USE_CASE_TYPES.get(req.use_case, [])
    matching = [c for c in candidates if c["tipo"] in allowed_types]

    # Filter by thermal requirement
    if req.thermal_requirement is not None:
        matching = [
            c for c in matching
            if c.get("r_value") is not None and c["r_value"] >= req.thermal_requirement
        ]

    # Filter by budget
    if req.budget_max is not None:
        matching = [
            c for c in matching
            if c["price_per_m2"] * req.area_m2 <= req.budget_max
        ]

    total_matching = len(matching)
    notes: list[str] = []

    if not matching:
        notes.append(
            "No se encontraron paneles que cumplan todos los criterios. "
            "Intente relajar el presupuesto o el requerimiento térmico."
        )
        return RecommendPanelResponse(
            use_case=req.use_case,
            area_m2=req.area_m2,
            thermal_requirement=req.thermal_requirement,
            budget_max=req.budget_max,
            total_candidates=total_candidates,
            total_matching=0,
            recommendations=[],
            comparison_table=[],
            notes=notes,
        )

    # Score and rank
    for panel in matching:
        panel["score"] = _score_panel(panel, req.area_m2)

    matching.sort(key=lambda p: p["score"], reverse=True)
    top = matching[:3]

    # Build recommendations
    recommendations = []
    for i, panel in enumerate(top):
        total_cost = round(panel["price_per_m2"] * req.area_m2, 2)
        rec = PanelRecommendation(
            rank=i + 1,
            product_id=panel["product_id"],
            name=panel["name"],
            familia=panel["familia"],
            sub_familia=panel["sub_familia"],
            thickness_mm=panel["thickness_mm"],
            price_per_m2=panel["price_per_m2"],
            total_cost=total_cost,
            thermal_resistance=panel.get("r_value"),
            thermal_conductivity=panel.get("coef_termico"),
            autoportancia_m=panel.get("autoportancia_m"),
            ignifugo=panel.get("ignifugo"),
            score=panel["score"],
            score_breakdown={
                "r_value_per_usd": round((panel.get("r_value", 0) or 0) * 100 / max(panel["price_per_m2"], 0.01), 2),
                "pir_bonus": "PIR" in (panel.get("sub_familia", "") or "").upper(),
                "autoportancia_bonus": (panel.get("autoportancia_m") or 0) > 7,
            },
            advantages=_generate_advantages(panel),
            considerations=_generate_considerations(panel, req.use_case),
        )
        recommendations.append(rec)

    # Build comparison table
    comparison_table = []
    for rec in recommendations:
        comparison_table.append({
            "rank": rec.rank,
            "product": rec.name,
            "thickness": f"{rec.thickness_mm:.0f}mm",
            "R_value": rec.thermal_resistance,
            "price_m2": f"USD {rec.price_per_m2:.2f}",
            "total": f"USD {rec.total_cost:,.2f}",
            "autoportancia": f"{rec.autoportancia_m}m" if rec.autoportancia_m else "N/A",
            "fire": rec.ignifugo or "N/A",
            "score": rec.score,
        })

    # Notes
    notes.append(f"Evaluados {total_candidates} paneles, {total_matching} cumplen criterios.")
    notes.append("Score = valor R-térmico por USD — mayor score = mejor relación calidad/precio.")
    notes.append("Precios con IVA 22% incluido. BMC no realiza instalaciones.")
    if req.use_case == "camara_frigorifica":
        notes.append("Para cámaras frigoríficas se recomienda PIR por su resistencia al fuego y mejor aislamiento por mm.")

    return RecommendPanelResponse(
        use_case=req.use_case,
        area_m2=req.area_m2,
        thermal_requirement=req.thermal_requirement,
        budget_max=req.budget_max,
        total_candidates=total_candidates,
        total_matching=total_matching,
        recommendations=recommendations,
        comparison_table=comparison_table,
        notes=notes,
    )


# ─── FastAPI Route ───

@router.post(
    "/recommend_panel",
    response_model=RecommendPanelResponse,
    summary="Panel Selector — AI-powered panel recommendation",
    description=(
        "Given a use case, thermal requirement, budget, and area, returns "
        "the top 3 recommended panels ranked by price/performance ratio. "
        "Includes comparison table, advantages, and considerations for each option."
    ),
)
async def api_recommend_panel(req: RecommendPanelRequest):
    return recommend_panels(req)
