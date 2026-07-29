"""Project upload, processing and retention orchestration."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Sequence
from uuid import uuid4

from app.application.audit_pipeline import (
    AuditPipeline,
    PipelineProgress,
    PipelineRequest,
)
from app.application.ports import ProjectRepository, ProjectStorage
from app.application.project_files import IncomingProjectFile
from app.domain.projects import ProjectEvent, ProjectRecord

PipelineFactory = Callable[[], AuditPipeline]


class ProjectManager:
    def __init__(
        self,
        *,
        repository: ProjectRepository,
        storage: ProjectStorage,
        raw_retention_days: int,
        max_workers: int,
        pipeline_factory: PipelineFactory = AuditPipeline,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._raw_retention_days = raw_retention_days
        self._pipeline_factory = pipeline_factory
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="audit-project",
        )

    def submit_upload(
        self,
        *,
        name: str,
        files: Sequence[IncomingProjectFile],
    ) -> ProjectRecord:
        project_id = str(uuid4())
        now = datetime.now(timezone.utc)
        self._repository.create(
            project_id=project_id,
            name=name,
            raw_expires_at=now + timedelta(days=self._raw_retention_days),
        )
        try:
            stored = self._storage.save_uploads(project_id, files)
            self._repository.set_upload_saved(
                project_id,
                storage_path=str(stored.project_path),
            )
            self._repository.append_progress(
                project_id,
                stage="UPLOAD",
                message=(
                    f"Uploaded {stored.file_count} files "
                    f"({stored.total_bytes:,} bytes)"
                ),
                completed_steps=0,
                total_steps=8,
                warning=False,
            )
            project = self._repository.mark_processing(project_id)
        except Exception as exc:
            self._repository.mark_failed(project_id, str(exc))
            raise

        self._executor.submit(
            self._execute,
            project_id,
            stored.project_path,
        )
        return project

    def get(self, project_id: str) -> ProjectRecord:
        return self._repository.get(project_id)

    def list(self) -> list[ProjectRecord]:
        return self._repository.list()

    def list_events(
        self,
        project_id: str,
        *,
        after_event_id: int = 0,
    ) -> list[ProjectEvent]:
        return self._repository.list_events(
            project_id,
            after_event_id=after_event_id,
        )

    def cleanup_expired_inputs(self) -> int:
        now = datetime.now(timezone.utc)
        expired = self._repository.list_expired_raw(now)
        for project in expired:
            self._storage.delete_raw_input(project.project_id)
            self._repository.mark_raw_deleted(project.project_id, now)
        return len(expired)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=False)

    def _execute(self, project_id: str, project_path: Path) -> None:
        try:
            issues_path = project_path / "sample_issues.json"
            if not issues_path.is_file():
                raise ValueError(
                    "Missing sample_issues.json at the root of the uploaded "
                    "project folder."
                )
            result = self._pipeline_factory().run(
                PipelineRequest(
                    project_path=project_path,
                    issues_path=issues_path,
                ),
                reporter=lambda progress: self._report(
                    project_id,
                    progress,
                ),
            )
            output_path = self._storage.promote_output(
                project_id,
                result.output_path,
            )
            self._repository.mark_completed(
                project_id,
                output_path=str(output_path),
                version=result.version,
                issue_count=result.issue_count,
            )
        except Exception as exc:
            self._repository.mark_failed(project_id, str(exc))

    def _report(
        self,
        project_id: str,
        progress: PipelineProgress,
    ) -> None:
        self._repository.append_progress(
            project_id,
            stage=progress.stage,
            message=progress.message,
            completed_steps=progress.completed_steps,
            total_steps=progress.total_steps,
            warning=progress.warning,
        )

