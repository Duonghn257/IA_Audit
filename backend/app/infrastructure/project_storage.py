"""Local filesystem project storage adapter for the POC."""
from __future__ import annotations

import shutil
from pathlib import Path, PurePosixPath
from typing import Sequence

from app.application.project_files import (
    IncomingProjectFile,
    ProjectUploadError,
    StoredProjectInput,
)

_CHUNK_SIZE = 1024 * 1024


class LocalProjectStorage:
    def __init__(
        self,
        root: Path,
        *,
        max_files: int,
        max_total_bytes: int,
    ) -> None:
        self._root = root.expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._max_files = max_files
        self._max_total_bytes = max_total_bytes

    def save_uploads(
        self,
        project_id: str,
        files: Sequence[IncomingProjectFile],
    ) -> StoredProjectInput:
        if not files:
            raise ProjectUploadError("The uploaded folder is empty.")
        if len(files) > self._max_files:
            raise ProjectUploadError(
                f"Folder contains more than {self._max_files} files."
            )

        normalized = [
            (_safe_parts(item.relative_path), item.stream)
            for item in files
        ]
        normalized = _strip_common_folder(normalized)
        input_root = self._project_root(project_id) / "input"
        if input_root.exists():
            raise ProjectUploadError(
                f"Upload already exists for project {project_id}."
            )
        input_root.mkdir(parents=True)

        total_bytes = 0
        try:
            for parts, stream in normalized:
                destination = input_root.joinpath(*parts).resolve()
                if input_root not in destination.parents:
                    raise ProjectUploadError("Unsafe upload path.")
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("wb") as target:
                    while chunk := stream.read(_CHUNK_SIZE):
                        total_bytes += len(chunk)
                        if total_bytes > self._max_total_bytes:
                            raise ProjectUploadError(
                                "Folder exceeds the configured upload size "
                                "limit."
                            )
                        target.write(chunk)
        except Exception:
            shutil.rmtree(input_root, ignore_errors=True)
            raise

        return StoredProjectInput(
            project_path=input_root,
            file_count=len(files),
            total_bytes=total_bytes,
        )

    def promote_output(self, project_id: str, source: Path) -> Path:
        source = source.resolve()
        input_root = (self._project_root(project_id) / "input").resolve()
        if input_root not in source.parents or not source.is_file():
            raise ProjectUploadError(
                "Generated output is outside the project input directory."
            )
        output_root = self._project_root(project_id) / "output"
        output_root.mkdir(parents=True, exist_ok=True)
        destination = output_root / source.name
        shutil.copy2(source, destination)
        return destination.resolve()

    def delete_raw_input(self, project_id: str) -> None:
        input_root = self._project_root(project_id) / "input"
        shutil.rmtree(input_root, ignore_errors=True)

    def _project_root(self, project_id: str) -> Path:
        project_root = (self._root / project_id).resolve()
        if project_root.parent != self._root:
            raise ProjectUploadError("Invalid project identifier.")
        return project_root


def _safe_parts(raw_path: str) -> tuple[str, ...]:
    normalized = raw_path.replace("\\", "/").strip()
    path = PurePosixPath(normalized)
    if (
        not normalized
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ProjectUploadError(f"Unsafe relative path: {raw_path!r}")
    return path.parts


def _strip_common_folder(
    files: list[tuple[tuple[str, ...], object]],
) -> list[tuple[tuple[str, ...], object]]:
    first_parts = {parts[0] for parts, _ in files}
    if len(first_parts) == 1 and all(len(parts) > 1 for parts, _ in files):
        return [(parts[1:], stream) for parts, stream in files]
    return files

