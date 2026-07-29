"""Thread-safe in-memory run store for the POC API."""
from __future__ import annotations

import copy
import threading
import uuid
from datetime import datetime, timezone

from app.domain.runs import (
    RunEvent,
    RunNotFoundError,
    RunRecord,
    RunStatus,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class InMemoryRunStore:
    """POC store; replace with PostgreSQL without changing API use cases."""

    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._lock = threading.RLock()

    def create(self, project_path: str, issues_path: str) -> RunRecord:
        with self._lock:
            timestamp = _now()
            record = RunRecord(
                run_id=str(uuid.uuid4()),
                project_path=project_path,
                issues_path=issues_path,
                status=RunStatus.QUEUED,
                created_at=timestamp,
                updated_at=timestamp,
            )
            self._runs[record.run_id] = record
            return copy.deepcopy(record)

    def mark_running(self, run_id: str) -> RunRecord:
        with self._lock:
            record = self._require(run_id)
            timestamp = _now()
            record.status = RunStatus.RUNNING
            record.started_at = timestamp
            record.updated_at = timestamp
            return copy.deepcopy(record)

    def append_progress(
        self,
        run_id: str,
        *,
        stage: str,
        message: str,
        completed_steps: int,
        total_steps: int,
        warning: bool,
    ) -> RunEvent:
        with self._lock:
            record = self._require(run_id)
            event = RunEvent(
                event_id=len(record.events) + 1,
                stage=stage,
                message=message,
                completed_steps=completed_steps,
                total_steps=total_steps,
                warning=warning,
                occurred_at=_now(),
            )
            record.events.append(event)
            record.updated_at = event.occurred_at
            return copy.deepcopy(event)

    def mark_completed(
        self,
        run_id: str,
        *,
        output_path: str,
        version: str,
        issue_count: int,
    ) -> RunRecord:
        with self._lock:
            record = self._require(run_id)
            timestamp = _now()
            record.status = RunStatus.COMPLETED
            record.completed_at = timestamp
            record.updated_at = timestamp
            record.output_path = output_path
            record.version = version
            record.issue_count = issue_count
            return copy.deepcopy(record)

    def mark_failed(self, run_id: str, error: str) -> RunRecord:
        with self._lock:
            record = self._require(run_id)
            timestamp = _now()
            record.status = RunStatus.FAILED
            record.completed_at = timestamp
            record.updated_at = timestamp
            record.error = error
            return copy.deepcopy(record)

    def get(self, run_id: str) -> RunRecord:
        with self._lock:
            return copy.deepcopy(self._require(run_id))

    def list(self) -> list[RunRecord]:
        with self._lock:
            records = sorted(
                self._runs.values(),
                key=lambda item: item.created_at,
                reverse=True,
            )
            return copy.deepcopy(records)

    def list_events(
        self,
        run_id: str,
        *,
        after_event_id: int = 0,
    ) -> list[RunEvent]:
        with self._lock:
            record = self._require(run_id)
            return copy.deepcopy(
                [
                    event
                    for event in record.events
                    if event.event_id > after_event_id
                ]
            )

    def _require(self, run_id: str) -> RunRecord:
        try:
            return self._runs[run_id]
        except KeyError as exc:
            raise RunNotFoundError(run_id) from exc
