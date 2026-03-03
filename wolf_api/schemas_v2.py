"""
Panelin Wolf API v2 — Pydantic Schemas for Smart Quote Engine
==============================================================

All request/response models for the /v2/smart_quote endpoint.
Uses strict Field validators to ensure data integrity before
any calculation occurs.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class SmartQuoteRequest(BaseModel):
    """Request body for POST /v2/smart_quote.

    The GPT resolves product_id from user intent and forwards dimensions.
    The engine does ALL math — BOM, pricing, discounts, waste, taxes.
    """

    product_id: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Product ID (e.g. ISODEC_EPS_100mm, IROOF30, ISOPANEL_EPS_50mm)",
        examples=["ISODEC_EPS_100mm", "ISOPANEL_EPS_50mm", "IROOF30"],
    )
    length_m: float = Field(
        ...,
        gt=0,
        le=50.0,
        description="Length dimension in meters",
    )
    width_m: float = Field(
        ...,
        gt=0,
        le=50.0,
        description="Width dimension in meters",
    )
    quantity: int = Field(
        1,
        ge=1,
        le=5000,
        description="Number of identical areas to quote",
    )
    include_accessories: bool = Field(
        True,
        description="Include flashings/profiles (goteros, babetas) in BOM",
    )
    include_fixings: bool = Field(
        True,
        description="Include fixation hardware (varillas, tuercas, arandelas) in BOM",
    )
    include_sealant: bool = Field(
        True,
        description="Include sealant products (silicona, cinta butilo) in BOM",
    )
    discount_percent: float = Field(
        0.0,
        ge=0,
        le=30,
        description="Manual discount percentage (0-30%). Volume discounts are applied automatically on top.",
    )
    include_tax: bool = Field(
        True,
        description="Include IVA 22% in totals. Catalog prices already include IVA.",
    )
    installation_type: Literal["techo", "pared"] = Field(
        "techo",
        description="Installation type: 'techo' (roof) or 'pared' (wall/facade)",
    )

    @field_validator("product_id")
    @classmethod
    def normalize_product_id(cls, v: str) -> str:
        return v.strip()

    @model_validator(mode="after")
    def validate_dimensions(self) -> "SmartQuoteRequest":
        area = self.length_m * self.width_m * self.quantity
        if area < 0.25:
            raise ValueError(
                f"Total area too small: {area:.2f} m². Minimum is 0.25 m²."
            )
        if area > 50000:
            raise ValueError(
                f"Total area too large: {area:.0f} m². Maximum is 50,000 m². "
                f"Contact sales team for projects of this scale."
            )
        return self


class LineItem(BaseModel):
    """Single line item in a quotation — a product with quantity and pricing."""

    product_id: str = Field(..., description="Product SKU or ID")
    name: str = Field(..., description="Human-readable product name")
    category: Literal[
        "panel", "fixing", "sealant", "flashing", "accessory"
    ] = Field(..., description="Item category for grouping")
    quantity: int = Field(..., ge=0, description="Quantity needed")
    unit: str = Field(..., description="Unit of measure (m², unid, tubo)")
    unit_price: float = Field(..., ge=0, description="Unit price USD (IVA included)")
    subtotal: float = Field(..., ge=0, description="quantity × unit_price")


class SmartQuoteResponse(BaseModel):
    """Complete quotation response from POST /v2/smart_quote.

    Contains the full BOM with individually priced line items,
    volume/manual discounts, waste factor, IVA breakdown, and totals.
    """

    quote_id: str = Field(
        ...,
        description="Unique quotation ID (format: SQ-YYYYMMDD-XXXXXXXX)",
        examples=["SQ-20260303-A1B2C3D4"],
    )
    product_id: str = Field(..., description="Main panel product quoted")
    product_name: str = Field(..., description="Main panel product name")
    area_m2: float = Field(..., ge=0, description="Total area in m²")
    quantity: int = Field(..., ge=1, description="Number of areas")
    installation_type: str = Field(..., description="techo or pared")

    line_items: List[LineItem] = Field(
        ..., description="Complete BOM with all line items priced"
    )

    subtotal: float = Field(
        ..., ge=0, description="Sum of all line items before discounts"
    )
    volume_discount_percent: float = Field(
        0.0,
        ge=0,
        description="Automatic volume discount (5%/10%/15% by area)",
    )
    volume_discount_amount: float = Field(
        0.0, ge=0, description="Volume discount in USD"
    )
    manual_discount_percent: float = Field(
        0.0, ge=0, description="Manual discount from request"
    )
    manual_discount_amount: float = Field(
        0.0, ge=0, description="Manual discount in USD"
    )
    discount_amount: float = Field(
        0.0, ge=0, description="Total discount (volume + manual)"
    )
    after_discount: float = Field(
        ..., ge=0, description="Subtotal minus all discounts"
    )

    waste_factor_percent: float = Field(
        7.0, description="Material waste factor (default 7%)"
    )
    waste_cost: float = Field(
        ..., ge=0, description="Additional cost for waste material"
    )

    iva_rate: float = Field(0.22, description="IVA rate (22% Uruguay)")
    iva_included: bool = Field(
        True,
        description="Whether IVA is included in prices (always True — catalog prices include IVA)",
    )
    iva_amount: float = Field(
        ..., description="IVA amount (informational — already in prices)"
    )

    total: float = Field(..., ge=0, description="Final total USD")

    estimated_install_hours: float = Field(
        ...,
        ge=0,
        description="Estimated installation hours (reference only — BMC does not install)",
    )
    valid_until: str = Field(
        ...,
        description="Quote validity date (ISO 8601, 10 days from generation)",
    )

    currency: str = Field("USD", description="Currency code")
    notes: List[str] = Field(
        default_factory=list,
        description="Additional notes, warnings, or recommendations",
    )

    @staticmethod
    def generate_quote_id() -> str:
        """Generate a unique quote ID: SQ-YYYYMMDD-XXXXXXXX."""
        now = datetime.now(timezone.utc)
        return f"SQ-{now.strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}"

    @staticmethod
    def calculate_valid_until() -> str:
        """Calculate validity: 10 days from now, ISO 8601."""
        return (
            datetime.now(timezone.utc) + timedelta(days=10)
        ).isoformat()
