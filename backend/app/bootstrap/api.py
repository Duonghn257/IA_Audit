"""FastAPI application factory and dependency composition."""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.errors import ApiError, api_error_handler
from app.api.middleware import CorrelationIdMiddleware
from app.api.router import api_v1_router
from app.api.routes.auth import callback_alias_router
from app.application.audit_intake_service import AuditIntakeService
from app.application.audit_workspace_service import AuditWorkspaceService
from app.application.auth_service import AuthService
from app.application.discovery_service import (
    DiscoveryEngine,
    DiscoveryService,
    UnavailableDiscoveryEngine,
)
from app.application.path_resolver import LocalPathResolver
from app.application.project_manager import ProjectManager
from app.application.run_manager import RunManager
from app.core.settings import ApiSettings, load_api_settings
from app.infrastructure.audit_intake_repository import (
    SqlAlchemyAuditIntakeRepository,
)
from app.infrastructure.audit_repository import SqlAlchemyAuditRepository
from app.infrastructure.auth_repository import SqlAlchemyAuthRepository
from app.infrastructure.database import Database
from app.infrastructure.google_oauth import GoogleOAuthClient
from app.infrastructure.local_intake_storage import (
    LocalAuditIntakeStorage,
)
from app.infrastructure.project_repository import (
    SqlAlchemyProjectRepository,
)
from app.infrastructure.project_storage import LocalProjectStorage
from app.infrastructure.run_store import InMemoryRunStore


def create_app(
    *,
    settings: ApiSettings | None = None,
    run_manager: RunManager | None = None,
    project_manager: ProjectManager | None = None,
    audit_workspace_service: AuditWorkspaceService | None = None,
    audit_intake_service: AuditIntakeService | None = None,
    discovery_service: DiscoveryService | None = None,
    discovery_engine: DiscoveryEngine | None = None,
    auth_service: AuthService | None = None,
    google_oauth_client: GoogleOAuthClient | None = None,
) -> FastAPI:
    runtime_settings = settings or load_api_settings()
    runtime_manager = run_manager or RunManager(
        store=InMemoryRunStore(),
        max_workers=runtime_settings.run_workers,
    )
    database = None
    if project_manager is None:
        database = Database(runtime_settings.database_url)
        database.create_schema()
        project_repository = SqlAlchemyProjectRepository(
            database.sessions
        )
        project_storage = LocalProjectStorage(
            runtime_settings.storage_root,
            max_files=runtime_settings.upload_max_files,
            max_total_bytes=runtime_settings.upload_max_bytes,
        )
        runtime_project_manager = ProjectManager(
            repository=project_repository,
            storage=project_storage,
            raw_retention_days=runtime_settings.raw_retention_days,
            max_workers=runtime_settings.run_workers,
        )
    else:
        runtime_project_manager = project_manager

    if audit_workspace_service is None:
        if database is None:
            database = Database(runtime_settings.database_url)
            database.create_schema()
        runtime_audit_workspace_service = AuditWorkspaceService(
            SqlAlchemyAuditRepository(database.sessions)
        )
    else:
        runtime_audit_workspace_service = audit_workspace_service

    if audit_intake_service is None:
        if database is None:
            database = Database(runtime_settings.database_url)
            database.create_schema()
        runtime_audit_intake_service = AuditIntakeService(
            SqlAlchemyAuditIntakeRepository(database.sessions),
            LocalAuditIntakeStorage(
                runtime_settings.storage_root / "uat-intake"
            ),
            max_files=runtime_settings.upload_max_files,
            max_total_bytes=runtime_settings.upload_max_bytes,
        )
    else:
        runtime_audit_intake_service = audit_intake_service

    if discovery_service is None:
        if database is None:
            database = Database(runtime_settings.database_url)
            database.create_schema()
        runtime_discovery_service = DiscoveryService(
            SqlAlchemyAuditRepository(database.sessions),
            LocalAuditIntakeStorage(
                runtime_settings.storage_root / "uat-intake"
            ),
            discovery_engine or UnavailableDiscoveryEngine(),
        )
    else:
        runtime_discovery_service = discovery_service

    if database is None:
        database = Database(runtime_settings.database_url)
        database.create_schema()
    runtime_auth_service = auth_service or AuthService(
        SqlAlchemyAuthRepository(database.sessions),
        session_ttl_hours=runtime_settings.auth_session_ttl_hours,
    )
    runtime_google_oauth_client = google_oauth_client
    if runtime_google_oauth_client is None and runtime_settings.google_auth_enabled:
        runtime_google_oauth_client = GoogleOAuthClient(
            client_id=runtime_settings.google_client_id or "",
            client_secret=runtime_settings.google_client_secret or "",
            redirect_uri=runtime_settings.google_redirect_uri or "",
            allowed_domains=runtime_settings.google_allowed_domains,
        )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        project_service = app.state.project_manager
        if hasattr(project_service, "cleanup_expired_inputs"):
            project_service.cleanup_expired_inputs()
        yield
        manager = app.state.run_manager
        if hasattr(manager, "shutdown"):
            manager.shutdown()
        if hasattr(project_service, "shutdown"):
            project_service.shutdown()
        if app.state.database is not None:
            app.state.database.dispose()

    application = FastAPI(
        title="Operation Report Jedi API",
        version="2.0.0",
        lifespan=lifespan,
    )
    application.state.settings = runtime_settings
    application.state.run_manager = runtime_manager
    application.state.project_manager = runtime_project_manager
    application.state.audit_workspace_service = (
        runtime_audit_workspace_service
    )
    application.state.audit_intake_service = (
        runtime_audit_intake_service
    )
    application.state.discovery_service = runtime_discovery_service
    application.state.auth_service = runtime_auth_service
    application.state.google_oauth_client = runtime_google_oauth_client
    application.state.database = database
    application.state.path_resolver = LocalPathResolver(runtime_settings)
    application.add_exception_handler(ApiError, api_error_handler)
    application.add_middleware(CorrelationIdMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(runtime_settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_v1_router)
    application.include_router(callback_alias_router)
    tests_ui_root = runtime_settings.backend_root / "tests-ui"
    if tests_ui_root.is_dir():
        application.mount(
            "/tests-ui",
            StaticFiles(directory=tests_ui_root, html=True),
            name="tests-ui",
        )
    return application
