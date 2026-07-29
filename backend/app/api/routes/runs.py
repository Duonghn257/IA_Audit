"""Audit-run command, query and progress endpoints."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_path_resolver, get_run_manager
from app.api.errors import ApiError
from app.api.schemas.runs import (
    CreateRunRequest,
    RunEventResponse,
    RunResponse,
)
from app.application.path_resolver import (
    LocalPathResolver,
    PathValidationError,
)
from app.application.run_manager import RunManager
from app.domain.runs import RunNotFoundError

router = APIRouter(prefix="/runs", tags=["runs"])

RunManagerDependency = Annotated[RunManager, Depends(get_run_manager)]
PathResolverDependency = Annotated[
    LocalPathResolver,
    Depends(get_path_resolver),
]


@router.post(
    "",
    response_model=RunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_run(
    payload: CreateRunRequest,
    manager: RunManagerDependency,
    resolver: PathResolverDependency,
) -> RunResponse:
    try:
        request = resolver.resolve_run_request(
            project_path=payload.project_path,
            issues_path=payload.issues_path,
        )
    except PathValidationError as exc:
        raise ApiError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="INVALID_RUN_PATH",
            message=str(exc),
        ) from exc
    return RunResponse.from_domain(manager.submit(request))


@router.get("", response_model=list[RunResponse])
def list_runs(manager: RunManagerDependency) -> list[RunResponse]:
    return [RunResponse.from_domain(run) for run in manager.list()]


@router.get("/{run_id}", response_model=RunResponse)
def get_run(run_id: str, manager: RunManagerDependency) -> RunResponse:
    return RunResponse.from_domain(_get_run_or_404(manager, run_id))


@router.get(
    "/{run_id}/events",
    response_model=list[RunEventResponse],
)
def list_run_events(
    run_id: str,
    manager: RunManagerDependency,
    after_event_id: int = Query(default=0, ge=0),
) -> list[RunEventResponse]:
    _get_run_or_404(manager, run_id)
    return [
        RunEventResponse.from_domain(event)
        for event in manager.list_events(
            run_id,
            after_event_id=after_event_id,
        )
    ]


@router.get("/{run_id}/events/stream")
def stream_run_events(
    run_id: str,
    manager: RunManagerDependency,
    after_event_id: int = Query(default=0, ge=0),
) -> StreamingResponse:
    _get_run_or_404(manager, run_id)
    return StreamingResponse(
        _event_stream(manager, run_id, after_event_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/{run_id}/output", response_class=FileResponse)
def download_run_output(
    run_id: str,
    manager: RunManagerDependency,
) -> FileResponse:
    run = _get_run_or_404(manager, run_id)
    if not run.output_path:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            code="OUTPUT_NOT_READY",
            message="The run output is not ready for download.",
        )
    output_path = Path(run.output_path).resolve()
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
    manager: RunManager,
    run_id: str,
    after_event_id: int,
) -> AsyncIterator[str]:
    cursor = after_event_id
    idle_cycles = 0
    while True:
        events = manager.list_events(run_id, after_event_id=cursor)
        for event in events:
            cursor = event.event_id
            payload = RunEventResponse.from_domain(event).model_dump(
                mode="json"
            )
            yield (
                f"id: {event.event_id}\n"
                "event: progress\n"
                f"data: {json.dumps(payload)}\n\n"
            )
        run = manager.get(run_id)
        if run.status.is_terminal and not events:
            yield "event: end\ndata: {}\n\n"
            return
        idle_cycles += 1
        if idle_cycles % 30 == 0:
            yield ": heartbeat\n\n"
        await asyncio.sleep(0.5)


def _get_run_or_404(manager: RunManager, run_id: str):
    try:
        return manager.get(run_id)
    except RunNotFoundError as exc:
        raise ApiError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RUN_NOT_FOUND",
            message=f"Run not found: {run_id}",
        ) from exc
