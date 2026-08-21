"""Durable job status, progress and retry endpoints."""
from __future__ import annotations

import asyncio
import json
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.audit_errors import audit_api_errors
from app.api.dependencies import get_audit_workspace_service
from app.api.schemas.audit_jobs import JobEventResponse, JobResponse
from app.application.audit_workspace_service import AuditWorkspaceService

router = APIRouter(prefix="/jobs", tags=["audit-jobs"])
AuditServiceDependency = Annotated[AuditWorkspaceService, Depends(get_audit_workspace_service)]


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, service: AuditServiceDependency) -> JobResponse:
    with audit_api_errors():
        return JobResponse.from_domain(service.get_job(job_id))


@router.get("/{job_id}/events", response_model=list[JobEventResponse])
def list_job_events(
    job_id: str,
    service: AuditServiceDependency,
    after_event_id: int = Query(default=0, ge=0),
) -> list[JobEventResponse]:
    with audit_api_errors():
        return [
            JobEventResponse.from_domain(item)
            for item in service.list_job_events(job_id, after_event_id)
        ]


@router.get("/{job_id}/events/stream")
def stream_job_events(
    job_id: str,
    service: AuditServiceDependency,
    after_event_id: int = Query(default=0, ge=0),
) -> StreamingResponse:
    with audit_api_errors():
        service.get_job(job_id)
    return StreamingResponse(
        _event_stream(service, job_id, after_event_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.post("/{job_id}/retry", response_model=JobResponse)
def retry_job(job_id: str, service: AuditServiceDependency) -> JobResponse:
    with audit_api_errors():
        return JobResponse.from_domain(service.retry_job(job_id))


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
