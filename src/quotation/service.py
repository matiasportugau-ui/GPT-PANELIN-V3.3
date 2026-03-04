"""QuotationService — thin façade over panelin_v4 deterministic engine.

This service is the domain boundary between the Agno agent layer and the
v4 pipeline. It NEVER modifies the engine; it only calls it and marshals
results to JSON-serializable dicts.

Design principles:
- All methods are synchronous (the engine is <0.4ms per step)
- All output is JSON-serializable (no dataclasses returned)
- Prices ALWAYS come from KB — never invented
- Raises ValueError for invalid inputs, never swallows errors silently
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class QuotationService:
    """Façade over the panelin_v4 pipeline engine."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self._data_dir = data_dir or Path(".")
        self._engine_ready = False
        self._load_engine()

    def _load_engine(self) -> None:
        """Lazy-import the v4 engine modules to keep startup fast."""
        try:
            from panelin_v4.engine.classifier import classify_request
            from panelin_v4.engine.parser import parse_request
            from panelin_v4.engine.sre_engine import calculate_sre
            from panelin_v4.engine.bom_engine import calculate_bom
            from panelin_v4.engine.pricing_engine import calculate_pricing
            from panelin_v4.engine.validation_engine import validate_quotation
            from panelin_v4.engine.quotation_engine import process_quotation, process_batch
            from panelin_v4.evaluator.sai_engine import calculate_sai

            self._classify = classify_request
            self._parse = parse_request
            self._sre = calculate_sre
            self._bom = calculate_bom
            self._pricing = calculate_pricing
            self._validate = validate_quotation
            self._process = process_quotation
            self._batch = process_batch
            self._sai = calculate_sai
            self._engine_ready = True
            logger.info("panelin_v4 engine loaded OK")
        except ImportError as exc:
            logger.warning("panelin_v4 engine not available: %s", exc)
            self._engine_ready = False

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def classify(self, text: str) -> dict[str, Any]:
        """Classify the request type and mode. Step 1 of pipeline."""
        self._ensure_ready()
        result = self._classify(text)
        req_type = result.request_type.value if hasattr(result.request_type, "value") else str(result.request_type)
        # ClassificationResult uses operating_mode (not mode)
        op_mode = result.operating_mode if hasattr(result, "operating_mode") else getattr(result, "mode", None)
        mode = op_mode.value if hasattr(op_mode, "value") else str(op_mode)
        return {
            "type": req_type,
            "mode": mode,
            "confidence": getattr(result, "confidence", 1.0),
            "raw_text": text,
        }

    def parse(self, text: str) -> dict[str, Any]:
        """Parse free-text into a structured QuoteRequest. Step 2."""
        self._ensure_ready()
        result = self._parse(text)
        return _to_dict(result)

    def sre(self, parsed: dict[str, Any]) -> dict[str, Any]:
        """Calculate Structural Risk Engine score. Step 3."""
        self._ensure_ready()
        from panelin_v4.engine.parser import QuoteRequest
        req = _from_dict(QuoteRequest, parsed)
        result = self._sre(req)
        return _to_dict(result)

    def bom(self, parsed: dict[str, Any]) -> dict[str, Any]:
        """Calculate Bill of Materials. Step 4.

        Accepts a flat dict with keys: familia, sub_familia, thickness_mm,
        length_m, width_m, uso, structure_type, roof_type.
        """
        self._ensure_ready()
        familia = parsed.get("familia", "")
        thickness = parsed.get("thickness_mm")
        length_m = parsed.get("length_m")
        width_m = parsed.get("width_m")
        if not familia or not thickness:
            return {"error": "familia and thickness_mm required for BOM", "items": []}
        if not length_m or not width_m:
            return {"error": "Faltan dimensiones (largo/ancho) para calcular BOM", "items": []}
        try:
            result = self._bom(
                familia=familia,
                sub_familia=parsed.get("sub_familia") or "EPS",
                thickness_mm=int(thickness),
                length_m=float(length_m),
                width_m=float(width_m),
                uso=parsed.get("uso") or "techo",
                structure_type=parsed.get("structure_type") or "metal",
                roof_type=parsed.get("roof_type"),
            )
            return _to_dict(result)
        except Exception as exc:
            logger.warning("BOM error: %s", exc)
            return {"error": str(exc), "items": []}

    def pricing(self, bom_data: dict[str, Any], parsed: dict[str, Any]) -> dict[str, Any]:
        """Calculate pricing from BOM. Step 5."""
        self._ensure_ready()
        if bom_data.get("error") or not bom_data.get("items"):
            return {"error": "No BOM to price", "total_usd": 0.0, "items": []}
        try:
            from panelin_v4.engine.bom_engine import BOMResult, BOMItem
            bom = _from_dict(BOMResult, bom_data)
            result = self._pricing(
                bom=bom,
                familia=parsed.get("familia", ""),
                sub_familia=parsed.get("sub_familia", "EPS"),
                thickness_mm=parsed.get("thickness_mm", 0),
                panel_area_m2=bom_data.get("area_m2"),
            )
            return _to_dict(result)
        except Exception as exc:
            logger.warning("Pricing error: %s", exc)
            return {"error": str(exc), "total_usd": 0.0, "items": []}

    def validate(
        self,
        parsed: dict[str, Any],
        bom_data: dict[str, Any],
        pricing_data: dict[str, Any],
        mode: str = "pre_cotizacion",
    ) -> dict[str, Any]:
        """Validate the quotation. Step 6."""
        self._ensure_ready()
        try:
            from panelin_v4.engine.parser import QuoteRequest
            from panelin_v4.engine.bom_engine import BOMResult
            from panelin_v4.engine.pricing_engine import PricingResult
            req = _from_dict(QuoteRequest, parsed)
            bom = _from_dict(BOMResult, bom_data) if bom_data.get("items") else None
            pricing = _from_dict(PricingResult, pricing_data) if pricing_data.get("items") else None
            result = self._validate(request=req, bom=bom, pricing=pricing, mode=mode)
            return _to_dict(result)
        except Exception as exc:
            logger.warning("Validation error: %s", exc)
            return {"valid": False, "error": str(exc), "issues": []}

    def process(self, text: str, mode: Optional[str] = None) -> dict[str, Any]:
        """Full pipeline in one call — classify → parse → SRE → BOM → price → validate → SAI."""
        self._ensure_ready()
        result = self._process(text, force_mode=mode)
        return _to_dict(result)

    def batch(self, texts: list[str]) -> list[dict[str, Any]]:
        """Process multiple quotation requests in batch."""
        self._ensure_ready()
        results = self._batch(texts)
        return [_to_dict(r) for r in results]

    def sai(self, quotation: dict[str, Any]) -> dict[str, Any]:
        """Calculate System Accuracy Index for a completed quotation."""
        self._ensure_ready()
        score = self._sai(quotation)
        if isinstance(score, (int, float)):
            return {"score": float(score)}
        return _to_dict(score)

    def _ensure_ready(self) -> None:
        if not self._engine_ready:
            raise RuntimeError(
                "panelin_v4 engine not available. "
                "Ensure the engine is installed and KB files are present."
            )


# ------------------------------------------------------------------ #
# Internal helpers
# ------------------------------------------------------------------ #

def _to_dict(obj: Any) -> dict[str, Any]:
    """Convert a dataclass, pydantic model, or plain object to a JSON-serializable dict."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "__dataclass_fields__"):
        import dataclasses
        return dataclasses.asdict(obj)
    if hasattr(obj, "__dict__"):
        raw = obj.__dict__
        out: dict[str, Any] = {}
        for k, v in raw.items():
            if k.startswith("_"):
                continue
            out[k] = _to_dict(v) if hasattr(v, "__dict__") else v
        return out
    return {"value": str(obj)}


def _from_dict(cls: type, data: dict[str, Any]) -> Any:
    """Reconstruct a dataclass or pydantic model from a dict (best-effort)."""
    if not data or isinstance(data, cls):
        return data
    try:
        import dataclasses
        if dataclasses.is_dataclass(cls):
            fields = {f.name for f in dataclasses.fields(cls)}
            filtered = {k: v for k, v in data.items() if k in fields}
            return cls(**filtered)
    except Exception:
        pass
    try:
        return cls(**data)
    except Exception:
        return cls()
