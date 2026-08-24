"""Typed API settings derived from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class ApiSettings:
    repository_root: Path
    backend_root: Path
    data_root: Path
    cors_origins: tuple[str, ...]
    run_workers: int
    database_url: str = "sqlite+pysqlite:///:memory:"
    storage_root: Path = Path(".runtime/projects")
    raw_retention_days: int = 7
    upload_max_files: int = 20
    upload_max_bytes: int = 100_000_000


def load_api_settings() -> ApiSettings:
    backend_root = Path(__file__).resolve().parents[2]
    repository_root = backend_root.parent
    load_dotenv(dotenv_path=backend_root / ".env", override=False)
    configured_data_root = os.environ.get("API_DATA_ROOT")
    data_root = (
        Path(configured_data_root).expanduser().resolve()
        if configured_data_root
        else (repository_root / "data").resolve()
    )
    raw_origins = os.environ.get(
        "API_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    cors_origins = tuple(
        origin.strip()
        for origin in raw_origins.split(",")
        if origin.strip()
    )
    run_workers = max(1, int(os.environ.get("API_RUN_WORKERS", "1")))
    database_url = os.environ.get(
        "DATABASE_URL",
        f"sqlite+pysqlite:///{backend_root / '.runtime' / 'audit.db'}",
    )
    configured_storage_root = os.environ.get("PROJECT_STORAGE_ROOT")
    storage_root = (
        Path(configured_storage_root).expanduser().resolve()
        if configured_storage_root
        else (backend_root / ".runtime" / "projects").resolve()
    )
    raw_retention_days = max(
        1,
        int(os.environ.get("RAW_UPLOAD_RETENTION_DAYS", "7")),
    )
    upload_max_files = max(
        1,
        int(os.environ.get("UPLOAD_MAX_FILES", "20")),
    )
    upload_max_bytes = max(
        1,
        int(
            os.environ.get(
                "UPLOAD_MAX_BYTES",
                str(100_000_000),
            )
        ),
    )
    return ApiSettings(
        repository_root=repository_root,
        backend_root=backend_root,
        data_root=data_root,
        cors_origins=cors_origins,
        run_workers=run_workers,
        database_url=database_url,
        storage_root=storage_root,
        raw_retention_days=raw_retention_days,
        upload_max_files=upload_max_files,
        upload_max_bytes=upload_max_bytes,
    )
