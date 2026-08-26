"""Immutable source tree endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.audit_errors import audit_api_errors
from app.api.dependencies import get_audit_workspace_service
from app.api.schemas.audit_sources import SourceTreeResponse
from app.application.audit_workspace_service import AuditWorkspaceService


router = APIRouter(prefix="/projects/{project_id}", tags=["audit-workspace"])
AuditServiceDependency = Annotated[
    AuditWorkspaceService, Depends(get_audit_workspace_service)
]


@router.get("/source-documents", response_model=SourceTreeResponse)
def get_source_documents(
    project_id: str,
    service: AuditServiceDependency,
) -> SourceTreeResponse:
    with audit_api_errors():
        return SourceTreeResponse.from_domain(service.get_source_tree(project_id))
