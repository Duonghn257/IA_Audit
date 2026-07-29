"""Output version directory scanner."""
from __future__ import annotations

import re
from pathlib import Path

_VERSION_RE = re.compile(r"^v0\.(\d+)$")


def next_version(project_path: Path) -> tuple[str, Path]:
    """Return (version_name, run_dir) for a new run.

    Scans `<project>/Output/` for existing `v0.N/` directories, picks N+1,
    and creates the new directory. Never overwrites an existing version.
    Non-directory files at the Output root (e.g., legacy `.docx` drafts from
    older runs) are ignored.
    """
    output_root = project_path / "Output"
    output_root.mkdir(exist_ok=True)
    existing = [
        int(m.group(1))
        for d in output_root.iterdir()
        if d.is_dir() and (m := _VERSION_RE.match(d.name))
    ]
    n = (max(existing) + 1) if existing else 1
    version = f"v0.{n}"
    run_dir = output_root / version
    run_dir.mkdir()
    return version, run_dir
