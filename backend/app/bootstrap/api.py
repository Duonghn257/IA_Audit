"""FastAPI application factory and dependency composition."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import ApiError, api_error_handler
from app.api.middleware import CorrelationIdMiddleware
from app.api.router import api_v1_router
from app.application.path_resolver import LocalPathResolver
from app.application.project_manager import ProjectManager
from app.application.run_manager import RunManager
from app.core.settings import ApiSettings, load_api_settings
from app.infrastructure.database import Database
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
    return application
