"""API schemas for uploaded audit projects."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.domain.projects import ProjectEvent, ProjectRecord, ProjectStatus


class ProjectEventResponse(BaseModel):
    event_id: int
    stage: str
    message: str
    completed_steps: int
    total_steps: int
    warning: bool
    occurred_at: datetime

    @classmethod
    def from_domain(cls, event: ProjectEvent) -> "ProjectEventResponse":
        return cls(
            event_id=event.event_id,
            stage=event.stage,
            message=event.message,
            completed_steps=event.completed_steps,
            total_steps=event.total_steps,
            warning=event.warning,
            occurred_at=event.occurred_at,
        )


class ProjectResponse(BaseModel):
    project_id: str
    name: str
    source_type: str
    status: ProjectStatus
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
    raw_expires_at: datetime | None
    raw_deleted_at: datetime | None

    @classmethod
    def from_domain(cls, project: ProjectRecord) -> "ProjectResponse":
        output_available = (
            project.status == ProjectStatus.COMPLETED
            and project.output_path is not None
        )
        return cls(
            project_id=project.project_id,
            name=project.name,
            source_type=project.source_type,
            status=project.status,
            current_activity=project.current_activity,
            allowed_actions=_allowed_actions(project),
            created_at=project.created_at,
            updated_at=project.updated_at,
            started_at=project.started_at,
            completed_at=project.completed_at,
            output_available=output_available,
            output_download_url=(
                f"/api/v1/projects/{project.project_id}/output"
                if output_available
                else None
            ),
            version=project.version,
            issue_count=project.issue_count,
            error=project.error,
            raw_expires_at=project.raw_expires_at,
            raw_deleted_at=project.raw_deleted_at,
        )


def _allowed_actions(project: ProjectRecord) -> list[str]:
    actions = ["VIEW_STATUS"]
    if project.status == ProjectStatus.PROCESSING:
        actions.append("VIEW_PROGRESS")
    elif project.status == ProjectStatus.COMPLETED:
        actions.extend(["VIEW_PROGRESS", "DOWNLOAD_OUTPUT"])
    elif project.status == ProjectStatus.FAILED:
        actions.append("VIEW_PROGRESS")
    return actions

