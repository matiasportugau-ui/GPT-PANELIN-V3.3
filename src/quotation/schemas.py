"""Pydantic schemas for Panelin quotation flows."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PanelinEngineInput(BaseModel):
    text: str = Field(..., min_length=1)
    mode: str = Field(default="pre_cotizacion")
    client_name: str | None = None
    client_phone: str | None = None
    client_location: str | None = None
    session_id: str | None = None
    user_id: str | None = None


class PanelinWorkflowResponse(BaseModel):
    ok: bool = True
    session_id: str
    quote: dict[str, Any]
    response_text: str


class ProductSearchInput(BaseModel):
    query: str = Field(..., min_length=2)
    max_results: int = Field(default=10, ge=1, le=50)

