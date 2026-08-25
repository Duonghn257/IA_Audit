"""Schemas for durable audit jobs and generated output revisions."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.audit import (
    JobEventRecord,
    JobRecord,
    JobState,
    JobType,
    OutputRevisionRecord,
    OutputStatus,
)


class StartDiscoveryRequest(BaseModel):
    force: bool = False


class StartAuditRequest(BaseModel):
    issue_revision: int


class RetryJobRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class JobResponse(BaseModel):
    job_id: str
    project_id: str
    project_version_id: str
    job_type: JobType
    state: JobState
    stage: str | None
    completed_items: int
    total_items: int | None
    current_message: str | None
    attempt_count: int
    correlation_id: str
    created_at: datetime
    updated_at: datetime
    heartbeat_at: datetime | None
    error: str | None

    @classmethod
    def from_domain(cls, value: JobRecord) -> JobResponse:
        fields = cls.model_fields
        return cls(**{name: getattr(value, name) for name in fields})


class JobEventResponse(BaseModel):
    event_id: int
    job_id: str
    stage: str
    message: str
    completed_items: int
    total_items: int | None
    warning: bool
    occurred_at: datetime

    @classmethod
    def from_domain(cls, value: JobEventRecord) -> JobEventResponse:
        return cls(**value.__dict__)


class OutputRevisionResponse(BaseModel):
    output_id: str
    project_version_id: str
    ordinal: int
    status: OutputStatus
    filename: str
    content_hash: str
    created_at: datetime
    download_url: str

    @classmethod
    def from_domain(cls, value: OutputRevisionRecord) -> OutputRevisionResponse:
        return cls(
            output_id=value.output_id,
            project_version_id=value.project_version_id,
            ordinal=value.ordinal,
            status=value.status,
            filename=value.filename,
            content_hash=value.content_hash,
            created_at=value.created_at,
            download_url=f"/api/v1/outputs/{value.output_id}/download",
        )
