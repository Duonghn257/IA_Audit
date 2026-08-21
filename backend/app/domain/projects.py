"""Domain models for uploaded audit projects."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ProjectNotFoundError(KeyError):
    """Raised when a project identifier does not exist."""


class ProjectTransitionError(RuntimeError):
    """Raised when an invalid project status transition is attempted."""


class ProjectStatus(StrEnum):
    UPLOADING = "UPLOADING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    READY_FOR_DISCOVERY = "READY_FOR_DISCOVERY"
    CANDIDATES_AVAILABLE = "CANDIDATES_AVAILABLE"
    OUTPUT_AVAILABLE = "OUTPUT_AVAILABLE"

    @property
    def is_terminal(self) -> bool:
        return self in {ProjectStatus.COMPLETED, ProjectStatus.FAILED}


@dataclass(frozen=True)
class ProjectEvent:
    event_id: int
    project_id: str
    stage: str
    message: str
    completed_steps: int
    total_steps: int
    warning: bool
    occurred_at: datetime


@dataclass(frozen=True)
class ProjectRecord:
    project_id: str
    name: str
    source_type: str
    status: ProjectStatus
    current_activity: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    storage_path: str | None = None
    output_path: str | None = None
    version: str | None = None
    issue_count: int | None = None
    error: str | None = None
    raw_expires_at: datetime | None = None
    raw_deleted_at: datetime | None = None
