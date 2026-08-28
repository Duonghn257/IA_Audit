"""Durable job status, progress and retry endpoints."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from fastapi.responses import StreamingResponse

from app.api.audit_errors import audit_api_errors
from app.api.dependencies import (
    CurrentPrincipalDependency,
    get_audit_execution_service,
    get_audit_workspace_service,
    get_discovery_service,
    get_project_manager,
)
from app.api.errors import ApiError
from app.api.schemas.audit_jobs import (
    JobEventResponse,
    JobResponse,
    RetryJobRequest,
)
from app.application.audit_execution_service import AuditExecutionService
from app.application.audit_workspace_service import AuditWorkspaceService
from app.application.discovery_service import DiscoveryService
from app.application.project_manager import ProjectManager
from app.domain.audit import JobRecord, JobType
from app.domain.projects import ProjectNotFoundError

router = APIRouter(prefix="/jobs", tags=["audit-jobs"])
AuditServiceDependency = Annotated[
    AuditWorkspaceService, Depends(get_audit_workspace_service)
]
ProjectManagerDependency = Annotated[ProjectManager, Depends(get_project_manager)]
AuditExecutionDependency = Annotated[
    AuditExecutionService, Depends(get_audit_execution_service)
]
DiscoveryServiceDependency = Annotated[DiscoveryService, Depends(get_discovery_service)]


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    service: AuditServiceDependency,
    manager: ProjectManagerDependency,
    principal: CurrentPrincipalDependency,
) -> JobResponse:
    with audit_api_errors():
        return JobResponse.from_domain(
            _get_owned_job_or_404(job_id, service, manager, principal.user.user_id)
        )


@router.get("/{job_id}/events", response_model=list[JobEventResponse])
def list_job_events(
    job_id: str,
    service: AuditServiceDependency,
    manager: ProjectManagerDependency,
    principal: CurrentPrincipalDependency,
    after_event_id: int = Query(default=0, ge=0),
) -> list[JobEventResponse]:
    with audit_api_errors():
        _get_owned_job_or_404(job_id, service, manager, principal.user.user_id)
        return [
            JobEventResponse.from_domain(item)
            for item in service.list_job_events(job_id, after_event_id)
        ]


@router.get("/{job_id}/events/stream")
def stream_job_events(
    job_id: str,
    service: AuditServiceDependency,
    manager: ProjectManagerDependency,
    principal: CurrentPrincipalDependency,
    after_event_id: int = Query(default=0, ge=0),
) -> StreamingResponse:
    with audit_api_errors():
        _get_owned_job_or_404(job_id, service, manager, principal.user.user_id)
    return StreamingResponse(
        _event_stream(service, job_id, after_event_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.post(
    "/{job_id}/retry",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    service: AuditServiceDependency,
    manager: ProjectManagerDependency,
    principal: CurrentPrincipalDependency,
    discovery: DiscoveryServiceDependency,
    audit: AuditExecutionDependency,
    request: RetryJobRequest | None = None,
) -> JobResponse:
    reason = request.reason if request else None
    with audit_api_errors():
        current = _get_owned_job_or_404(
            job_id, service, manager, principal.user.user_id
        )
        if current.job_type == JobType.DISCOVERY:
            started = discovery.retry_discovery(job_id, reason=reason)
            background_tasks.add_task(discovery.run_discovery, started.job.job_id)
            return JobResponse.from_domain(started.job)
        started = audit.retry_audit(job_id, reason=reason)
        background_tasks.add_task(audit.run_audit, started.job.job_id)
        return JobResponse.from_domain(started.job)


def _get_owned_job_or_404(
    job_id: str,
    service: AuditWorkspaceService,
    manager: ProjectManager,
    owner_user_id: str,
) -> JobRecord:
    job = service.get_job(job_id)
    try:
        manager.get(job.project_id, owner_user_id=owner_user_id)
    except ProjectNotFoundError as exc:
        raise ApiError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="JOB_NOT_FOUND",
            message=f"Job not found: {job_id}",
        ) from exc
    return job


async def _event_stream(
    service: AuditWorkspaceService,
    job_id: str,
    after_event_id: int,
) -> AsyncIterator[str]:
    cursor = after_event_id
    idle_cycles = 0
    while True:
        events = service.list_job_events(job_id, cursor)
        for event in events:
            cursor = event.event_id
            payload = JobEventResponse.from_domain(event).model_dump(mode="json")
            yield f"id: {event.event_id}\nevent: progress\ndata: {json.dumps(payload)}\n\n"
        job = service.get_job(job_id)
        if not job.state.is_active and not events:
            yield "event: end\ndata: {}\n\n"
            return
        idle_cycles += 1
        if idle_cycles % 30 == 0:
            yield ": heartbeat\n\n"
        await asyncio.sleep(0.5)
