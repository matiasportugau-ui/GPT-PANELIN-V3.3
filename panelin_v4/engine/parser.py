"""
Panelin v4.0 - Input Parser
=============================

Converts free-form Spanish text into a structured QuoteRequest object.
Tolerant to noise, abbreviations, and ambiguous input.

This parser NEVER blocks. If data is missing, it marks fields as None
and sets `incomplete_fields` so downstream engines can decide what to do.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ClientInfo:
    name: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None

    def to_dict(self) -> dict:
        return {"name": self.name, "phone": self.phone, "location": self.location}


@dataclass
class ProjectGeometry:
    length_m: Optional[float] = None
    width_m: Optional[float] = None
    height_m: Optional[float] = None
    panel_count: Optional[int] = None
    panel_lengths: list[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "length_m": self.length_m,
            "width_m": self.width_m,
            "height_m": self.height_m,
            "panel_count": self.panel_count,
            "panel_lengths": self.panel_lengths,
        }


@dataclass
class QuoteRequest:
    """Canonical structured representation of a quotation request."""
    familia: Optional[str] = None
    sub_familia: Optional[str] = None
    thickness_mm: Optional[int] = None
    uso: Optional[str] = None  # techo | pared | camara | mixto
    structure_type: Optional[str] = None  # metal | hormigon | madera
    span_m: Optional[float] = None
    geometry: ProjectGeometry = field(default_factory=ProjectGeometry)
    client: ClientInfo = field(default_factory=ClientInfo)
    include_accessories: bool = True
    include_fixings: bool = True
    include_shipping: bool = False
    iva_mode: str = "incluido"
    roof_type: Optional[str] = None  # 1_agua | 2_aguas | 4_aguas | mariposa
    raw_accessories_requested: list[str] = field(default_factory=list)
    raw_text: str = ""
    incomplete_fields: list[str] = field(default_factory=list)
    assumptions_used: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "familia": self.familia,
            "sub_familia": self.sub_familia,
            "thickness_mm": self.thickness_mm,
            "uso": self.uso,
            "structure_type": self.structure_type,
            "span_m": self.span_m,
            "geometry": self.geometry.to_dict(),
            "client": self.client.to_dict(),
            "include_accessories": self.include_accessories,
            "include_fixings": self.include_fixings,
            "include_shipping": self.include_shipping,
            "iva_mode": self.iva_mode,
            "roof_type": self.roof_type,
            "raw_accessories_requested": self.raw_accessories_requested,
            "incomplete_fields": self.incomplete_fields,
            "assumptions_used": self.assumptions_used,
        }


# ────────────────────────── Regex patterns ──────────────────────────

_FAMILY_PATTERNS = {
    "ISODEC": re.compile(r"\bisodec\b", re.IGNORECASE),
    "ISOROOF": re.compile(r"\bisoroof\b", re.IGNORECASE),
    "ISOPANEL": re.compile(r"\bisopanel\b", re.IGNORECASE),
    "ISOWALL": re.compile(r"\bisowall\b", re.IGNORECASE),
    "ISOFRIG": re.compile(r"\bisofrig\b", re.IGNORECASE),
    "HIANSA": re.compile(r"\bhiansa\b", re.IGNORECASE),
}

_CORE_PATTERNS = {
    "EPS": re.compile(r"\beps\b", re.IGNORECASE),
    "PIR": re.compile(r"\bpir\b", re.IGNORECASE),
}

_THICKNESS_PATTERN = re.compile(
    r"(\d{2,3})\s*(?:mm|milimetros|milímetros)\b"
    r"|(\d{1,3})\s*(?:cm)\b"
    r"|(?:de\s+)?(\d{2,3})\s*(?:mm)?\s*(?:de\s+espesor)",
    re.IGNORECASE,
)

_PANEL_COUNT_PATTERN = re.compile(
    r"(\d+)\s*(?:panel(?:es)?|piezas?|placas?|tramos?|p\.)\b",
    re.IGNORECASE,
)

_LENGTH_PATTERN = re.compile(
    r"(?:de\s+)?(\d+[.,]?\d*)\s*(?:m(?:ts?|etros?)?)\s*(?:de\s+largo)?(?!\w)",
    re.IGNORECASE,
)

_DIMENSION_PATTERN = re.compile(
    r"(\d+[.,]?\d*)\s*(?:m(?:ts?)?)?\s*(?:(?:de\s+)?(?:largo|ancho|long))?\s*[x×]\s*(\d+[.,]?\d*)\s*(?:m(?:ts?)?)?",
    re.IGNORECASE,
)

_HEIGHT_PATTERN = re.compile(
    r"(?:alto|altura|h)\s*(?:de\s+)?(\d+[.,]?\d*)\s*(?:m(?:ts?)?)?",
    re.IGNORECASE,
)

_STRUCTURE_PATTERNS = {
    "hormigon": re.compile(r"(?:H°|\bhormigón\b|\bhormigon\b|\bloza\b|\blosa\b)", re.IGNORECASE),
    "metal": re.compile(r"\b(?:metal|metálic[ao]|acero|hierro)\b", re.IGNORECASE),
    "madera": re.compile(r"\b(?:madera|tirantes?|listones?)\b", re.IGNORECASE),
}

_ROOF_TYPE_PATTERNS = {
    "2_aguas": re.compile(r"\b(?:2|dos)\s*aguas?\b", re.IGNORECASE),
    "4_aguas": re.compile(r"\b(?:4|cuatro)\s*aguas?\b", re.IGNORECASE),
    "mariposa": re.compile(r"\bmariposa\b", re.IGNORECASE),
    "1_agua": re.compile(r"\b(?:1|una?)\s*agua\b", re.IGNORECASE),
}

_PHONE_PATTERN = re.compile(r"0?9[\s-]?\d[\s-]?\d{3}[\s-]?\d{3}")

_FLETE_PATTERN = re.compile(r"\bflete\b", re.IGNORECASE)

_PANEL_LENGTHS_PATTERN = re.compile(
    r"(\d+)\s*(?:panel(?:es)?|piezas?|placas?|tramos?|p\.?)\s+(?:de\s+)?(\d+[.,]?\d*)\s*(?:m(?:ts?|etros?)?)?",
    re.IGNORECASE,
)

_ACCESSORY_KEYWORDS = [
    "gotero", "babeta", "canalón", "canalon", "soporte", "tapa",
    "embudo", "ángulo", "angulo", "perfil u", "cumbrera", "remache",
    "tornillo", "arandela", "tortuga", "silicona", "varilla", "tuerca",
    "salchicha", "sellador", "kit anclaje",
]


def _parse_float(s: str) -> float:
    """Parse a float from Spanish text (handles comma as decimal separator)."""
    return float(s.replace(",", "."))


def _detect_familia(text: str) -> Optional[str]:
    for fam, pattern in _FAMILY_PATTERNS.items():
        if pattern.search(text):
            return fam
    return None


def _detect_subfamilia(text: str) -> Optional[str]:
    for core, pattern in _CORE_PATTERNS.items():
        if pattern.search(text):
            return core
    # Default inference by family
    return None


def _detect_thickness(text: str) -> Optional[int]:
    m = _THICKNESS_PATTERN.search(text)
    if not m:
        return None
    if m.group(1):
        return int(m.group(1))
    if m.group(2):
        cm_val = int(m.group(2))
        if cm_val <= 25:
            return cm_val * 10
        return cm_val
    if m.group(3):
        return int(m.group(3))
    return None


def _detect_uso(text: str, familia: Optional[str]) -> Optional[str]:
    text_lower = text.lower()

    if any(kw in text_lower for kw in ["techo", "cubierta", "cumbrera"]):
        return "techo"
    if any(kw in text_lower for kw in ["pared", "fachada", "muro", "habitacion", "habitación"]):
        return "pared"
    if any(kw in text_lower for kw in ["cámara", "camara", "frigoríf", "frigorif"]):
        return "camara"

    if familia:
        family_uso = {
            "ISODEC": "techo",
            "ISOROOF": "techo",
            "ISOPANEL": "pared",
            "ISOWALL": "pared",
            "ISOFRIG": "camara",
        }
        return family_uso.get(familia)

    return None


def _detect_structure(text: str) -> Optional[str]:
    for struct, pattern in _STRUCTURE_PATTERNS.items():
        if pattern.search(text):
            return struct
    return None


def _detect_roof_type(text: str) -> Optional[str]:
    for rtype, pattern in _ROOF_TYPE_PATTERNS.items():
        if pattern.search(text):
            return rtype
    return None


def _detect_panel_lengths(text: str) -> tuple[list[float], Optional[int]]:
    """Extract panel count + length specifications.

    Handles patterns like:
        '6p de 6,5 mts' -> ([6.5, 6.5, ...], 6)
        '3 de 2,30 m + 1 de 3,05 m' -> ([2.3, 2.3, 2.3, 3.05], 4)
    """
    panel_lengths: list[float] = []
    total_count = 0
    for m in _PANEL_LENGTHS_PATTERN.finditer(text):
        count = int(m.group(1))
        length = _parse_float(m.group(2))
        panel_lengths.extend([length] * count)
        total_count += count
    return panel_lengths, total_count if total_count > 0 else None


def _detect_dimensions(text: str) -> tuple[Optional[float], Optional[float]]:
    """Detect width x length pattern like '7 x 10'."""
    m = _DIMENSION_PATTERN.search(text)
    if m:
        d1 = _parse_float(m.group(1))
        d2 = _parse_float(m.group(2))
        return d1, d2
    return None, None


def _detect_accessories(text: str) -> list[str]:
    text_lower = text.lower()
    found = []
    for kw in _ACCESSORY_KEYWORDS:
        if kw in text_lower:
            found.append(kw)
    return found


def parse_request(text: str) -> QuoteRequest:
    """Parse free-form Spanish text into a structured QuoteRequest.

    This function NEVER raises. Missing data is recorded in
    `incomplete_fields` for downstream handling.
    """
    req = QuoteRequest(raw_text=text)

    req.familia = _detect_familia(text)
    req.sub_familia = _detect_subfamilia(text)
    req.thickness_mm = _detect_thickness(text)
    req.uso = _detect_uso(text, req.familia)
    req.structure_type = _detect_structure(text)
    req.roof_type = _detect_roof_type(text)

    # Default sub_familia inference
    if req.familia and not req.sub_familia:
        defaults = {
            "ISODEC": "EPS",
            "ISOROOF": "3G",
            "ISOPANEL": "EPS",
            "ISOWALL": "PIR",
            "ISOFRIG": "PIR",
        }
        inferred = defaults.get(req.familia)
        if inferred:
            req.sub_familia = inferred
            req.assumptions_used.append(f"sub_familia inferred as {inferred} from {req.familia}")

    # Panel lengths
    panel_lengths, panel_count = _detect_panel_lengths(text)
    if panel_lengths:
        req.geometry.panel_lengths = panel_lengths
        req.geometry.panel_count = len(panel_lengths)
    elif panel_count:
        req.geometry.panel_count = panel_count

    # Fallback panel count from simple pattern
    if req.geometry.panel_count is None:
        m = _PANEL_COUNT_PATTERN.search(text)
        if m:
            req.geometry.panel_count = int(m.group(1))

    # Dimensions (width x length)
    dim_w, dim_l = _detect_dimensions(text)
    if dim_w and dim_l:
        req.geometry.width_m = dim_w
        req.geometry.length_m = dim_l

    # Single length
    if not req.geometry.length_m and not req.geometry.panel_lengths:
        m = _LENGTH_PATTERN.search(text)
        if m:
            req.geometry.length_m = _parse_float(m.group(1))

    # Derive length from panel_lengths if not set
    if not req.geometry.length_m and req.geometry.panel_lengths:
        req.geometry.length_m = max(req.geometry.panel_lengths)

    # Height
    m = _HEIGHT_PATTERN.search(text)
    if m:
        req.geometry.height_m = _parse_float(m.group(1))

    # Client phone
    pm = _PHONE_PATTERN.search(text)
    if pm:
        req.client.phone = pm.group(0).replace(" ", "").replace("-", "")

    # Shipping
    req.include_shipping = bool(_FLETE_PATTERN.search(text))

    # Accessories requested
    req.raw_accessories_requested = _detect_accessories(text)

    # Check completeness
    if not req.familia:
        req.incomplete_fields.append("familia")
    if not req.thickness_mm:
        req.incomplete_fields.append("thickness_mm")
    if not req.uso:
        req.incomplete_fields.append("uso")
    if req.uso == "techo" and req.span_m is None:
        req.incomplete_fields.append("span_m")
    if not req.structure_type:
        req.incomplete_fields.append("structure_type")
    if not req.geometry.length_m and not req.geometry.panel_lengths:
        req.incomplete_fields.append("dimensions")
    if not req.geometry.width_m and not req.geometry.panel_count:
        req.incomplete_fields.append("width_or_panel_count")

    return req
