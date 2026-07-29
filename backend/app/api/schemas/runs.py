"""API schemas for audit-run endpoints."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.runs import RunEvent, RunRecord, RunStatus


class CreateRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_path: str = Field(min_length=1)
    issues_path: str = Field(min_length=1)


class RunEventResponse(BaseModel):
    event_id: int
    stage: str
    message: str
    completed_steps: int
    total_steps: int
    warning: bool
    occurred_at: datetime

    @classmethod
    def from_domain(cls, event: RunEvent) -> "RunEventResponse":
        return cls(
            event_id=event.event_id,
            stage=event.stage,
            message=event.message,
            completed_steps=event.completed_steps,
            total_steps=event.total_steps,
            warning=event.warning,
            occurred_at=event.occurred_at,
        )


class RunResponse(BaseModel):
    run_id: str
    project_path: str
    issues_path: str
    status: RunStatus
    current_activity: str | None
    allowed_actions: list[str]
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    output_available: bool
    output_download_url: str | None
    version: str | None
    issue_count: int | None
    error: str | None

    @classmethod
    def from_domain(cls, run: RunRecord) -> "RunResponse":
        current_activity = run.events[-1].message if run.events else None
        return cls(
            run_id=run.run_id,
            project_path=run.project_path,
            issues_path=run.issues_path,
            status=run.status,
            current_activity=current_activity,
            allowed_actions=_allowed_actions(run),
            created_at=run.created_at,
            updated_at=run.updated_at,
            started_at=run.started_at,
            completed_at=run.completed_at,
            output_available=run.output_path is not None,
            output_download_url=(
                f"/api/v1/runs/{run.run_id}/output"
                if run.output_path
                else None
            ),
            version=run.version,
            issue_count=run.issue_count,
            error=run.error,
        )


def _allowed_actions(run: RunRecord) -> list[str]:
    if run.status == RunStatus.QUEUED:
        return ["VIEW_STATUS"]
    if run.status == RunStatus.RUNNING:
        return ["VIEW_STATUS", "VIEW_PROGRESS"]
    if run.status == RunStatus.COMPLETED:
        return ["VIEW_STATUS", "VIEW_PROGRESS", "DOWNLOAD_OUTPUT"]
    return ["VIEW_STATUS", "VIEW_PROGRESS"]
