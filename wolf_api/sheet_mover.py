"""Legacy sheet mover endpoints.

These endpoints are preserved for backward compatibility while the workflow is
migrated to Agno-native orchestration.
"""

from __future__ import annotations

import hmac
import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def verify_api_key(api_key: str | None = Security(api_key_header)) -> str:
    expected = os.getenv("WOLF_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="WOLF_API_KEY not configured")
    if not api_key or not hmac.compare_digest(api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


class MoveResult(BaseModel):
    action: str
    rows_moved: int
    details: List[str]


router = APIRouter(tags=["Sheet Mover"])


@router.post("/cotizaciones/mover_esperando", response_model=MoveResult)
async def mover_a_esperando(_: str = Depends(verify_api_key)) -> MoveResult:
    return MoveResult(
        action="mover_esperando",
        rows_moved=0,
        details=["Operación deshabilitada temporalmente: migrando a workflows Agno."],
    )


@router.post("/cotizaciones/scan_admin", response_model=MoveResult)
async def scan_admin(_: str = Depends(verify_api_key)) -> MoveResult:
    return MoveResult(
        action="scan_admin",
        rows_moved=0,
        details=["Operación deshabilitada temporalmente: migrando a workflows Agno."],
    )
