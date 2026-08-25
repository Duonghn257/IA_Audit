"""Durable job, progress, audit-input and output persistence operations."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.audit import (
    AuditInputSnapshotRecord,
    AuditStateError,
    AuditVersionNotFoundError,
    AuditVersionState,
    CandidateIssueInput,
    IssueOrigin,
    IssueStatus,
    JobEventRecord,
    JobNotRetryableError,
    JobRecord,
    JobState,
    JobType,
    LogicalRole,
    OutputRevisionRecord,
    OutputStatus,
    ProjectState,
    SourceDocumentRecord,
)
from app.infrastructure.audit_models import (
    AuditInputSnapshotModel,
    IssueModel,
    JobEventModel,
    JobModel,
    OutputRevisionModel,
    SourceDocumentModel,
)
from app.infrastructure.audit_persistence import (
    ensure_no_active_job,
    get_job,
    get_project,
    get_snapshot,
    get_version,
    to_job_event_record,
    to_job_record,
    to_output_record,
    to_snapshot_record,
    touch_issue_workspace,
    utcnow,
    version_state_from_outputs,
)


class SqlAlchemyAuditJobRepository:
    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def get_job(self, job_id: str) -> JobRecord:
        with self._sessions() as session:
            return to_job_record(get_job(session, job_id))

    def list_jobs_for_version(self, version_id: str) -> list[JobRecord]:
        with self._sessions() as session:
            get_version(session, version_id)
            jobs = session.scalars(
                select(JobModel)
                .where(JobModel.project_version_id == version_id)
                .order_by(JobModel.created_at.desc(), JobModel.job_id.desc())
            ).all()
            return [to_job_record(job) for job in jobs]

    def list_source_documents(
        self, project_id: str
    ) -> list[SourceDocumentRecord]:
        with self._sessions() as session:
            snapshot = get_snapshot(session, project_id)
            documents = session.scalars(
                select(SourceDocumentModel)
                .where(SourceDocumentModel.snapshot_id == snapshot.snapshot_id)
                .order_by(
                    SourceDocumentModel.relative_path,
                    SourceDocumentModel.document_id,
                )
            ).all()
            return [
                SourceDocumentRecord(
                    document_id=document.document_id,
                    snapshot_id=document.snapshot_id,
                    relative_path=document.relative_path,
                    logical_role=LogicalRole(document.logical_role),
                    original_object_key=document.original_object_key,
                    content_hash=document.content_hash,
                    size_bytes=document.size_bytes,
                    content_type=document.content_type,
                )
                for document in documents
            ]

    def enqueue_job(
        self,
        project_id: str,
        version_id: str,
        *,
        job_id: str,
        job_type: JobType,
        input_hash: str,
        correlation_id: str,
        stage: str | None = None,
    ) -> JobRecord:
        now = utcnow()
        with self._sessions.begin() as session:
            version = get_version(session, version_id, lock=True)
            if version.project_id != project_id:
                raise AuditVersionNotFoundError(version_id)
            ensure_no_active_job(session, version_id, job_type, input_hash)
            job = JobModel(
                job_id=job_id,
                project_id=project_id,
                project_version_id=version_id,
                job_type=job_type.value,
                state=JobState.QUEUED.value,
                stage=stage,
                input_hash=input_hash,
                correlation_id=correlation_id,
                created_at=now,
                updated_at=now,
            )
            if job_type == JobType.AUDIT:
                version.state = AuditVersionState.AUDITING.value
                version.updated_at = now
            session.add(job)
        return to_job_record(job)

    def enqueue_audit_job(
        self,
        project_id: str,
        version_id: str,
        *,
        job_id: str,
        snapshot_id: str,
        input_hash: str,
        issue_payload: dict[str, Any],
        central_asset_versions: dict[str, Any],
        correlation_id: str,
    ) -> tuple[JobRecord, AuditInputSnapshotRecord]:
        now = utcnow()
        with self._sessions.begin() as session:
            version = get_version(session, version_id, lock=True)
            if version.project_id != project_id:
                raise AuditVersionNotFoundError(version_id)
            ensure_no_active_job(session, version_id, JobType.AUDIT, input_hash)
            snapshot = AuditInputSnapshotModel(
                snapshot_id=snapshot_id,
                project_version_id=version_id,
                issue_revision=version.issue_revision,
                input_hash=input_hash,
                issue_payload=issue_payload,
                central_asset_versions=central_asset_versions,
                created_at=now,
            )
            job = JobModel(
                job_id=job_id,
                project_id=project_id,
                project_version_id=version_id,
                job_type=JobType.AUDIT.value,
                state=JobState.QUEUED.value,
                input_hash=input_hash,
                correlation_id=correlation_id,
                input_snapshot_id=snapshot_id,
                created_at=now,
                updated_at=now,
            )
            version.state = AuditVersionState.AUDITING.value
            version.updated_at = now
            session.add_all([snapshot, job])
        return to_job_record(job), to_snapshot_record(snapshot, job_id)

    def claim_next_job(self, worker_id: str, *, lease_seconds: int = 60) -> JobRecord | None:
        now = utcnow()
        with self._sessions.begin() as session:
            job = session.scalars(select(JobModel).where(
                (JobModel.state == JobState.QUEUED.value)
                | ((JobModel.state == JobState.RUNNING.value) & (JobModel.lease_expires_at < now))
            ).order_by(JobModel.created_at).with_for_update(skip_locked=True)).first()
            if job is None:
                return None
            job.state = JobState.RUNNING.value
            job.lease_owner = worker_id
            job.lease_expires_at = now + timedelta(seconds=lease_seconds)
            job.heartbeat_at = now
            job.attempt_count += 1
            job.updated_at = now
        return to_job_record(job)

    def claim_job(
        self,
        job_id: str,
        worker_id: str,
        *,
        lease_seconds: int = 300,
    ) -> JobRecord | None:
        now = utcnow()
        with self._sessions.begin() as session:
            job = get_job(session, job_id, lock=True)
            if job.state != JobState.QUEUED.value:
                return None
            job.state = JobState.RUNNING.value
            job.lease_owner = worker_id
            job.lease_expires_at = now + timedelta(seconds=lease_seconds)
            job.heartbeat_at = now
            job.attempt_count += 1
            job.updated_at = now
        return to_job_record(job)

    def append_job_event(
        self,
        job_id: str,
        *,
        stage: str,
        message: str,
        completed_items: int,
        total_items: int | None,
        warning: bool = False,
        checkpoint: dict[str, Any] | None = None,
    ) -> JobEventRecord:
        now = utcnow()
        with self._sessions.begin() as session:
            job = get_job(session, job_id, lock=True)
            event = JobEventModel(
                job_id=job_id,
                stage=stage,
                message=message,
                completed_items=completed_items,
                total_items=total_items,
                warning=warning,
                occurred_at=now,
            )
            job.stage = stage
            job.current_message = message
            job.completed_items = completed_items
            job.total_items = total_items
            job.checkpoint = checkpoint
            job.heartbeat_at = now
            job.updated_at = now
            session.add(event)
            session.flush()
        return to_job_event_record(event)

    def complete_discovery(
        self,
        job_id: str,
        candidates: Sequence[CandidateIssueInput],
    ) -> JobRecord:
        now = utcnow()
        with self._sessions.begin() as session:
            job = get_job(session, job_id, lock=True)
            if (
                job.job_type != JobType.DISCOVERY.value
                or job.state != JobState.RUNNING.value
            ):
                raise AuditStateError(
                    "Only a running Discovery job can publish candidates."
                )
            version = get_version(
                session, job.project_version_id, lock=True
            )
            existing = session.scalars(
                select(IssueModel).where(
                    IssueModel.project_version_id == version.version_id,
                    IssueModel.origin == IssueOrigin.AI_DISCOVERED.value,
                )
            ).all()
            for issue in existing:
                session.delete(issue)
            session.flush()
            for candidate in candidates:
                session.add(
                    IssueModel(
                        issue_id=str(uuid4()),
                        project_version_id=version.version_id,
                        origin=IssueOrigin.AI_DISCOVERED.value,
                        status=IssueStatus.READY_FOR_REVIEW.value,
                        title_hint=candidate.title_hint,
                        observed_gap=candidate.observed_gap,
                        evidence_summary=candidate.evidence_summary,
                        evidence_refs=list(candidate.evidence_refs),
                        sop_refs=list(candidate.sop_refs),
                        risk_category=candidate.risk_category or None,
                        confidence=None,
                        validation_flags=[],
                        row_version=1,
                        created_at=now,
                        updated_at=now,
                    )
                )
            touch_issue_workspace(session, version, now)
            if version.state != AuditVersionState.STALE_OUTPUT.value:
                version.state = AuditVersionState.CANDIDATES_READY.value
            project = get_project(session, job.project_id, lock=True)
            project.status = ProjectState.CANDIDATES_AVAILABLE.value
            project.current_activity = (
                f"{len(candidates)} candidate issues ready for review"
            )
            project.updated_at = now
            job.state = JobState.SUCCEEDED.value
            job.stage = "COMPLETE"
            job.current_message = project.current_activity
            job.completed_items = len(candidates)
            job.total_items = len(candidates)
            job.error = None
            job.lease_owner = None
            job.lease_expires_at = None
            job.updated_at = now
            session.flush()
            return to_job_record(job)

    def finish_job(self, job_id: str, *, state: JobState, error: str | None = None) -> JobRecord:
        if state not in {JobState.SUCCEEDED, JobState.INCOMPLETE, JobState.FAILED}:
            raise ValueError("finish_job requires a terminal job state")
        now = utcnow()
        with self._sessions.begin() as session:
            job = get_job(session, job_id, lock=True)
            job.state = state.value
            job.error = error
            job.lease_owner = None
            job.lease_expires_at = None
            job.updated_at = now
            version = get_version(session, job.project_version_id, lock=True)
            if job.job_type == JobType.DISCOVERY.value and state == JobState.SUCCEEDED:
                version.state = AuditVersionState.CANDIDATES_READY.value
                project = get_project(session, job.project_id, lock=True)
                project.status = ProjectState.CANDIDATES_AVAILABLE.value
                project.updated_at = now
            elif job.job_type == JobType.AUDIT.value and state != JobState.SUCCEEDED:
                version.state = version_state_from_outputs(session, version.version_id).value
            version.updated_at = now
        return to_job_record(job)

    def publish_output_revision(
        self,
        job_id: str,
        *,
        output_id: str,
        filename: str,
        object_key: str,
        content_hash: str,
        run_manifest_object_key: str | None = None,
    ) -> OutputRevisionRecord:
        now = utcnow()
        with self._sessions.begin() as session:
            job = get_job(session, job_id, lock=True)
            if job.job_type != JobType.AUDIT.value or not job.input_snapshot_id:
                raise AuditStateError("Only an Audit job with frozen input can publish output.")
            version = get_version(session, job.project_version_id, lock=True)
            ordinal = session.scalar(
                select(func.coalesce(func.max(OutputRevisionModel.ordinal), 0)).where(
                    OutputRevisionModel.project_version_id == version.version_id
                )
            ) + 1
            for output in session.scalars(select(OutputRevisionModel).where(
                (OutputRevisionModel.project_version_id == version.version_id)
                & (OutputRevisionModel.status == OutputStatus.CURRENT.value)
            )):
                output.status = OutputStatus.STALE.value
            output = OutputRevisionModel(
                output_id=output_id,
                project_version_id=version.version_id,
                audit_input_snapshot_id=job.input_snapshot_id,
                ordinal=int(ordinal),
                status=OutputStatus.CURRENT.value,
                filename=filename,
                object_key=object_key,
                content_hash=content_hash,
                run_manifest_object_key=run_manifest_object_key,
                created_at=now,
            )
            job.state = JobState.SUCCEEDED.value
            job.updated_at = now
            version.state = AuditVersionState.DOCX_READY.value
            version.updated_at = now
            project = get_project(session, job.project_id, lock=True)
            project.status = ProjectState.OUTPUT_AVAILABLE.value
            project.updated_at = now
            session.add(output)
        return to_output_record(output)

    def list_job_events(self, job_id: str, *, after_event_id: int = 0) -> list[JobEventRecord]:
        with self._sessions() as session:
            get_job(session, job_id)
            events = session.scalars(select(JobEventModel).where(
                (JobEventModel.job_id == job_id) & (JobEventModel.event_id > after_event_id)
            ).order_by(JobEventModel.event_id)).all()
            return [to_job_event_record(event) for event in events]

    def retry_job(
        self, job_id: str, *, reason: str | None = None
    ) -> JobRecord:
        now = utcnow()
        with self._sessions.begin() as session:
            job = get_job(session, job_id, lock=True)
            if JobState(job.state) not in {
                JobState.FAILED,
                JobState.INCOMPLETE,
            }:
                raise JobNotRetryableError(job_id)
            if reason:
                session.add(
                    JobEventModel(
                        job_id=job_id,
                        stage="RETRY_QUEUED",
                        message=reason,
                        completed_items=0,
                        total_items=None,
                        warning=False,
                        occurred_at=now,
                    )
                )
            job.state = JobState.QUEUED.value
            job.stage = None
            job.completed_items = 0
            job.total_items = None
            job.current_message = None
            job.error = None
            job.lease_owner = None
            job.lease_expires_at = None
            job.heartbeat_at = None
            job.updated_at = now
            if job.job_type == JobType.AUDIT.value:
                version = get_version(session, job.project_version_id, lock=True)
                version.state = AuditVersionState.AUDITING.value
                version.updated_at = now
        return to_job_record(job)

    def list_output_revisions(self, version_id: str) -> list[OutputRevisionRecord]:
        with self._sessions() as session:
            get_version(session, version_id)
            outputs = session.scalars(
                select(OutputRevisionModel)
                .where(OutputRevisionModel.project_version_id == version_id)
                .order_by(OutputRevisionModel.ordinal.desc())
            ).all()
            return [to_output_record(output) for output in outputs]
