"""API v1 router composition."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.routes.audit_jobs import router as audit_jobs_router
from app.api.routes.audit_versions import router as audit_versions_router
from app.api.routes.health import router as health_router
from app.api.routes.planned_storage import router as planned_storage_router
from app.api.routes.projects import router as projects_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(projects_router)
api_v1_router.include_router(audit_versions_router)
api_v1_router.include_router(audit_jobs_router)
api_v1_router.include_router(planned_storage_router)
