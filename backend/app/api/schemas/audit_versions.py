"""Schemas for project audit versions."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.api.schemas.audit_jobs import JobResponse
from app.application.audit_workspace_service import VersionWorkspace
from app.domain.audit import AuditVersionState


class CreateVersionRequest(BaseModel):
    base_version_id: str


class ProjectVersionResponse(BaseModel):
    version_id: str
    project_id: str
    sequence_no: int
    label: str
    base_version_id: str | None
    state: AuditVersionState
    issue_revision: int
    issue_counts: dict[str, int]
    latest_job: JobResponse | None
    output_available: bool
    allowed_actions: list[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, workspace: VersionWorkspace) -> "ProjectVersionResponse":
        version = workspace.version
        return cls(
            version_id=version.version_id,
            project_id=version.project_id,
            sequence_no=version.sequence_no,
            label=version.label,
            base_version_id=version.base_version_id,
            state=version.state,
            issue_revision=version.issue_revision,
            issue_counts=workspace.issue_counts,
            latest_job=(
                JobResponse.from_domain(workspace.latest_job)
                if workspace.latest_job
                else None
            ),
            output_available=workspace.output_available,
            allowed_actions=_allowed_actions(version.state, workspace.output_available),
            created_at=version.created_at,
            updated_at=version.updated_at,
        )


def _allowed_actions(state: AuditVersionState, output_available: bool) -> list[str]:
    actions = ["CREATE_VERSION", "VIEW_ISSUES"]
    if state != AuditVersionState.AUDITING:
        actions.extend(["EDIT_ISSUES", "RUN_DISCOVERY", "RUN_AUDIT"])
    else:
        actions.append("VIEW_PROGRESS")
    if output_available:
        actions.append("DOWNLOAD_OUTPUT")
    return actions
