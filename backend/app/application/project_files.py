"""Transport-neutral file types used by project upload workflows."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO


class ProjectUploadError(ValueError):
    """Raised when an uploaded project folder is invalid."""


@dataclass(frozen=True)
class IncomingProjectFile:
    relative_path: str
    stream: BinaryIO


@dataclass(frozen=True)
class StoredProjectInput:
    project_path: Path
    file_count: int
    total_bytes: int

