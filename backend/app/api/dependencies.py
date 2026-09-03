"""FastAPI dependency accessors."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, Request, status

from app.api.errors import ApiError
from app.application.audit_execution_service import AuditExecutionService
from app.application.audit_intake_service import AuditIntakeService
from app.application.audit_workspace_service import AuditWorkspaceService
from app.application.central_knowledge_service import CentralKnowledgeService
from app.application.auth_service import AuthService
from app.application.discovery_service import DiscoveryService
from app.application.path_resolver import LocalPathResolver
from app.application.project_manager import ProjectManager
from app.application.run_manager import RunManager
from app.core.settings import ApiSettings
from app.domain.auth import AuthUser
from app.domain.projects import ProjectNotFoundError, ProjectRecord
from app.infrastructure.google_oauth import GoogleOAuthClient


@dataclass(frozen=True)
class AuthPrincipal:
    user: AuthUser
    csrf_token: str
    session_id: str | None
    expires_at: datetime | None


def get_settings(request: Request) -> ApiSettings:
    return request.app.state.settings


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


def get_google_oauth_client(request: Request) -> GoogleOAuthClient | None:
    return request.app.state.google_oauth_client


def get_current_principal(
    request: Request,
    settings: Annotated[ApiSettings, Depends(get_settings)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthPrincipal:
    if not settings.google_auth_enabled:
        now = datetime.now(timezone.utc)
        return AuthPrincipal(
            user=AuthUser(
                user_id="uat_shared_user",
                provider="UAT_SHARED",
                provider_subject="uat_shared_user",
                email="uat-shared@localhost",
                email_verified=True,
                display_name="UAT shared user",
                picture_url=None,
                hosted_domain=None,
                created_at=now,
                last_login_at=now,
            ),
            csrf_token="",
            session_id=None,
            expires_at=None,
        )
    session = auth_service.authenticate(request.cookies.get(settings.auth_cookie_name))
    if session is None:
        raise ApiError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="AUTH_REQUIRED",
            message="Sign in is required to access this resource.",
        )
    return AuthPrincipal(
        user=session.user,
        csrf_token=session.csrf_token,
        session_id=session.session_id,
        expires_at=session.expires_at,
    )


def require_authenticated_user(
    principal: Annotated[AuthPrincipal, Depends(get_current_principal)],
) -> AuthPrincipal:
    return principal


def require_csrf(
    request: Request,
    settings: Annotated[ApiSettings, Depends(get_settings)],
    principal: Annotated[AuthPrincipal, Depends(get_current_principal)],
) -> None:
    if not settings.google_auth_enabled or request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    supplied = request.headers.get("X-CSRF-Token", "")
    if not supplied or not secrets.compare_digest(supplied, principal.csrf_token):
        raise ApiError(
            status_code=status.HTTP_403_FORBIDDEN,
            code="CSRF_TOKEN_INVALID",
            message="A valid CSRF token is required for this request.",
        )


def get_run_manager(request: Request) -> RunManager:
    return request.app.state.run_manager


def get_path_resolver(request: Request) -> LocalPathResolver:
    return request.app.state.path_resolver


def get_project_manager(request: Request) -> ProjectManager:
    return request.app.state.project_manager


def require_owned_project(
    project_id: str,
    principal: Annotated[AuthPrincipal, Depends(get_current_principal)],
    manager: Annotated[ProjectManager, Depends(get_project_manager)],
) -> ProjectRecord:
    try:
        return manager.get(
            project_id,
            owner_user_id=principal.user.user_id,
        )
    except ProjectNotFoundError as exc:
        raise ApiError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="PROJECT_NOT_FOUND",
            message=f"Project not found: {project_id}",
        ) from exc


def get_audit_intake_service(request: Request) -> AuditIntakeService:
    return request.app.state.audit_intake_service


def get_audit_workspace_service(request: Request) -> AuditWorkspaceService:
    return request.app.state.audit_workspace_service


def get_discovery_service(request: Request) -> DiscoveryService:
    return request.app.state.discovery_service


def get_audit_execution_service(
    request: Request,
) -> AuditExecutionService:
    return request.app.state.audit_execution_service


def get_central_knowledge_service(
    request: Request,
) -> CentralKnowledgeService:
    return request.app.state.central_knowledge_service


SettingsDependency = Annotated[ApiSettings, Depends(get_settings)]
AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
GoogleOAuthDependency = Annotated[
    GoogleOAuthClient | None,
    Depends(get_google_oauth_client),
]
CurrentPrincipalDependency = Annotated[
    AuthPrincipal,
    Depends(get_current_principal),
]
