"""Pydantic models for Panelin Sheets Orchestrator API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WriteEntry(BaseModel):
    range: str = Field(..., description="A1 range notation, e.g. 'EPS_100!B6'")
    values: List[List[Any]] = Field(..., description="2-D array matching the range dimensions")


class WritePlan(BaseModel):
    job_id: str
    version: str = "1"
    writes: List[WriteEntry] = Field(default_factory=list)
    computed: Dict[str, Any] = Field(default_factory=dict)
    notes: str = ""


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


class QueueProcessRequest(BaseModel):
    limit: int = Field(default=20, ge=1, le=100, description="Max jobs to process in this batch")


class QueueProcessResponse(BaseModel):
    processed: int
    succeeded: int
    failed: int
