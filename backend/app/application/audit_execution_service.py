"""Durable Audit job orchestration over frozen version candidates."""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from collections.abc import Sequence
from contextlib import AbstractContextManager, ExitStack
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Protocol
from uuid import uuid4

from app.application.audit_pipeline import (
    AuditPipeline,
    PipelineProgress,
    PipelineRequest,
    PipelineResult,
)
from app.domain.audit import (
    AuditInputSnapshotRecord,
    AuditPreflightError,
    AuditProjectRecord,
    IssueOrigin,
    IssueRecord,
    IssueStatus,
    JobRecord,
    JobState,
    JobType,
    LogicalRole,
    OutputRevisionRecord,
    ProjectVersionRecord,
    SourceDocumentRecord,
)

_ELIGIBLE_STATUSES = frozenset(
    {
        IssueStatus.DRAFT,
        IssueStatus.READY_FOR_REVIEW,
        IssueStatus.APPROVED,
        IssueStatus.NEEDS_EVIDENCE,
    }
)
_ROLE_FOLDERS = {
    LogicalRole.SCOPE: "AWP",
    LogicalRole.RISK_CONTEXT: "APM",
    LogicalRole.EVIDENCE: "Process Understanding",
    LogicalRole.CRITERIA: "Process SOP",
    LogicalRole.CONTEXT: "Context",
}


@dataclass(frozen=True)
class CentralAuditAssets:
    guideline_path: Path | None = None
    guideline_version: str = "builtin-default"
    template_path: Path | None = None
    template_version: str = "builtin-default"

    def versions(self) -> dict[str, str]:
        return {
            "guideline": self.guideline_version,
            "template": self.template_version,
        }


@dataclass(frozen=True)
class AuditStart:
    job: JobRecord
    scheduled: bool


@dataclass(frozen=True)
class OutputDownload:
    output: OutputRevisionRecord
    project_id: str
    local_path: Path


class AuditRepository(Protocol):
    def get_project(self, project_id: str) -> AuditProjectRecord: ...
    def get_version(
        self, project_id: str, version_id: str
    ) -> ProjectVersionRecord: ...
    def list_issues(self, version_id: str) -> list[IssueRecord]: ...
    def list_source_documents(
        self, project_id: str
    ) -> list[SourceDocumentRecord]: ...
    def list_jobs_for_version(self, version_id: str) -> list[JobRecord]: ...
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
    ) -> tuple[JobRecord, AuditInputSnapshotRecord]: ...
    def claim_job(
        self, job_id: str, worker_id: str, *, lease_seconds: int = 300
    ) -> JobRecord | None: ...
    def get_job(self, job_id: str) -> JobRecord: ...
    def get_audit_input_snapshot(
        self, job_id: str
    ) -> AuditInputSnapshotRecord: ...
    def append_job_event(
        self,
        job_id: str,
        *,
        stage: str,
        message: str,
        completed_items: int,
        total_items: int | None,
        warning: bool = False,
        checkpoint: dict[str, object] | None = None,
    ): ...
    def publish_output_revision(
        self,
        job_id: str,
        *,
        output_id: str,
        filename: str,
        object_key: str,
        content_hash: str,
        run_manifest_object_key: str | None = None,
    ) -> OutputRevisionRecord: ...
    def finish_job(
        self, job_id: str, *, state: JobState, error: str | None = None
    ) -> JobRecord: ...
    def retry_job(
        self, job_id: str, *, reason: str | None = None
    ) -> JobRecord: ...
    def get_output_revision(
        self, output_id: str
    ) -> tuple[OutputRevisionRecord, str]: ...


class AuditStorage(Protocol):
    def materialize(
        self, object_key: str, *, suffix: str = ""
    ) -> AbstractContextManager[Path]: ...
    def put_output(self, source: Path, object_key: str): ...
    def path_for_download(self, object_key: str) -> Path: ...


class PipelineRunner(Protocol):
    def run(
        self,
        request: PipelineRequest,
        *,
        reporter=None,
    ) -> PipelineResult: ...


class AuditExecutionService:
    pipeline_version = "legacy-eight-stage-v2"

    def __init__(
        self,
        repository: AuditRepository,
        storage: AuditStorage,
        *,
        pipeline: PipelineRunner | None = None,
        assets: CentralAuditAssets | None = None,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._pipeline = pipeline or AuditPipeline()
        self._assets = assets or CentralAuditAssets()

    def start_audit(
        self,
        project_id: str,
        version_id: str,
        *,
        issue_revision: int,
        correlation_id: str,
    ) -> AuditStart:
        version = self._repository.get_version(project_id, version_id)
        if version.issue_revision != issue_revision:
            raise AuditPreflightError(
                "issue_revision is stale; reload the version before "
                "starting an audit."
            )
        issues = tuple(
            issue
            for issue in self._repository.list_issues(version_id)
            if issue.status in _ELIGIBLE_STATUSES
        )
        if not issues:
            raise AuditPreflightError(
                "Audit version does not contain any candidate issues "
                "eligible for output."
            )
        for issue in issues:
            _validate_issue(issue)

        documents = self._repository.list_source_documents(project_id)
        if not documents:
            raise AuditPreflightError(
                "Audit project does not contain an immutable source snapshot."
            )
        issue_payload = {
            "version_id": version_id,
            "issue_revision": issue_revision,
            "issues": [_serialise_issue(issue) for issue in issues],
        }
        asset_versions = self._assets.versions()
        input_hash = _audit_input_hash(
            issue_payload,
            documents,
            asset_versions,
            self.pipeline_version,
        )
        matching = [
            job
            for job in self._repository.list_jobs_for_version(version_id)
            if job.job_type == JobType.AUDIT
            and job.input_hash == input_hash
        ]
        if matching:
            return AuditStart(matching[0], scheduled=False)

        job, _ = self._repository.enqueue_audit_job(
            project_id,
            version_id,
            job_id=str(uuid4()),
            snapshot_id=str(uuid4()),
            input_hash=input_hash,
            issue_payload=issue_payload,
            central_asset_versions=asset_versions,
            correlation_id=correlation_id,
        )
        return AuditStart(job, scheduled=True)

    def run_audit(self, job_id: str) -> None:
        claimed = self._repository.claim_job(
            job_id, f"audit-{uuid4()}", lease_seconds=900
        )
        if claimed is None:
            return
        try:
            snapshot = self._repository.get_audit_input_snapshot(job_id)
            project = self._repository.get_project(claimed.project_id)
            version = self._repository.get_version(
                claimed.project_id, claimed.project_version_id
            )
            documents = self._repository.list_source_documents(
                claimed.project_id
            )
            self._repository.append_job_event(
                job_id,
                stage="PREPARING_SOURCE",
                message=(
                    f"Preparing {len(documents)} immutable source documents"
                ),
                completed_items=0,
                total_items=8,
            )
            with tempfile.TemporaryDirectory(
                prefix=f"audit-{job_id}-"
            ) as temporary:
                workspace = Path(temporary)
                with ExitStack() as stack:
                    self._materialize_source(stack, workspace, documents)
                    self._materialize_assets(workspace)
                    result = self._pipeline.run(
                        PipelineRequest(
                            project_path=workspace,
                            auditor_input=snapshot.issue_payload["issues"],
                            version=version.label,
                            run_directory=workspace / "run",
                            project_name=project.name,
                        ),
                        reporter=lambda progress: self._report_progress(
                            job_id, progress
                        ),
                    )
                output_id = str(uuid4())
                output_key = (
                    f"projects/{claimed.project_id}/versions/"
                    f"{claimed.project_version_id}/outputs/"
                    f"{output_id}.docx"
                )
                stored = self._storage.put_output(
                    result.output_path, output_key
                )
                manifest_path = workspace / "run-manifest.json"
                manifest_path.write_text(
                    json.dumps(
                        {
                            "job_id": job_id,
                            "project_id": claimed.project_id,
                            "version_id": claimed.project_version_id,
                            "version_label": version.label,
                            "input_hash": snapshot.input_hash,
                            "issue_revision": snapshot.issue_revision,
                            "issue_count": result.issue_count,
                            "pipeline_version": self.pipeline_version,
                            "central_asset_versions": (
                                snapshot.central_asset_versions
                            ),
                            "source_documents": [
                                {
                                    "document_id": item.document_id,
                                    "relative_path": item.relative_path,
                                    "content_hash": item.content_hash,
                                }
                                for item in documents
                            ],
                        },
                        indent=2,
                        sort_keys=True,
                    ),
                    encoding="utf-8",
                )
                manifest_key = output_key.removesuffix(
                    ".docx"
                ) + ".manifest.json"
                self._storage.put_output(manifest_path, manifest_key)
                self._repository.append_job_event(
                    job_id,
                    stage="PUBLISHING",
                    message="Publishing immutable DOCX output revision",
                    completed_items=8,
                    total_items=8,
                )
                self._repository.publish_output_revision(
                    job_id,
                    output_id=output_id,
                    filename=result.output_path.name,
                    object_key=output_key,
                    content_hash=stored.content_hash,
                    run_manifest_object_key=manifest_key,
                )
        except Exception as exc:  # noqa: BLE001
            message = str(exc) or exc.__class__.__name__
            try:
                self._repository.append_job_event(
                    job_id,
                    stage="FAILED",
                    message=message,
                    completed_items=0,
                    total_items=8,
                    warning=True,
                )
            finally:
                self._repository.finish_job(
                    job_id, state=JobState.FAILED, error=message
                )

    def retry_audit(
        self, job_id: str, *, reason: str | None = None
    ) -> AuditStart:
        current = self._repository.get_job(job_id)
        if current.job_type != JobType.AUDIT:
            raise ValueError("Only Audit jobs can use Audit retry.")
        return AuditStart(
            self._repository.retry_job(job_id, reason=reason),
            scheduled=True,
        )

    def get_output_download(self, output_id: str) -> OutputDownload:
        output, project_id = self._repository.get_output_revision(output_id)
        return OutputDownload(
            output=output,
            project_id=project_id,
            local_path=self._storage.path_for_download(output.object_key),
        )

    def _materialize_source(
        self,
        stack: ExitStack,
        workspace: Path,
        documents: Sequence[SourceDocumentRecord],
    ) -> None:
        for document in documents:
            suffix = PurePosixPath(document.relative_path).suffix.lower()
            source = stack.enter_context(
                self._storage.materialize(
                    document.original_object_key, suffix=suffix
                )
            )
            folder = _ROLE_FOLDERS[document.logical_role]
            destination = workspace / folder / PurePosixPath(
                document.relative_path
            ).name
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                destination = destination.with_name(
                    f"{document.document_id}-{destination.name}"
                )
            shutil.copy2(source, destination)

    def _materialize_assets(self, workspace: Path) -> None:
        if self._assets.guideline_path is not None:
            destination = workspace / "Guidelines" / (
                self._assets.guideline_path.name
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self._assets.guideline_path, destination)
        if self._assets.template_path is not None:
            destination = workspace / "Output" / "template.docx"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self._assets.template_path, destination)

    def _report_progress(
        self, job_id: str, progress: PipelineProgress
    ) -> None:
        self._repository.append_job_event(
            job_id,
            stage=progress.stage,
            message=progress.message,
            completed_items=progress.completed_steps,
            total_items=progress.total_steps,
            warning=progress.warning,
        )


def _validate_issue(issue: IssueRecord) -> None:
    if not issue.observed_gap.strip():
        raise AuditPreflightError(
            f"Candidate issue {issue.issue_id} requires observed_gap."
        )
    if issue.origin == IssueOrigin.AI_DISCOVERED:
        missing: list[str] = []
        if not (issue.evidence_summary or "").strip():
            missing.append("evidence_summary")
        if not issue.evidence_refs:
            missing.append("evidence_refs")
        if not issue.sop_refs:
            missing.append("sop_refs")
        if missing:
            raise AuditPreflightError(
                f"AI candidate {issue.issue_id} is missing: "
                + ", ".join(missing)
            )


def _serialise_issue(issue: IssueRecord) -> dict[str, Any]:
    return {
        "issue_id": issue.issue_id,
        "origin": issue.origin.value,
        "status": issue.status.value,
        "title_hint": issue.title_hint,
        "observed_gap": issue.observed_gap,
        "evidence_summary": issue.evidence_summary,
        "evidence_refs": list(issue.evidence_refs),
        "sop_refs": list(issue.sop_refs),
        "risk_category": (
            issue.risk_category.value if issue.risk_category else None
        ),
        "confidence": issue.confidence,
        "validation_flags": list(issue.validation_flags),
        "source_refs": [
            {
                "reference_id": ref.reference_id,
                "ref_kind": ref.ref_kind.value,
                "document_id": ref.document_id,
                "unit_id": ref.unit_id,
                "location": ref.location,
                "quote": ref.quote,
            }
            for ref in issue.source_refs
        ],
    }


def _audit_input_hash(
    issue_payload: dict[str, Any],
    documents: Sequence[SourceDocumentRecord],
    asset_versions: dict[str, str],
    pipeline_version: str,
) -> str:
    payload = {
        "issue_payload": issue_payload,
        "documents": [
            {
                "document_id": item.document_id,
                "content_hash": item.content_hash,
            }
            for item in sorted(documents, key=lambda item: item.document_id)
        ],
        "central_asset_versions": asset_versions,
        "pipeline_version": pipeline_version,
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"
