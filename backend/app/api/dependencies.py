"""FastAPI dependency accessors."""
from __future__ import annotations

from fastapi import Request

from app.application.audit_intake_service import AuditIntakeService
from app.application.audit_workspace_service import AuditWorkspaceService
from app.application.path_resolver import LocalPathResolver
from app.application.project_manager import ProjectManager
from app.application.run_manager import RunManager


def get_run_manager(request: Request) -> RunManager:
    return request.app.state.run_manager


def get_path_resolver(request: Request) -> LocalPathResolver:
    return request.app.state.path_resolver


def get_project_manager(request: Request) -> ProjectManager:
    return request.app.state.project_manager


def get_audit_intake_service(
    request: Request,
) -> AuditIntakeService:
    return request.app.state.audit_intake_service


def get_audit_workspace_service(request: Request) -> AuditWorkspaceService:
    return request.app.state.audit_workspace_service
