"""Folder upload, project status, progress and DOCX download endpoints."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path, PurePosixPath
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse

from app.api.dependencies import get_project_manager
from app.api.errors import ApiError
from app.api.schemas.projects import (
    ProjectEventResponse,
    ProjectResponse,
)
from app.application.project_files import (
    IncomingProjectFile,
    ProjectUploadError,
)
from app.application.project_manager import ProjectManager
from app.domain.projects import ProjectNotFoundError, ProjectStatus

router = APIRouter(prefix="/projects", tags=["projects"])

ProjectManagerDependency = Annotated[
    ProjectManager,
    Depends(get_project_manager),
]


@router.post(
    "/upload",
    response_model=ProjectResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def upload_project(
    manager: ProjectManagerDependency,
    files: Annotated[list[UploadFile], File()],
    relative_paths: Annotated[list[str], Form()],
    name: Annotated[str | None, Form()] = None,
) -> ProjectResponse:
    if len(files) != len(relative_paths):
        raise ApiError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="INVALID_FOLDER_UPLOAD",
            message="Each uploaded file must have one relative path.",
        )
    project_name = (name or _infer_project_name(relative_paths)).strip()
    if not project_name:
        raise ApiError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="INVALID_PROJECT_NAME",
            message="Project name must not be empty.",
        )

    incoming = [
        IncomingProjectFile(relative_path=path, stream=upload.file)
        for path, upload in zip(relative_paths, files, strict=True)
    ]
    try:
        project = manager.submit_upload(
            name=project_name[:255],
            files=incoming,
        )
    except ProjectUploadError as exc:
        raise ApiError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="INVALID_FOLDER_UPLOAD",
            message=str(exc),
        ) from exc
    finally:
        for upload in files:
            upload.file.close()
    return ProjectResponse.from_domain(project)


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    manager: ProjectManagerDependency,
) -> list[ProjectResponse]:
    return [
        ProjectResponse.from_domain(project)
        for project in manager.list()
    ]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    manager: ProjectManagerDependency,
) -> ProjectResponse:
    return ProjectResponse.from_domain(
        _get_project_or_404(manager, project_id)
    )


@router.get(
    "/{project_id}/events",
    response_model=list[ProjectEventResponse],
)
def list_project_events(
    project_id: str,
    manager: ProjectManagerDependency,
    after_event_id: int = Query(default=0, ge=0),
) -> list[ProjectEventResponse]:
    _get_project_or_404(manager, project_id)
    return [
        ProjectEventResponse.from_domain(event)
        for event in manager.list_events(
            project_id,
            after_event_id=after_event_id,
        )
    ]


@router.get("/{project_id}/events/stream")
def stream_project_events(
    project_id: str,
    manager: ProjectManagerDependency,
    after_event_id: int = Query(default=0, ge=0),
) -> StreamingResponse:
    _get_project_or_404(manager, project_id)
    return StreamingResponse(
        _event_stream(manager, project_id, after_event_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/{project_id}/output", response_class=FileResponse)
def download_project_output(
    project_id: str,
    manager: ProjectManagerDependency,
) -> FileResponse:
    project = _get_project_or_404(manager, project_id)
    if (
        project.status != ProjectStatus.COMPLETED
        or not project.output_path
    ):
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            code="OUTPUT_NOT_READY",
            message="The project output is not ready for download.",
        )
    output_path = Path(project.output_path).resolve()
    if not output_path.is_file():
        raise ApiError(
            status_code=status.HTTP_410_GONE,
            code="OUTPUT_NOT_FOUND",
            message="The generated output file is no longer available.",
        )
    return FileResponse(
        path=output_path,
        filename=output_path.name,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
    )


async def _event_stream(
    manager: ProjectManager,
    project_id: str,
    after_event_id: int,
) -> AsyncIterator[str]:
    cursor = after_event_id
    idle_cycles = 0
    while True:
        events = manager.list_events(
            project_id,
            after_event_id=cursor,
        )
        for event in events:
            cursor = event.event_id
            payload = ProjectEventResponse.from_domain(event).model_dump(
                mode="json"
            )
            yield (
                f"id: {event.event_id}\n"
                "event: progress\n"
                f"data: {json.dumps(payload)}\n\n"
            )
        project = manager.get(project_id)
        if project.status.is_terminal and not events:
            yield "event: end\ndata: {}\n\n"
            return
        idle_cycles += 1
        if idle_cycles % 30 == 0:
            yield ": heartbeat\n\n"
        await asyncio.sleep(0.5)


def _get_project_or_404(
    manager: ProjectManager,
    project_id: str,
):
    try:
        return manager.get(project_id)
    except ProjectNotFoundError as exc:
        raise ApiError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="PROJECT_NOT_FOUND",
            message=f"Project not found: {project_id}",
        ) from exc


def _infer_project_name(relative_paths: list[str]) -> str:
    if not relative_paths:
        return "Audit Project"
    parts = PurePosixPath(
        relative_paths[0].replace("\\", "/")
    ).parts
    return parts[0].replace("_", " ").replace("-", " ") if parts else ""

