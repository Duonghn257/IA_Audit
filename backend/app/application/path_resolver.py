"""Resolve user-supplied POC paths inside approved local boundaries."""
from __future__ import annotations

from pathlib import Path

from app.application.audit_pipeline import PipelineRequest
from app.core.settings import ApiSettings


class PathValidationError(ValueError):
    """Raised when a local path is invalid or outside an approved root."""


class LocalPathResolver:
    """Temporary POC adapter until browser upload replaces local paths."""

    def __init__(self, settings: ApiSettings) -> None:
        self._settings = settings

    def resolve_run_request(
        self,
        *,
        project_path: str,
        issues_path: str,
    ) -> PipelineRequest:
        project = self._resolve(project_path)
        issues = self._resolve(issues_path)

        self._ensure_inside(
            project,
            self._settings.data_root,
            label="project_path",
        )
        self._ensure_inside(
            issues,
            self._settings.repository_root,
            label="issues_path",
        )
        if not project.is_dir():
            raise PathValidationError(
                f"project_path is not a directory: {project_path}"
            )
        if not issues.is_file():
            raise PathValidationError(
                f"issues_path is not a file: {issues_path}"
            )
        return PipelineRequest(project_path=project, issues_path=issues)

    def _resolve(self, raw_path: str) -> Path:
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = self._settings.repository_root / path
        return path.resolve()

    @staticmethod
    def _ensure_inside(path: Path, root: Path, *, label: str) -> None:
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise PathValidationError(
                f"{label} must be inside {root}"
            ) from exc

