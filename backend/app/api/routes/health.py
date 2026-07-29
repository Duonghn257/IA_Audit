"""Health endpoints."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "operation-report-jedi-backend",
        "version": "2.0.0",
    }

