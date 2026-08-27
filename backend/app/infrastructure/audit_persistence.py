"""Shared queries, validation and record mapping for audit repositories."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.audit import (
    ActiveJobConflictError,
    AuditInputSnapshotRecord,
    AuditIssueNotFoundError,
    AuditJobNotFoundError,
    AuditProjectNotFoundError,
    AuditProjectRecord,
    AuditStateError,
    AuditVersionNotFoundError,
    AuditVersionState,
    IssueOrigin,
    IssueRecord,
    IssueStatus,
    JobEventRecord,
    JobRecord,
    JobState,
    JobType,
    LogicalRole,
    RiskCategory,
    OutputRevisionRecord,
    OutputStatus,
    ProjectState,
    ProjectVersionRecord,
    SourceReferenceInput,
    SourceReferenceRecord,
    SourceRefKind,
    UploadFileRecord,
    UploadSessionNotFoundError,
    UploadSessionRecord,
    UploadSessionState,
)
from app.infrastructure.audit_models import (
    AuditInputSnapshotModel,
    IssueModel,
    IssueSourceRefModel,
    JobEventModel,
    JobModel,
    OutputRevisionModel,
    ProjectVersionModel,
    SourceDocumentModel,
    SourceSnapshotModel,
    UploadSessionModel,
)
from app.infrastructure.project_repository import ProjectModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_upload_session(session: Session, session_id: str, *, lock: bool = False) -> UploadSessionModel:
    statement = select(UploadSessionModel).where(UploadSessionModel.session_id == session_id)
    if lock:
        statement = statement.with_for_update()
    model = session.scalars(statement).first()
    if model is None:
        raise UploadSessionNotFoundError(session_id)
    return model


def get_project(session: Session, project_id: str, *, lock: bool = False) -> ProjectModel:
    statement = select(ProjectModel).where(ProjectModel.project_id == project_id)
    if lock:
        statement = statement.with_for_update()
    model = session.scalars(statement).first()
    if model is None:
        raise AuditProjectNotFoundError(project_id)
    return model


def get_snapshot(session: Session, project_id: str) -> SourceSnapshotModel:
    model = session.scalars(select(SourceSnapshotModel).where(SourceSnapshotModel.project_id == project_id)).first()
    if model is None:
        raise AuditProjectNotFoundError(project_id)
    return model


def get_version(session: Session, version_id: str, *, lock: bool = False) -> ProjectVersionModel:
    statement = select(ProjectVersionModel).where(ProjectVersionModel.version_id == version_id)
    if lock:
        statement = statement.with_for_update()
    model = session.scalars(statement).first()
    if model is None:
        raise AuditVersionNotFoundError(version_id)
    return model


def get_issue(session: Session, issue_id: str, *, lock: bool = False) -> IssueModel:
    statement = select(IssueModel).where(IssueModel.issue_id == issue_id)
    if lock:
        statement = statement.with_for_update()
    model = session.scalars(statement).first()
    if model is None:
        raise AuditIssueNotFoundError(issue_id)
    return model


def get_job(session: Session, job_id: str, *, lock: bool = False) -> JobModel:
    statement = select(JobModel).where(JobModel.job_id == job_id)
    if lock:
        statement = statement.with_for_update()
    model = session.scalars(statement).first()
    if model is None:
        raise AuditJobNotFoundError(job_id)
    return model


def require_upload_state(model: UploadSessionModel, expected: set[UploadSessionState]) -> None:
    if UploadSessionState(model.state) not in expected:
        values = ", ".join(state.value for state in expected)
        raise AuditStateError(f"Upload session {model.session_id} is {model.state}, expected {values}.")


def validate_source_refs(session: Session, project_id: str, source_refs: Sequence[SourceReferenceInput]) -> None:
    if not source_refs:
        return
    snapshot = get_snapshot(session, project_id)
    document_ids = {reference.document_id for reference in source_refs}
    found = set(session.scalars(select(SourceDocumentModel.document_id).where(
        (SourceDocumentModel.snapshot_id == snapshot.snapshot_id)
        & SourceDocumentModel.document_id.in_(document_ids)
    )))
    unknown = document_ids - found
    if unknown:
        raise ValueError(f"Unknown source documents: {sorted(unknown)}")


def source_ref_model(reference: SourceReferenceInput, issue_id: str) -> IssueSourceRefModel:
    return IssueSourceRefModel(
        reference_id=reference.reference_id,
        issue_id=issue_id,
        ref_kind=reference.ref_kind.value,
        document_id=reference.document_id,
        unit_id=reference.unit_id,
        location=reference.location,
        quote=reference.quote,
    )


def touch_issue_workspace(session: Session, version: ProjectVersionModel, now: datetime) -> None:
    version.issue_revision += 1
    version.updated_at = now
    outputs = session.scalars(select(OutputRevisionModel).where(
        (OutputRevisionModel.project_version_id == version.version_id)
        & (OutputRevisionModel.status == OutputStatus.CURRENT.value)
    ))
    has_output = False
    for output in outputs:
        output.status = OutputStatus.STALE.value
        has_output = True
    if has_output:
        version.state = AuditVersionState.STALE_OUTPUT.value


def ensure_no_active_job(session: Session, version_id: str, job_type: JobType, input_hash: str) -> None:
    existing = session.scalars(select(JobModel).where(
        (JobModel.project_version_id == version_id)
        & (JobModel.job_type == job_type.value)
        & (JobModel.input_hash == input_hash)
        & JobModel.state.in_([JobState.QUEUED.value, JobState.RUNNING.value])
    )).first()
    if existing is not None:
        raise ActiveJobConflictError(existing.job_id)


def next_version_number(session: Session, project_id: str) -> int:
    latest = session.scalar(select(func.max(ProjectVersionModel.sequence_no)).where(ProjectVersionModel.project_id == project_id))
    return int(latest or 0) + 1


def version_state_from_outputs(session: Session, version_id: str) -> AuditVersionState:
    output = session.scalars(select(OutputRevisionModel).where(
        OutputRevisionModel.project_version_id == version_id
    ).order_by(OutputRevisionModel.ordinal.desc())).first()
    if output is None:
        return AuditVersionState.DRAFT
    return AuditVersionState.DOCX_READY if output.status == OutputStatus.CURRENT.value else AuditVersionState.STALE_OUTPUT


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def to_upload_session_record(model: UploadSessionModel) -> UploadSessionRecord:
    return UploadSessionRecord(
        session_id=model.session_id,
        state=UploadSessionState(model.state),
        actor_id=model.actor_id,
        actor_label=model.actor_label,
        actor_type=model.actor_type,
        created_at=as_utc(model.created_at),
        expires_at=as_utc(model.expires_at),
        validation_report=model.validation_report,
        promoted_at=as_utc(model.promoted_at),
    )


def to_upload_file_record(model) -> UploadFileRecord:
    return UploadFileRecord(
        file_id=model.file_id,
        session_id=model.session_id,
        relative_path=model.relative_path,
        size_bytes=model.size_bytes,
        content_type=model.content_type,
        staging_object_key=model.staging_object_key,
        upload_status=model.upload_status,
        content_hash=model.content_hash,
        logical_role=(
            LogicalRole(model.logical_role)
            if model.logical_role
            else None
        ),
        readability_status=model.readability_status,
        validation_message=model.validation_message,
        modified_at=as_utc(model.modified_at),
    )


def to_project_record(project: ProjectModel, snapshot: SourceSnapshotModel, next_number: int) -> AuditProjectRecord:
    return AuditProjectRecord(project.project_id, project.name, next_number, snapshot.snapshot_id, ProjectState(project.status), as_utc(project.created_at), as_utc(project.updated_at))


def to_version_record(model: ProjectVersionModel) -> ProjectVersionRecord:
    return ProjectVersionRecord(
        model.version_id,
        model.project_id,
        model.sequence_no,
        model.label,
        model.base_version_id,
        AuditVersionState(model.state),
        model.issue_revision,
        model.created_by_user_id,
        model.created_by_name,
        as_utc(model.created_at),
        as_utc(model.updated_at),
    )


def _risk_category(value: str | None) -> RiskCategory | None:
    if value is None:
        return None
    try:
        return RiskCategory(value)
    except ValueError:
        return None


def to_issue_record(model: IssueModel) -> IssueRecord:
    source_refs = tuple(
        SourceReferenceRecord(
            reference_id=reference.reference_id,
            ref_kind=SourceRefKind(reference.ref_kind),
            document_id=reference.document_id,
            unit_id=reference.unit_id,
            location=reference.location,
            quote=reference.quote,
        )
        for reference in model.source_refs
    )
    return IssueRecord(
        issue_id=model.issue_id,
        project_version_id=model.project_version_id,
        origin=IssueOrigin(model.origin),
        status=IssueStatus(model.status),
        observed_gap=model.observed_gap,
        title_hint=model.title_hint,
        evidence_summary=model.evidence_summary,
        risk_category=_risk_category(model.risk_category),
        confidence=model.confidence,
        validation_flags=list(model.validation_flags),
        row_version=model.row_version,
        created_at=as_utc(model.created_at),
        updated_at=as_utc(model.updated_at),
        evidence_refs=tuple(model.evidence_refs or ()),
        sop_refs=tuple(model.sop_refs or ()),
        source_refs=source_refs,
    )


def to_job_record(model: JobModel) -> JobRecord:
    return JobRecord(model.job_id, model.project_id, model.project_version_id, JobType(model.job_type), JobState(model.state), model.stage, model.input_hash, model.completed_items, model.total_items, model.current_message, model.attempt_count, model.correlation_id, as_utc(model.created_at), as_utc(model.updated_at), as_utc(model.heartbeat_at), model.error)


def to_job_event_record(model: JobEventModel) -> JobEventRecord:
    return JobEventRecord(model.event_id, model.job_id, model.stage, model.message, model.completed_items, model.total_items, model.warning, as_utc(model.occurred_at))


def to_snapshot_record(model: AuditInputSnapshotModel, job_id: str) -> AuditInputSnapshotRecord:
    return AuditInputSnapshotRecord(model.snapshot_id, model.project_version_id, job_id, model.issue_revision, model.input_hash, as_utc(model.created_at))


def to_output_record(model: OutputRevisionModel) -> OutputRevisionRecord:
    return OutputRevisionRecord(model.output_id, model.project_version_id, model.audit_input_snapshot_id, model.ordinal, OutputStatus(model.status), model.filename, model.object_key, model.content_hash, as_utc(model.created_at))
