"""Schemas for local-first UAT upload sessions."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.application.audit_intake_service import (
    PromotedProject,
    UploadFileView,
    UploadSessionView,
)
from app.domain.audit import (
    AuditVersionState,
    LogicalRole,
    ProjectState,
    UploadSessionState,
)


class UploadFileRequest(BaseModel):
    relative_path: str = Field(min_length=1, max_length=1024)
    size_bytes: int = Field(gt=0)
    content_type: str | None = Field(default=None, max_length=255)
    modified_at: datetime | None = None


class CreateUploadSessionRequest(BaseModel):
    files: list[UploadFileRequest] = Field(min_length=1)


class CreateProjectFromUploadRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class UploadFileResponse(BaseModel):
    file_id: str
    relative_path: str
    size_bytes: int
    content_type: str | None
    modified_at: datetime | None
    upload_status: str
    logical_role: LogicalRole | None
    readability_status: str | None
    validation_message: str | None
    upload_method: str
    upload_url: str
    required_headers: dict[str, str]

    @classmethod
    def from_view(cls, view: UploadFileView) -> UploadFileResponse:
        file = view.file
        return cls(
            file_id=file.file_id,
            relative_path=file.relative_path,
            size_bytes=file.size_bytes,
            content_type=file.content_type,
            modified_at=file.modified_at,
            upload_status=file.upload_status,
            logical_role=file.logical_role,
            readability_status=file.readability_status,
            validation_message=file.validation_message,
            upload_method=view.upload_method,
            upload_url=view.upload_url,
            required_headers=view.required_headers,
        )


class UploadSessionResponse(BaseModel):
    session_id: str
    state: UploadSessionState
    created_at: datetime
    expires_at: datetime
    promoted_at: datetime | None
    files: list[UploadFileResponse]
    validation_report: dict[str, Any] | None
    allowed_actions: list[str]
    action_reasons: dict[str, str]

    @classmethod
    def from_view(
        cls, view: UploadSessionView
    ) -> UploadSessionResponse:
        session = view.session
        return cls(
            session_id=session.session_id,
            state=session.state,
            created_at=session.created_at,
            expires_at=session.expires_at,
            promoted_at=session.promoted_at,
            files=[
                UploadFileResponse.from_view(file)
                for file in view.files
            ],
            validation_report=session.validation_report,
            allowed_actions=list(view.allowed_actions),
            action_reasons=view.action_reasons,
        )


class CreatedVersionResponse(BaseModel):
    version_id: str
    sequence_no: int
    label: str
    state: AuditVersionState
    issue_revision: int


class CreateProjectFromUploadResponse(BaseModel):
    project_id: str
    name: str
    state: ProjectState
    source_snapshot_id: str
    version: CreatedVersionResponse
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_result(
        cls, result: PromotedProject
    ) -> CreateProjectFromUploadResponse:
        project = result.project
        version = result.version
        return cls(
            project_id=project.project_id,
            name=project.name,
            state=project.state,
            source_snapshot_id=project.source_snapshot_id,
            version=CreatedVersionResponse(
                version_id=version.version_id,
                sequence_no=version.sequence_no,
                label=version.label,
                state=version.state,
                issue_revision=version.issue_revision,
            ),
            created_at=project.created_at,
            updated_at=project.updated_at,
        )
