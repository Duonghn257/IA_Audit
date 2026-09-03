"""Typed records passed between UAT application and persistence layers."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.domain.audit_states import (
    AuditVersionState,
    IssueOrigin,
    IssueStatus,
    JobState,
    JobType,
    LogicalRole,
    OutputStatus,
    ProjectState,
    RiskCategory,
    SourceRefKind,
    UploadSessionState,
)


@dataclass(frozen=True)
class UploadFileInput:
    file_id: str
    relative_path: str
    size_bytes: int
    content_type: str | None
    staging_object_key: str
    modified_at: datetime | None = None


@dataclass(frozen=True)
class UploadFileRecord:
    file_id: str
    session_id: str
    relative_path: str
    size_bytes: int
    content_type: str | None
    staging_object_key: str
    upload_status: str
    content_hash: str | None
    logical_role: LogicalRole | None
    readability_status: str | None
    validation_message: str | None
    modified_at: datetime | None = None


@dataclass(frozen=True)
class UploadFileValidation:
    file_id: str
    content_hash: str
    logical_role: LogicalRole
    readability_status: str
    validation_message: str | None = None


@dataclass(frozen=True)
class UploadSessionRecord:
    session_id: str
    state: UploadSessionState
    actor_id: str
    actor_label: str
    actor_type: str
    created_at: datetime
    expires_at: datetime
    validation_report: dict[str, Any] | None
    promoted_at: datetime | None


@dataclass(frozen=True)
class AuditProjectRecord:
    project_id: str
    name: str
    next_version_number: int
    source_snapshot_id: str
    state: ProjectState
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ProjectVersionRecord:
    version_id: str
    project_id: str
    sequence_no: int
    label: str
    base_version_id: str | None
    state: AuditVersionState
    issue_revision: int
    created_by_user_id: str
    created_by_name: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class SourceReferenceInput:
    reference_id: str
    ref_kind: SourceRefKind
    document_id: str
    location: dict[str, Any]
    unit_id: str | None = None
    quote: str | None = None


@dataclass(frozen=True)
class SourceReferenceRecord:
    reference_id: str
    ref_kind: SourceRefKind
    document_id: str
    location: dict[str, Any]
    unit_id: str | None = None
    quote: str | None = None


def source_reference_label(
    value: SourceReferenceInput | SourceReferenceRecord,
) -> str:
    """Build the legacy display value from a canonical source reference."""
    description = value.location.get("description")
    if isinstance(description, str) and description.strip():
        location = description.strip()
    elif value.location:
        location = json.dumps(
            value.location,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    else:
        location = ""
    return f"{value.document_id} - {location}" if location else value.document_id


def compatibility_reference_lists(
    values: tuple[SourceReferenceInput | SourceReferenceRecord, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Derive deprecated evidence/SOP arrays from canonical references."""
    evidence = tuple(
        source_reference_label(value)
        for value in values
        if value.ref_kind == SourceRefKind.EVIDENCE
    )
    criteria = tuple(
        source_reference_label(value)
        for value in values
        if value.ref_kind == SourceRefKind.CRITERIA
    )
    return evidence, criteria


@dataclass(frozen=True)
class SourceDocumentRecord:
    document_id: str
    snapshot_id: str
    relative_path: str
    logical_role: LogicalRole
    original_object_key: str
    content_hash: str
    size_bytes: int
    content_type: str | None
    upload_status: str
    parse_status: str


@dataclass(frozen=True)
class CandidateIssueInput:
    title_hint: str
    observed_gap: str
    evidence_summary: str
    source_refs: tuple[SourceReferenceInput, ...]
    risk_category: RiskCategory


@dataclass(frozen=True)
class IssueRecord:
    issue_id: str
    project_version_id: str
    origin: IssueOrigin
    status: IssueStatus
    observed_gap: str
    title_hint: str | None
    evidence_summary: str | None
    risk_category: RiskCategory | None
    confidence: float | None
    validation_flags: list[str]
    row_version: int
    created_at: datetime
    updated_at: datetime
    evidence_refs: tuple[str, ...] = ()
    sop_refs: tuple[str, ...] = ()
    source_refs: tuple[SourceReferenceRecord, ...] = ()


@dataclass(frozen=True)
class JobRecord:
    job_id: str
    project_id: str
    project_version_id: str
    job_type: JobType
    state: JobState
    stage: str | None
    input_hash: str
    completed_items: int
    total_items: int | None
    current_message: str | None
    attempt_count: int
    correlation_id: str
    created_at: datetime
    updated_at: datetime
    heartbeat_at: datetime | None
    error: str | None


@dataclass(frozen=True)
class JobEventRecord:
    event_id: int
    job_id: str
    stage: str
    message: str
    completed_items: int
    total_items: int | None
    warning: bool
    occurred_at: datetime


@dataclass(frozen=True)
class AuditInputSnapshotRecord:
    snapshot_id: str
    project_version_id: str
    job_id: str
    issue_revision: int
    input_hash: str
    issue_payload: dict[str, Any]
    central_asset_versions: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True)
class OutputRevisionRecord:
    output_id: str
    project_version_id: str
    audit_input_snapshot_id: str
    ordinal: int
    status: OutputStatus
    filename: str
    object_key: str
    content_hash: str
    created_at: datetime
