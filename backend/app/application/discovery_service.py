"""Durable source-discovery orchestration with an injectable AI engine."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from contextlib import AbstractContextManager, ExitStack
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol
from uuid import uuid4

from app.domain.audit import (
    ActiveJobConflictError,
    CandidateIssueInput,
    JobRecord,
    JobState,
    JobType,
    LogicalRole,
    SourceDocumentRecord,
    SourceNotReadyError,
)

_REQUIRED_ROLES = frozenset(
    {
        LogicalRole.SCOPE,
        LogicalRole.RISK_CONTEXT,
        LogicalRole.EVIDENCE,
        LogicalRole.CRITERIA,
    }
)


@dataclass(frozen=True)
class DiscoveryDocument:
    document_id: str
    relative_path: str
    logical_role: LogicalRole
    content_hash: str
    local_path: Path


@dataclass(frozen=True)
class DiscoveryStart:
    job: JobRecord
    scheduled: bool


class DiscoveryEngine(Protocol):
    engine_version: str

    def discover(
        self, documents: Sequence[DiscoveryDocument]
    ) -> Sequence[CandidateIssueInput]: ...


class DiscoveryRepository(Protocol):
    def get_version(self, project_id: str, version_id: str): ...
    def list_source_documents(
        self, project_id: str
    ) -> list[SourceDocumentRecord]: ...
    def list_jobs_for_version(self, version_id: str) -> list[JobRecord]: ...
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
    ) -> JobRecord: ...
    def claim_job(
        self, job_id: str, worker_id: str, *, lease_seconds: int = 300
    ) -> JobRecord | None: ...
    def get_job(self, job_id: str) -> JobRecord: ...
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
    def complete_discovery(
        self, job_id: str, candidates: Sequence[CandidateIssueInput]
    ) -> JobRecord: ...
    def finish_job(
        self, job_id: str, *, state: JobState, error: str | None = None
    ) -> JobRecord: ...
    def retry_job(
        self, job_id: str, *, reason: str | None = None
    ) -> JobRecord: ...


class DiscoveryStorage(Protocol):
    def materialize(
        self, object_key: str, *, suffix: str = ""
    ) -> AbstractContextManager[Path]: ...


class UnavailableDiscoveryEngine:
    """Default adapter until the AI team provides the real implementation."""

    engine_version = "unavailable-v1"

    def discover(
        self, documents: Sequence[DiscoveryDocument]
    ) -> Sequence[CandidateIssueInput]:
        del documents
        raise RuntimeError(
            "AI discovery engine is not configured. Install the AI adapter "
            "and retry this job."
        )


class DiscoveryService:
    def __init__(
        self,
        repository: DiscoveryRepository,
        storage: DiscoveryStorage,
        engine: DiscoveryEngine,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._engine = engine

    def start_discovery(
        self,
        project_id: str,
        version_id: str,
        *,
        force: bool,
        correlation_id: str,
    ) -> DiscoveryStart:
        self._repository.get_version(project_id, version_id)
        documents = self._source_documents(project_id)
        input_hash = _discovery_input_hash(
            version_id, documents, self._engine.engine_version
        )
        matching = [
            job
            for job in self._repository.list_jobs_for_version(version_id)
            if job.job_type == JobType.DISCOVERY
            and job.input_hash == input_hash
        ]
        if matching and not force:
            return DiscoveryStart(matching[0], scheduled=False)
        active = next((job for job in matching if job.state.is_active), None)
        if active is not None:
            raise ActiveJobConflictError(active.job_id)
        job = self._repository.enqueue_job(
            project_id,
            version_id,
            job_id=str(uuid4()),
            job_type=JobType.DISCOVERY,
            input_hash=input_hash,
            correlation_id=correlation_id,
            stage="QUEUED",
        )
        return DiscoveryStart(job, scheduled=True)

    def run_discovery(self, job_id: str) -> None:
        claimed = self._repository.claim_job(
            job_id, f"discovery-{uuid4()}", lease_seconds=300
        )
        if claimed is None:
            return
        try:
            documents = self._source_documents(claimed.project_id)
            total = len(documents)
            self._repository.append_job_event(
                job_id,
                stage="PREPARING_SOURCE",
                message=f"Preparing {total} immutable source documents",
                completed_items=0,
                total_items=total,
            )
            with ExitStack() as stack:
                engine_documents = tuple(
                    DiscoveryDocument(
                        document_id=document.document_id,
                        relative_path=document.relative_path,
                        logical_role=document.logical_role,
                        content_hash=document.content_hash,
                        local_path=stack.enter_context(
                            self._storage.materialize(
                                document.original_object_key,
                                suffix=PurePosixPath(
                                    document.relative_path
                                ).suffix.lower(),
                            )
                        ),
                    )
                    for document in documents
                )
                discovered = self._engine.discover(engine_documents)
            candidates = tuple(
                _normalise_candidate(candidate) for candidate in discovered
            )
            self._repository.append_job_event(
                job_id,
                stage="SAVING_CANDIDATES",
                message=f"Saving {len(candidates)} candidate issues",
                completed_items=total,
                total_items=total,
            )
            self._repository.complete_discovery(job_id, candidates)
        except Exception as exc:  # noqa: BLE001
            message = str(exc) or exc.__class__.__name__
            try:
                self._repository.append_job_event(
                    job_id,
                    stage="FAILED",
                    message=message,
                    completed_items=0,
                    total_items=None,
                    warning=True,
                )
            finally:
                self._repository.finish_job(
                    job_id, state=JobState.FAILED, error=message
                )

    def retry_discovery(
        self, job_id: str, *, reason: str | None = None
    ) -> DiscoveryStart:
        current = self._repository.get_job(job_id)
        if current.job_type != JobType.DISCOVERY:
            raise ValueError("Only Discovery jobs can use Discovery retry.")
        job = self._repository.retry_job(job_id, reason=reason)
        return DiscoveryStart(job, scheduled=True)

    def _source_documents(
        self, project_id: str
    ) -> list[SourceDocumentRecord]:
        documents = self._repository.list_source_documents(project_id)
        available = {document.logical_role for document in documents}
        missing = sorted(role.value for role in _REQUIRED_ROLES - available)
        if missing:
            raise SourceNotReadyError(
                "Immutable source is missing required roles: "
                + ", ".join(missing)
            )
        return documents


def _normalise_candidate(value: CandidateIssueInput) -> CandidateIssueInput:
    title = value.title_hint.strip()
    observed_gap = value.observed_gap.strip()
    evidence_summary = value.evidence_summary.strip()
    if not title or not observed_gap or not evidence_summary:
        raise ValueError(
            "Discovery candidate requires title_hint, observed_gap and "
            "evidence_summary."
        )
    evidence_refs = _normalise_refs(value.evidence_refs, "evidence_refs")
    sop_refs = _normalise_refs(value.sop_refs, "sop_refs")
    return CandidateIssueInput(
        title_hint=title,
        observed_gap=observed_gap,
        evidence_summary=evidence_summary,
        evidence_refs=evidence_refs,
        sop_refs=sop_refs,
        risk_category=value.risk_category.strip(),
    )


def _normalise_refs(values: Sequence[str], field: str) -> tuple[str, ...]:
    refs = tuple(dict.fromkeys(value.strip() for value in values if value.strip()))
    if not refs:
        raise ValueError(f"Discovery candidate requires at least one {field} entry.")
    return refs


def _discovery_input_hash(
    version_id: str,
    documents: Sequence[SourceDocumentRecord],
    engine_version: str,
) -> str:
    payload = {
        "version_id": version_id,
        "engine_version": engine_version,
        "documents": [
            {
                "document_id": item.document_id,
                "relative_path": item.relative_path,
                "logical_role": item.logical_role.value,
                "content_hash": item.content_hash,
            }
            for item in sorted(documents, key=lambda item: item.relative_path)
        ],
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"
