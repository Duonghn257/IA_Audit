"""Application service for background audit-run execution."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from app.application.audit_pipeline import AuditPipeline, PipelineRequest
from app.application.ports import RunStore
from app.domain.runs import RunEvent, RunRecord

PipelineFactory = Callable[[], AuditPipeline]


class RunManager:
    """Runs one POC pipeline at a time and exposes durable-shaped state."""

    def __init__(
        self,
        *,
        store: RunStore,
        pipeline_factory: PipelineFactory = AuditPipeline,
        max_workers: int = 1,
    ) -> None:
        self._store = store
        self._pipeline_factory = pipeline_factory
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="audit-run",
        )

    def submit(self, request: PipelineRequest) -> RunRecord:
        record = self._store.create(
            project_path=str(request.project_path),
            issues_path=str(request.issues_path),
        )
        self._executor.submit(self._execute, record.run_id, request)
        return record

    def get(self, run_id: str) -> RunRecord:
        return self._store.get(run_id)

    def list(self) -> list[RunRecord]:
        return self._store.list()

    def list_events(
        self,
        run_id: str,
        *,
        after_event_id: int = 0,
    ) -> list[RunEvent]:
        return self._store.list_events(
            run_id,
            after_event_id=after_event_id,
        )

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _execute(self, run_id: str, request: PipelineRequest) -> None:
        self._store.mark_running(run_id)
        try:
            result = self._pipeline_factory().run(
                request,
                reporter=lambda progress: self._store.append_progress(
                    run_id,
                    stage=progress.stage,
                    message=progress.message,
                    completed_steps=progress.completed_steps,
                    total_steps=progress.total_steps,
                    warning=progress.warning,
                ),
            )
        except Exception as exc:
            self._store.mark_failed(run_id, str(exc))
            return
        self._store.mark_completed(
            run_id,
            output_path=str(result.output_path),
            version=result.version,
            issue_count=result.issue_count,
        )
