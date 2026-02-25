"""
Panelin v4.0 - Request Classifier
===================================

Classifies incoming quotation requests into types and determines
the appropriate operating mode. This is the first stage of the pipeline.

Request Types:
    - roof_system: Complete roof installation
    - wall_system: Wall/facade panel installation
    - room_complete: Full room (walls + roof)
    - accessories_only: Only accessories/profiles
    - update: Update/modify existing quotation
    - waterproofing: Waterproofing products
    - conventional_sheet: Standard metal sheets (outside core KB)
    - post_sale: Claim or post-sale issue
    - info_only: Informational query

Operating Modes:
    - informativo: Quick info, no formal quote
    - pre_cotizacion: Pre-quotation with assumptions, non-blocking
    - formal: Full formal quotation with validation
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class RequestType(str, Enum):
    ROOF_SYSTEM = "roof_system"
    WALL_SYSTEM = "wall_system"
    ROOM_COMPLETE = "room_complete"
    ACCESSORIES_ONLY = "accessories_only"
    UPDATE = "update"
    WATERPROOFING = "waterproofing"
    CONVENTIONAL_SHEET = "conventional_sheet"
    POST_SALE = "post_sale"
    INFO_ONLY = "info_only"
    MIXED = "mixed"


class OperatingMode(str, Enum):
    INFORMATIVO = "informativo"
    PRE_COTIZACION = "pre_cotizacion"
    FORMAL = "formal"


@dataclass
class ClassificationResult:
    request_type: RequestType
    operating_mode: OperatingMode
    has_roof: bool = False
    has_wall: bool = False
    has_accessories: bool = False
    is_update: bool = False
    confidence: float = 0.0
    signals: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "request_type": self.request_type.value,
            "operating_mode": self.operating_mode.value,
            "has_roof": self.has_roof,
            "has_wall": self.has_wall,
            "has_accessories": self.has_accessories,
            "is_update": self.is_update,
            "confidence": self.confidence,
            "signals": self.signals,
        }


_ROOF_KEYWORDS = [
    "isodec", "isoroof", "techo", "cubierta", "2 aguas", "dos aguas",
    "4 aguas", "cuatro aguas", "mariposa", "lucernario", "cumbrera",
    "pendiente", "canalon", "canalón", "gotero",
]

_WALL_KEYWORDS = [
    "isopanel", "isowall", "isofrig", "pared", "fachada", "muro",
    "habitacion", "habitación", "perfil u",
]

_ACCESSORY_ONLY_KEYWORDS = [
    "gotero", "babeta", "canalón", "canalon", "remache", "tornillo",
    "arandela", "tortuga", "silicona", "sellador", "varilla", "tuerca",
    "soporte", "embudo", "tapa", "ángulo", "angulo", "perfil",
    "salchicha", "kit anclaje",
]

_UPDATE_KEYWORDS = [
    "actualizar", "actualización", "actualiza", "reenviar",
    "agregar", "dividir", "solo precio", "modificar",
]

_WATERPROOFING_KEYWORDS = [
    "impermeabiliz", "rubber", "manta", "goma líquida", "goma liquida",
    "hm-rubber", "óxido", "oxido",
]

_SHEET_KEYWORDS = [
    "chapa", "cal.", "cal ", "calibre", "bc-30", "bc30",
    "hiansa", "bastidor",
]

_POST_SALE_KEYWORDS = [
    "reclamo", "oxidado", "problema", "garantía", "garantia", "defecto",
]

_FORMAL_KEYWORDS = [
    "pdf", "formal", "presupuesto oficial", "cotización formal",
    "json", "contractual",
]


def _count_matches(text_lower: str, keywords: list[str]) -> int:
    return sum(1 for kw in keywords if kw in text_lower)


def classify_request(
    text: str,
    force_mode: Optional[OperatingMode] = None,
) -> ClassificationResult:
    """Classify a quotation request text into type and operating mode.

    Args:
        text: Raw request text (Spanish, free-form).
        force_mode: Override auto-detected mode if set.

    Returns:
        ClassificationResult with type, mode, and detection signals.
    """
    text_lower = text.lower().strip()
    signals: list[str] = []

    roof_score = _count_matches(text_lower, _ROOF_KEYWORDS)
    wall_score = _count_matches(text_lower, _WALL_KEYWORDS)
    acc_score = _count_matches(text_lower, _ACCESSORY_ONLY_KEYWORDS)
    update_score = _count_matches(text_lower, _UPDATE_KEYWORDS)
    waterproof_score = _count_matches(text_lower, _WATERPROOFING_KEYWORDS)
    sheet_score = _count_matches(text_lower, _SHEET_KEYWORDS)
    post_sale_score = _count_matches(text_lower, _POST_SALE_KEYWORDS)
    formal_score = _count_matches(text_lower, _FORMAL_KEYWORDS)

    has_roof = roof_score > 0
    has_wall = wall_score > 0
    has_accessories = acc_score > 0
    is_update = update_score > 0

    if has_roof:
        signals.append(f"roof_keywords={roof_score}")
    if has_wall:
        signals.append(f"wall_keywords={wall_score}")
    if has_accessories:
        signals.append(f"accessory_keywords={acc_score}")
    if is_update:
        signals.append(f"update_keywords={update_score}")

    # Determine request type by priority
    request_type = RequestType.INFO_ONLY
    confidence = 0.5

    if post_sale_score >= 2:
        request_type = RequestType.POST_SALE
        confidence = 0.9
        signals.append("post_sale_detected")
    elif is_update:
        request_type = RequestType.UPDATE
        confidence = 0.85
        signals.append("update_detected")
    elif waterproof_score >= 2:
        request_type = RequestType.WATERPROOFING
        confidence = 0.85
        signals.append("waterproofing_detected")
    elif sheet_score >= 2 and not has_roof and not has_wall:
        request_type = RequestType.CONVENTIONAL_SHEET
        confidence = 0.8
        signals.append("conventional_sheet_detected")
    elif has_roof and has_wall:
        request_type = RequestType.ROOM_COMPLETE
        confidence = 0.8
        signals.append("room_complete: roof+wall")
    elif has_roof:
        request_type = RequestType.ROOF_SYSTEM
        confidence = 0.85
        signals.append("roof_system_detected")
    elif has_wall:
        request_type = RequestType.WALL_SYSTEM
        confidence = 0.85
        signals.append("wall_system_detected")
    elif has_accessories and not has_roof and not has_wall:
        request_type = RequestType.ACCESSORIES_ONLY
        confidence = 0.8
        signals.append("accessories_only_detected")
    elif sheet_score >= 1:
        request_type = RequestType.CONVENTIONAL_SHEET
        confidence = 0.7
        signals.append("conventional_sheet_maybe")

    # Mixed type detection
    if has_roof and has_wall and has_accessories:
        request_type = RequestType.MIXED
        confidence = 0.75
        signals.append("mixed_type_detected")

    # Determine operating mode
    if force_mode:
        mode = force_mode
        signals.append(f"mode_forced={force_mode.value}")
    elif formal_score > 0:
        mode = OperatingMode.FORMAL
        signals.append("formal_mode_from_keywords")
    elif is_update:
        mode = OperatingMode.PRE_COTIZACION
        signals.append("pre_mode_from_update")
    elif request_type == RequestType.ACCESSORIES_ONLY:
        mode = OperatingMode.PRE_COTIZACION
        signals.append("pre_mode_for_accessories")
    elif request_type == RequestType.INFO_ONLY:
        mode = OperatingMode.INFORMATIVO
        signals.append("info_mode_default")
    else:
        mode = OperatingMode.PRE_COTIZACION
        signals.append("pre_mode_default")

    return ClassificationResult(
        request_type=request_type,
        operating_mode=mode,
        has_roof=has_roof,
        has_wall=has_wall,
        has_accessories=has_accessories,
        is_update=is_update,
        confidence=confidence,
        signals=signals,
    )
