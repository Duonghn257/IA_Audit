"""Domain models for asynchronous audit runs."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class RunNotFoundError(KeyError):
    """Raised when a run identifier does not exist."""


class RunStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    @property
    def is_terminal(self) -> bool:
        return self in {RunStatus.COMPLETED, RunStatus.FAILED}


@dataclass(frozen=True)
class RunEvent:
    event_id: int
    stage: str
    message: str
    completed_steps: int
    total_steps: int
    warning: bool
    occurred_at: datetime


@dataclass
class RunRecord:
    run_id: str
    project_path: str
    issues_path: str
    status: RunStatus
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    output_path: str | None = None
    version: str | None = None
    issue_count: int | None = None
    error: str | None = None
    events: list[RunEvent] = field(default_factory=list)
