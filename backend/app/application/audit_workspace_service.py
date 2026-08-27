"""Application service for the editable audit workspace API."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Protocol
from uuid import uuid4

from app.domain.audit import (
    AuditProjectRecord,
    IssueOrigin,
    IssueRecord,
    IssueStatus,
    JobEventRecord,
    JobRecord,
    OutputRevisionRecord,
    OutputStatus,
    ProjectVersionRecord,
    RiskCategory,
    SourceDocumentRecord,
    SourceReferenceInput,
)


class AuditWorkspaceRepository(Protocol):
    def get_project(self, project_id: str) -> AuditProjectRecord: ...
    def list_source_documents(
        self, project_id: str
    ) -> list[SourceDocumentRecord]: ...
    def list_versions(self, project_id: str) -> list[ProjectVersionRecord]: ...
    def get_version(
        self, project_id: str, version_id: str
    ) -> ProjectVersionRecord: ...
    def create_next_version(
        self,
        project_id: str,
        *,
        base_version_id: str,
        version_id: str,
        created_by_user_id: str,
        created_by_name: str,
    ) -> ProjectVersionRecord: ...
    def list_issues(self, version_id: str) -> list[IssueRecord]: ...
    def get_issue(self, version_id: str, issue_id: str) -> IssueRecord: ...
    def create_issue(self, version_id: str, **values: object) -> IssueRecord: ...
    def update_issue(self, version_id: str, issue_id: str, **values: object) -> IssueRecord: ...
    def get_job(self, job_id: str) -> JobRecord: ...
    def list_jobs_for_version(self, version_id: str) -> list[JobRecord]: ...
    def list_job_events(self, job_id: str, *, after_event_id: int = 0) -> list[JobEventRecord]: ...
    def retry_job(
        self, job_id: str, *, reason: str | None = None
    ) -> JobRecord: ...
    def list_output_revisions(self, version_id: str) -> list[OutputRevisionRecord]: ...


@dataclass(frozen=True)
class VersionWorkspace:
    version: ProjectVersionRecord
    issue_counts: dict[str, int]
    latest_job: JobRecord | None
    output_available: bool
    output_status: OutputStatus | None


@dataclass(frozen=True)
class SourceFolder:
    name: str
    logical_role: str
    files: tuple[SourceDocumentRecord, ...]


@dataclass(frozen=True)
class SourceTree:
    snapshot_id: str
    folders: tuple[SourceFolder, ...]


_SOURCE_FOLDER_NAMES = {
    "SCOPE": "AWP",
    "RISK_CONTEXT": "APM",
    "EVIDENCE": "Process Understanding",
    "CRITERIA": "Process SOP",
}
_SOURCE_ROLE_ORDER = tuple(_SOURCE_FOLDER_NAMES)


class AuditWorkspaceService:
    def __init__(self, repository: AuditWorkspaceRepository) -> None:
        self._repository = repository

    def list_versions(self, project_id: str) -> list[VersionWorkspace]:
        return [self._workspace(version) for version in self._repository.list_versions(project_id)]

    def get_source_tree(self, project_id: str) -> SourceTree:
        project = self._repository.get_project(project_id)
        documents = self._repository.list_source_documents(project_id)
        grouped: dict[str, list[SourceDocumentRecord]] = {}
        for document in documents:
            grouped.setdefault(document.logical_role.value, []).append(document)

        ordered_roles = [role for role in _SOURCE_ROLE_ORDER if role in grouped]
        ordered_roles.extend(sorted(set(grouped) - set(ordered_roles)))
        folders = tuple(
            SourceFolder(
                name=_SOURCE_FOLDER_NAMES.get(
                    role,
                    PurePosixPath(grouped[role][0].relative_path).parent.name,
                ),
                logical_role=role,
                files=tuple(grouped[role]),
            )
            for role in ordered_roles
        )
        return SourceTree(snapshot_id=project.source_snapshot_id, folders=folders)

    def get_version(self, project_id: str, version_id: str) -> VersionWorkspace:
        return self._workspace(self._repository.get_version(project_id, version_id))

    def create_version(
        self,
        project_id: str,
        base_version_id: str,
        *,
        created_by_user_id: str,
        created_by_name: str,
    ) -> VersionWorkspace:
        version = self._repository.create_next_version(
            project_id,
            base_version_id=base_version_id,
            version_id=str(uuid4()),
            created_by_user_id=created_by_user_id,
            created_by_name=created_by_name,
        )
        return self._workspace(version)

    def list_issues(self, version_id: str) -> list[IssueRecord]:
        return self._repository.list_issues(version_id)

    def get_issue(self, version_id: str, issue_id: str) -> IssueRecord:
        return self._repository.get_issue(version_id, issue_id)

    def create_manual_issue(
        self,
        version_id: str,
        *,
        status: IssueStatus,
        observed_gap: str,
        title_hint: str | None,
        evidence_summary: str | None,
        evidence_refs: Sequence[str],
        sop_refs: Sequence[str],
        risk_category: RiskCategory | None,
        source_refs: Sequence[SourceReferenceInput],
    ) -> IssueRecord:
        return self._repository.create_issue(
            version_id,
            issue_id=str(uuid4()),
            origin=IssueOrigin.MANUAL,
            status=status,
            observed_gap=observed_gap,
            title_hint=title_hint,
            evidence_summary=evidence_summary,
            evidence_refs=evidence_refs,
            sop_refs=sop_refs,
            risk_category=risk_category,
            confidence=None,
            validation_flags=(),
            source_refs=source_refs,
        )

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
        evidence_refs: Sequence[str],
        sop_refs: Sequence[str],
        risk_category: RiskCategory | None,
        confidence: float | None,
        validation_flags: Sequence[str],
        source_refs: Sequence[SourceReferenceInput],
    ) -> IssueRecord:
        return self._repository.update_issue(
            version_id,
            issue_id,
            expected_row_version=expected_row_version,
            status=status,
            observed_gap=observed_gap,
            title_hint=title_hint,
            evidence_summary=evidence_summary,
            evidence_refs=evidence_refs,
            sop_refs=sop_refs,
            risk_category=risk_category,
            confidence=confidence,
            validation_flags=validation_flags,
            source_refs=source_refs,
        )

    def set_issue_disposition(
        self,
        version_id: str,
        issue_id: str,
        *,
        expected_row_version: int,
        status: IssueStatus,
    ) -> IssueRecord:
        allowed = {
            IssueStatus.APPROVED,
            IssueStatus.NEEDS_EVIDENCE,
            IssueStatus.REJECTED,
            IssueStatus.OUT_OF_SCOPE,
        }
        if status not in allowed:
            raise ValueError(
                "Disposition status must be APPROVED, NEEDS_EVIDENCE, "
                "REJECTED or OUT_OF_SCOPE."
            )
        current = self.get_issue(version_id, issue_id)
        return self.update_issue(
            version_id,
            issue_id,
            expected_row_version=expected_row_version,
            status=status,
            observed_gap=current.observed_gap,
            title_hint=current.title_hint,
            evidence_summary=current.evidence_summary,
            evidence_refs=current.evidence_refs,
            sop_refs=current.sop_refs,
            risk_category=current.risk_category,
            confidence=current.confidence,
            validation_flags=current.validation_flags,
            source_refs=[
                SourceReferenceInput(
                    reference_id=reference.reference_id,
                    ref_kind=reference.ref_kind,
                    document_id=reference.document_id,
                    unit_id=reference.unit_id,
                    location=reference.location,
                    quote=reference.quote,
                )
                for reference in current.source_refs
            ],
        )

    def get_job(self, job_id: str) -> JobRecord:
        return self._repository.get_job(job_id)

    def list_job_events(self, job_id: str, after_event_id: int = 0) -> list[JobEventRecord]:
        return self._repository.list_job_events(job_id, after_event_id=after_event_id)

    def retry_job(
        self, job_id: str, *, reason: str | None = None
    ) -> JobRecord:
        return self._repository.retry_job(job_id, reason=reason)

    def list_outputs(self, version_id: str) -> list[OutputRevisionRecord]:
        return self._repository.list_output_revisions(version_id)

    def _workspace(self, version: ProjectVersionRecord) -> VersionWorkspace:
        counts: dict[str, int] = {}
        for issue in self._repository.list_issues(version.version_id):
            counts[issue.status.value] = counts.get(issue.status.value, 0) + 1
        jobs = self._repository.list_jobs_for_version(version.version_id)
        outputs = self._repository.list_output_revisions(version.version_id)
        return VersionWorkspace(
            version,
            counts,
            jobs[0] if jobs else None,
            bool(outputs),
            outputs[0].status if outputs else None,
        )
