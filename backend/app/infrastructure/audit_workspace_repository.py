"""Persistence operations for projects, versions, issues and citations."""
from __future__ import annotations

from collections.abc import Sequence
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.audit import (
    AuditIssueNotFoundError,
    AuditProjectRecord,
    AuditVersionNotFoundError,
    AuditVersionState,
    IssueOrigin,
    IssueRecord,
    IssueStatus,
    ProjectVersionRecord,
    SourceReferenceInput,
    SourceRefKind,
    VersionConflictError,
)
from app.infrastructure.audit_models import IssueModel, ProjectVersionModel
from app.infrastructure.audit_persistence import (
    get_issue,
    get_project,
    get_snapshot,
    get_version,
    next_version_number,
    source_ref_model,
    to_issue_record,
    to_project_record,
    to_version_record,
    touch_issue_workspace,
    utcnow,
    validate_source_refs,
)


class SqlAlchemyAuditWorkspaceRepository:
    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def get_project(self, project_id: str) -> AuditProjectRecord:
        with self._sessions() as session:
            project = get_project(session, project_id)
            snapshot = get_snapshot(session, project_id)
            return to_project_record(project, snapshot, next_version_number(session, project_id))

    def list_versions(self, project_id: str) -> list[ProjectVersionRecord]:
        with self._sessions() as session:
            get_project(session, project_id)
            versions = session.scalars(select(ProjectVersionModel).where(
                ProjectVersionModel.project_id == project_id
            ).order_by(ProjectVersionModel.sequence_no)).all()
            return [to_version_record(version) for version in versions]

    def get_version(self, project_id: str, version_id: str) -> ProjectVersionRecord:
        with self._sessions() as session:
            version = get_version(session, version_id)
            if version.project_id != project_id:
                raise AuditVersionNotFoundError(version_id)
            return to_version_record(version)

    def create_next_version(
        self,
        project_id: str,
        *,
        base_version_id: str,
        version_id: str,
    ) -> ProjectVersionRecord:
        now = utcnow()
        with self._sessions.begin() as session:
            get_project(session, project_id, lock=True)
            base = get_version(session, base_version_id)
            if base.project_id != project_id:
                raise AuditVersionNotFoundError(base_version_id)
            sequence_no = next_version_number(session, project_id)
            version = ProjectVersionModel(
                version_id=version_id,
                project_id=project_id,
                sequence_no=sequence_no,
                label=f"v0.{sequence_no}",
                base_version_id=base_version_id,
                state=AuditVersionState.DRAFT.value,
                issue_revision=base.issue_revision,
                created_at=now,
                updated_at=now,
            )
            session.add(version)
            for issue in session.scalars(select(IssueModel).where(
                IssueModel.project_version_id == base_version_id
            )):
                copied = IssueModel(
                    issue_id=str(uuid4()),
                    project_version_id=version_id,
                    origin=issue.origin,
                    status=issue.status,
                    title_hint=issue.title_hint,
                    observed_gap=issue.observed_gap,
                    evidence_summary=issue.evidence_summary,
                    evidence_refs=list(issue.evidence_refs or ()),
                    sop_refs=list(issue.sop_refs or ()),
                    risk_category=issue.risk_category,
                    confidence=issue.confidence,
                    validation_flags=list(issue.validation_flags),
                    row_version=1,
                    created_at=now,
                    updated_at=now,
                )
                session.add(copied)
                session.flush()
                copied.source_refs.extend(
                    source_ref_model(
                        SourceReferenceInput(
                            reference_id=str(uuid4()),
                            ref_kind=SourceRefKind(ref.ref_kind),
                            document_id=ref.document_id,
                            unit_id=ref.unit_id,
                            location=ref.location,
                            quote=ref.quote,
                        ),
                        copied.issue_id,
                    )
                    for ref in issue.source_refs
                )
        return to_version_record(version)

    def create_issue(
        self,
        version_id: str,
        *,
        issue_id: str,
        origin: IssueOrigin,
        status: IssueStatus,
        observed_gap: str,
        title_hint: str | None = None,
        evidence_summary: str | None = None,
        evidence_refs: Sequence[str] = (),
        sop_refs: Sequence[str] = (),
        risk_category: str | None = None,
        confidence: float | None = None,
        validation_flags: Sequence[str] = (),
        source_refs: Sequence[SourceReferenceInput] = (),
    ) -> IssueRecord:
        if not observed_gap.strip():
            raise ValueError("observed_gap must not be empty")
        now = utcnow()
        with self._sessions.begin() as session:
            version = get_version(session, version_id, lock=True)
            validate_source_refs(session, version.project_id, source_refs)
            issue = IssueModel(
                issue_id=issue_id,
                project_version_id=version_id,
                origin=origin.value,
                status=status.value,
                title_hint=title_hint,
                observed_gap=observed_gap,
                evidence_summary=evidence_summary,
                evidence_refs=list(evidence_refs),
                sop_refs=list(sop_refs),
                risk_category=risk_category,
                confidence=confidence,
                validation_flags=list(validation_flags),
                row_version=1,
                created_at=now,
                updated_at=now,
            )
            session.add(issue)
            session.add_all(source_ref_model(ref, issue_id) for ref in source_refs)
            touch_issue_workspace(session, version, now)
            session.flush()
            return to_issue_record(issue)

    def get_issue(self, version_id: str, issue_id: str) -> IssueRecord:
        with self._sessions() as session:
            issue = get_issue(session, issue_id)
            if issue.project_version_id != version_id:
                raise AuditIssueNotFoundError(issue_id)
            return to_issue_record(issue)

    def list_issues(self, version_id: str) -> list[IssueRecord]:
        with self._sessions() as session:
            get_version(session, version_id)
            issues = session.scalars(select(IssueModel).where(
                IssueModel.project_version_id == version_id
            ).order_by(IssueModel.created_at, IssueModel.issue_id)).all()
            return [to_issue_record(issue) for issue in issues]

    def update_issue(
        self,
        version_id: str,
        issue_id: str,
        *,
        expected_row_version: int,
        status: IssueStatus,
        observed_gap: str,
        title_hint: str | None,
        evidence_summary: str | None,
        evidence_refs: Sequence[str] = (),
        sop_refs: Sequence[str] = (),
        risk_category: str | None,
        confidence: float | None,
        validation_flags: Sequence[str],
        source_refs: Sequence[SourceReferenceInput],
    ) -> IssueRecord:
        if not observed_gap.strip():
            raise ValueError("observed_gap must not be empty")
        now = utcnow()
        with self._sessions.begin() as session:
            issue = get_issue(session, issue_id, lock=True)
            if issue.project_version_id != version_id:
                raise AuditIssueNotFoundError(issue_id)
            if issue.row_version != expected_row_version:
                raise VersionConflictError(issue_id)
            version = get_version(session, version_id, lock=True)
            validate_source_refs(session, version.project_id, source_refs)
            issue.status = status.value
            issue.observed_gap = observed_gap
            issue.title_hint = title_hint
            issue.evidence_summary = evidence_summary
            issue.evidence_refs = list(evidence_refs)
            issue.sop_refs = list(sop_refs)
            issue.risk_category = risk_category
            issue.confidence = confidence
            issue.validation_flags = list(validation_flags)
            issue.row_version += 1
            issue.updated_at = now
            issue.source_refs.clear()
            issue.source_refs.extend(source_ref_model(ref, issue_id) for ref in source_refs)
            touch_issue_workspace(session, version, now)
            session.flush()
            return to_issue_record(issue)
