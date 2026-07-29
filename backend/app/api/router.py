"""API v1 router composition."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.projects import router as projects_router
from app.api.routes.runs import router as runs_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(projects_router)
api_v1_router.include_router(runs_router)
