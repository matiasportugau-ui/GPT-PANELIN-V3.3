"""Domain service wrapper around Panelin v4 deterministic engine."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from panelin_reports.pdf_generator import build_quote_pdf
from panelin_v4.engine.classifier import OperatingMode
from panelin_v4.engine.quotation_engine import process_quotation
from panelin_v4.evaluator.sai_engine import calculate_sai
from src.core.config import Settings
from src.quotation.schemas import PanelinEngineInput


MODE_MAP: dict[str, OperatingMode] = {
    "informativo": OperatingMode.INFORMATIVO,
    "pre_cotizacion": OperatingMode.PRE_COTIZACION,
    "formal": OperatingMode.FORMAL,
}


class QuotationService:
    """Thin application service to isolate domain orchestration from transport layers."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._catalog_cache: dict[str, Any] | None = None

    def resolve_mode(self, raw_mode: str | None) -> OperatingMode:
        mode_key = (raw_mode or "pre_cotizacion").strip().lower()
        if mode_key not in MODE_MAP:
            valid = ", ".join(sorted(MODE_MAP))
            raise ValueError(f"Modo inválido '{raw_mode}'. Modos válidos: {valid}")
        return MODE_MAP[mode_key]

    def quote(self, payload: PanelinEngineInput) -> dict[str, Any]:
        mode = self.resolve_mode(payload.mode)
        result = process_quotation(
            text=payload.text,
            force_mode=mode,
            client_name=payload.client_name,
            client_phone=payload.client_phone,
            client_location=payload.client_location,
        )
        return result.to_dict()

    def validate(self, payload: PanelinEngineInput) -> dict[str, Any]:
        output = self.quote(payload)
        return {
            "mode": output["mode"],
            "classification": output["classification"],
            "request": output["request"],
            "sre": output["sre"],
            "bom": output["bom"],
            "pricing": output["pricing"],
            "validation": output["validation"],
        }

    def sai_score(self, payload: PanelinEngineInput) -> dict[str, Any]:
        mode = self.resolve_mode(payload.mode)
        quotation = process_quotation(
            text=payload.text,
            force_mode=mode,
            client_name=payload.client_name,
            client_phone=payload.client_phone,
            client_location=payload.client_location,
        )
        sai = calculate_sai(quotation)
        return {
            "quote_id": quotation.quote_id,
            "quote_status": quotation.status,
            "mode": quotation.mode,
            "sai": sai.to_dict(),
        }

    def search_products(self, query: str, max_results: int = 10) -> dict[str, Any]:
        catalog = self._load_catalog()
        terms = [term for term in query.lower().split() if term]
        results: list[dict[str, Any]] = []
        for product_id, payload in catalog.items():
            haystack = f"{product_id} {payload.get('name', '')} {payload.get('description', '')}".lower()
            if all(term in haystack for term in terms):
                results.append({"product_id": product_id, **payload})
                if len(results) >= max_results:
                    break
        return {"query": query, "count": len(results), "results": results}

    def generate_pdf(self, quote_data: dict[str, Any], file_prefix: str = "PANELIN") -> dict[str, Any]:
        output_dir = self.settings.output_pdf_dir_path
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        output_path = output_dir / f"{file_prefix}-{timestamp}.pdf"
        pdf_path = build_quote_pdf(quote_data, str(output_path))
        return {"ok": True, "path": pdf_path}

    def _load_catalog(self) -> dict[str, Any]:
        if self._catalog_cache is not None:
            return self._catalog_cache

        catalog_path = Path(self.settings.catalog_path)
        if not catalog_path.exists():
            self._catalog_cache = {}
            return self._catalog_cache

        with open(catalog_path, encoding="utf-8") as f:
            loaded = json.load(f)

        if isinstance(loaded, dict):
            self._catalog_cache = loaded
        else:
            self._catalog_cache = {}
        return self._catalog_cache

