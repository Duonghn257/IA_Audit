from datetime import datetime, timedelta, timezone

import pytest
from app.application.audit_workspace_service import AuditWorkspaceService
from app.domain.audit import (
    ActiveJobConflictError,
    AuditVersionState,
    DuplicateProjectNameError,
    IssueOrigin,
    IssueStatus,
    JobNotRetryableError,
    JobState,
    JobType,
    LogicalRole,
    OutputStatus,
    SourceReferenceInput,
    SourceRefKind,
    UploadFileInput,
    UploadFileValidation,
    VersionConflictError,
)
from app.infrastructure.audit_repository import (
    SourceDocumentModel,
    SqlAlchemyAuditRepository,
)
from app.infrastructure.database import Database
from sqlalchemy import select


def _create_project(repository: SqlAlchemyAuditRepository) -> tuple[str, str]:
    repository.create_upload_session(
        session_id="session-1",
        files=[
            UploadFileInput(
                file_id="file-1",
                relative_path="Evidence/access-review.xlsx",
                size_bytes=128,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                staging_object_key="staging/session-1/file-1",
            )
        ],
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    repository.complete_upload_validation(
        "session-1",
        validation_report={"errors": [], "warnings": []},
        files=[
            UploadFileValidation(
                file_id="file-1",
                content_hash="sha256:file-1",
                logical_role=LogicalRole.EVIDENCE,
                readability_status="READABLE",
            )
        ],
        valid=True,
    )
    project, version = repository.promote_upload_session(
        "session-1",
        project_id="project-1",
        source_snapshot_id="snapshot-1",
        version_id="version-1",
        name="FY2026 Access Review",
        manifest_hash="sha256:manifest-1",
        source_object_prefix="projects/project-1/source",
    )
    assert project.next_version_number == 2
    assert version.label == "v0.1"
    return project.project_id, version.version_id


def _document_id(database: Database) -> str:
    with database.sessions() as session:
        return session.scalars(select(SourceDocumentModel.document_id)).one()


def test_promotes_valid_staging_to_project_and_rejects_duplicate_name(tmp_path) -> None:
    database = Database(f"sqlite+pysqlite:///{tmp_path / 'audit.db'}")
    database.create_schema()
    repository = SqlAlchemyAuditRepository(database.sessions)

    _create_project(repository)
    assert repository.get_upload_session("session-1").state.value == "PROMOTED"

    repository.create_upload_session(
        session_id="session-2",
        files=[
            UploadFileInput(
                file_id="file-2",
                relative_path="Evidence/access-review.xlsx",
                size_bytes=128,
                content_type=None,
                staging_object_key="staging/session-2/file-2",
            )
        ],
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    repository.complete_upload_validation(
        "session-2",
        validation_report={"errors": [], "warnings": []},
        files=[
            UploadFileValidation(
                file_id="file-2",
                content_hash="sha256:file-1",
                logical_role=LogicalRole.EVIDENCE,
                readability_status="READABLE",
            )
        ],
        valid=True,
    )

    with pytest.raises(DuplicateProjectNameError):
        repository.promote_upload_session(
            "session-2",
            project_id="project-2",
            source_snapshot_id="snapshot-2",
            version_id="version-2",
            name="FY2026 Access Review",
            manifest_hash="sha256:manifest-2",
            source_object_prefix="projects/project-2/source",
        )

    project, version = repository.promote_upload_session(
        "session-2",
        project_id="project-2",
        source_snapshot_id="snapshot-2",
        version_id="version-2",
        name="FY2026 Access Review - rerun",
        manifest_hash="sha256:manifest-2",
        source_object_prefix="projects/project-2/source",
    )
    assert project.project_id == "project-2"
    assert version.label == "v0.1"
    database.dispose()


def test_versions_issues_jobs_and_output_revisions_are_isolated(tmp_path) -> None:
    database = Database(f"sqlite+pysqlite:///{tmp_path / 'audit.db'}")
    database.create_schema()
    repository = SqlAlchemyAuditRepository(database.sessions)
    project_id, version_one_id = _create_project(repository)
    document_id = _document_id(database)
    reference = SourceReferenceInput(
        reference_id="ref-1",
        ref_kind=SourceRefKind.EVIDENCE,
        document_id=document_id,
        location={"sheet": "Access review", "range": "A1:B2"},
    )
    issue = repository.create_issue(
        version_one_id,
        issue_id="issue-1",
        origin=IssueOrigin.MANUAL,
        status=IssueStatus.APPROVED,
        observed_gap="Review evidence is incomplete.",
        source_refs=[reference],
    )
    issue = AuditWorkspaceService(repository).set_issue_disposition(
        version_one_id,
        issue.issue_id,
        expected_row_version=issue.row_version,
        status=IssueStatus.NEEDS_EVIDENCE,
    )
    assert issue.source_refs[0].reference_id == reference.reference_id
    version_two = repository.create_next_version(
        project_id,
        base_version_id=version_one_id,
        version_id="version-2",
    )
    copied_issue = repository.list_issues(version_two.version_id)[0]
    assert copied_issue.issue_id != issue.issue_id
    assert copied_issue.observed_gap == issue.observed_gap
    assert copied_issue.source_refs[0].document_id == document_id
    assert version_two.label == "v0.2"
    assert repository.get_version(project_id, version_two.version_id) == version_two

    job, snapshot = repository.enqueue_audit_job(
        project_id,
        version_two.version_id,
        job_id="job-1",
        snapshot_id="input-1",
        input_hash="sha256:audit-input-1",
        issue_payload={"issue_ids": [copied_issue.issue_id]},
        central_asset_versions={"guideline": "1", "template": "1"},
        correlation_id="corr-1",
    )
    assert snapshot.job_id == job.job_id
    output = repository.publish_output_revision(
        job.job_id,
        output_id="output-1",
        filename="FY2026 Access Review_Issue Log v0.2.docx",
        object_key="outputs/project-1/v0.2/revision-1.docx",
        content_hash="sha256:output-1",
    )
    assert output.status == OutputStatus.CURRENT
    assert repository.list_output_revisions(version_two.version_id) == [output]

    updated = repository.update_issue(
        version_two.version_id,
        copied_issue.issue_id,
        expected_row_version=copied_issue.row_version,
        status=IssueStatus.APPROVED,
        observed_gap="Review evidence is incomplete and not retained.",
        title_hint=None,
        evidence_summary=None,
        risk_category=None,
        confidence=None,
        validation_flags=[],
        source_refs=[],
    )
    assert updated.row_version == copied_issue.row_version + 1
    assert repository.list_versions(project_id)[1].state == AuditVersionState.STALE_OUTPUT
    with pytest.raises(VersionConflictError):
        repository.update_issue(
            version_two.version_id,
            copied_issue.issue_id,
            expected_row_version=copied_issue.row_version,
            status=IssueStatus.APPROVED,
            observed_gap="Stale update",
            title_hint=None,
            evidence_summary=None,
            risk_category=None,
            confidence=None,
            validation_flags=[],
            source_refs=[],
        )
    assert repository.get_issue(version_one_id, issue.issue_id).observed_gap == (
        "Review evidence is incomplete."
    )
    database.dispose()


def test_jobs_are_idempotent_and_persist_events(tmp_path) -> None:
    database = Database(f"sqlite+pysqlite:///{tmp_path / 'audit.db'}")
    database.create_schema()
    repository = SqlAlchemyAuditRepository(database.sessions)
    project_id, version_id = _create_project(repository)
    job = repository.enqueue_job(
        project_id,
        version_id,
        job_id="job-discovery-1",
        job_type=JobType.DISCOVERY,
        input_hash="sha256:discovery-1",
        correlation_id="corr-discovery-1",
        stage="QUEUED",
    )
    with pytest.raises(ActiveJobConflictError):
        repository.enqueue_job(
            project_id,
            version_id,
            job_id="job-discovery-2",
            job_type=JobType.DISCOVERY,
            input_hash="sha256:discovery-1",
            correlation_id="corr-discovery-2",
        )
    claimed = repository.claim_next_job("worker-1")
    assert claimed is not None
    assert claimed.job_id == job.job_id
    assert claimed.state == JobState.RUNNING
    event = repository.append_job_event(
        job.job_id,
        stage="PARSING",
        message="Parsing evidence...",
        completed_items=1,
        total_items=2,
    )
    assert repository.list_job_events(job.job_id) == [event]
    assert repository.finish_job(job.job_id, state=JobState.SUCCEEDED).state == JobState.SUCCEEDED
    assert repository.list_versions(project_id)[0].state == AuditVersionState.CANDIDATES_READY
    assert repository.get_job(job.job_id).state == JobState.SUCCEEDED
    assert repository.list_jobs_for_version(version_id)[0].job_id == job.job_id
    with pytest.raises(JobNotRetryableError):
        repository.retry_job(job.job_id)
    database.dispose()
