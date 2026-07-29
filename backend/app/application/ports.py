"""Application ports implemented by infrastructure adapters."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Protocol, Sequence

from app.application.project_files import (
    IncomingProjectFile,
    StoredProjectInput,
)
from app.domain.projects import ProjectEvent, ProjectRecord
from app.domain.runs import RunEvent, RunRecord


class RunStore(Protocol):
    def create(self, project_path: str, issues_path: str) -> RunRecord: ...

    def mark_running(self, run_id: str) -> RunRecord: ...

    def append_progress(
        self,
        run_id: str,
        *,
        stage: str,
        message: str,
        completed_steps: int,
        total_steps: int,
        warning: bool,
    ) -> RunEvent: ...

    def mark_completed(
        self,
        run_id: str,
        *,
        output_path: str,
        version: str,
        issue_count: int,
    ) -> RunRecord: ...

    def mark_failed(self, run_id: str, error: str) -> RunRecord: ...

    def get(self, run_id: str) -> RunRecord: ...

    def list(self) -> list[RunRecord]: ...

    def list_events(
        self,
        run_id: str,
        *,
        after_event_id: int = 0,
    ) -> list[RunEvent]: ...


class ProjectRepository(Protocol):
    def create(
        self,
        *,
        project_id: str,
        name: str,
        raw_expires_at: datetime,
    ) -> ProjectRecord: ...

    def set_upload_saved(
        self,
        project_id: str,
        *,
        storage_path: str,
    ) -> ProjectRecord: ...

    def mark_processing(self, project_id: str) -> ProjectRecord: ...

    def append_progress(
        self,
        project_id: str,
        *,
        stage: str,
        message: str,
        completed_steps: int,
        total_steps: int,
        warning: bool,
    ) -> ProjectEvent: ...

    def mark_completed(
        self,
        project_id: str,
        *,
        output_path: str,
        version: str,
        issue_count: int,
    ) -> ProjectRecord: ...

    def mark_failed(self, project_id: str, error: str) -> ProjectRecord: ...

    def get(self, project_id: str) -> ProjectRecord: ...

    def list(self) -> list[ProjectRecord]: ...

    def list_events(
        self,
        project_id: str,
        *,
        after_event_id: int = 0,
    ) -> list[ProjectEvent]: ...

    def list_expired_raw(self, now: datetime) -> list[ProjectRecord]: ...

    def mark_raw_deleted(
        self,
        project_id: str,
        deleted_at: datetime,
    ) -> ProjectRecord: ...


class ProjectStorage(Protocol):
    def save_uploads(
        self,
        project_id: str,
        files: Sequence[IncomingProjectFile],
    ) -> StoredProjectInput: ...

    def promote_output(self, project_id: str, source: Path) -> Path: ...

    def delete_raw_input(self, project_id: str) -> None: ...
