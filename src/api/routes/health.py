"""Health endpoint for Spec C API."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from src.api.schemas import HealthResponse
from src.data.database import session_scope

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    db_reachable = False
    try:
        with session_scope() as session:
            session.execute(select(1)).scalar_one()
        db_reachable = True
    except Exception:
        db_reachable = False

    return HealthResponse(status="ok", db_reachable=db_reachable)
