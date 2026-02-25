"""Pydantic models for Panelin Sheets Orchestrator API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────────────
# Core write plan models
# ──────────────────────────────────────────────────────────────────────

class WriteEntry(BaseModel):
    range: str = Field(..., description="A1 range notation, e.g. 'EPS_100!B6'")
    values: List[List[Any]] = Field(..., description="2-D array matching the range dimensions")


class WritePlan(BaseModel):
    job_id: str
    version: str = "1"
    writes: List[WriteEntry] = Field(default_factory=list)
    computed: Dict[str, Any] = Field(default_factory=dict)
    notes: str = ""


# ──────────────────────────────────────────────────────────────────────
# /v1/fill
# ──────────────────────────────────────────────────────────────────────

class FillRequest(BaseModel):
    job_id: str = Field(..., description="Unique job identifier for idempotency")
    template_id: str = Field(..., description="Template name (without .json extension)")
    spreadsheet_id: str = Field(..., description="Google Sheets spreadsheet ID")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Data to fill into the sheet")
    dry_run: bool = Field(default=False, description="If True, generate plan but do not write")


class FillResponse(BaseModel):
    job_id: str
    status: str
    applied: bool
    writes_count: int = 0
    total_updated_cells: int = 0
    notes: str = ""
    write_plan: Optional[WritePlan] = None
    validation: Optional[Dict[str, Any]] = None


# ──────────────────────────────────────────────────────────────────────
# /v1/queue/process
# ──────────────────────────────────────────────────────────────────────

class QueueProcessRequest(BaseModel):
    limit: int = Field(default=20, ge=1, le=100, description="Max jobs to process in this batch")


class QueueProcessResponse(BaseModel):
    processed: int
    succeeded: int
    failed: int
    duration_ms: Optional[float] = None


# ──────────────────────────────────────────────────────────────────────
# /v1/read
# ──────────────────────────────────────────────────────────────────────

class ReadRequest(BaseModel):
    spreadsheet_id: str = Field(..., description="Google Sheets spreadsheet ID")
    ranges: List[str] = Field(..., min_length=1, description="A1 ranges to read")


class ReadResponse(BaseModel):
    spreadsheet_id: str
    value_ranges: List[Dict[str, Any]] = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────
# /v1/validate
# ──────────────────────────────────────────────────────────────────────

class ValidateRequest(BaseModel):
    product_family: str = Field(..., description="e.g. ISODEC_EPS")
    thickness_mm: int = Field(..., ge=30, le=250)
    length_m: float = Field(..., gt=0)
    width_m: float = Field(..., gt=0)
    usage: str = Field(default="techo", description="techo | pared | camara")
    structure: str = Field(default="metal", description="metal | hormigon")
    safety_margin: float = Field(default=0.15, ge=0, le=0.5)


class ValidateResponse(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    bom_summary: Dict[str, Any] = Field(default_factory=dict)


# ──────────────────────────────────────────────────────────────────────
# /v1/templates
# ──────────────────────────────────────────────────────────────────────

class TemplateInfo(BaseModel):
    template_id: str
    sheet_name: str
    writes_allowlist: List[str] = Field(default_factory=list)
    read_ranges: List[str] = Field(default_factory=list)
    hints: Dict[str, Any] = Field(default_factory=dict)


class TemplateListResponse(BaseModel):
    templates: List[TemplateInfo]
    count: int


# ──────────────────────────────────────────────────────────────────────
# /v1/jobs/{job_id}
# ──────────────────────────────────────────────────────────────────────

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    payload_hash: Optional[str] = None
    total_updated_cells: Optional[int] = None
    error: Optional[str] = None
