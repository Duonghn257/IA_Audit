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
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str | None = None
    google_allowed_domains: tuple[str, ...] = ()
    auth_post_login_redirect: str = "/tests-ui/"
    auth_session_ttl_hours: int = 12
    auth_cookie_name: str = "audit_session"
    auth_cookie_secure: bool = False

    @property
    def google_auth_enabled(self) -> bool:
        return bool(
            self.google_client_id
            and self.google_client_secret
            and self.google_redirect_uri
        )


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
    google_client_id = os.environ.get("GOOGLE_CLIENT_ID") or None
    google_client_secret = os.environ.get("GOOGLE_CLIENT_SECRET") or None
    google_redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI") or None
    google_values = (
        google_client_id,
        google_client_secret,
        google_redirect_uri,
    )
    if any(google_values) and not all(google_values):
        raise RuntimeError(
            "GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET and "
            "GOOGLE_REDIRECT_URI must be configured together."
        )
    google_allowed_domains = tuple(
        value.strip().lower()
        for value in os.environ.get("GOOGLE_ALLOWED_DOMAINS", "").split(",")
        if value.strip()
    )
    auth_post_login_redirect = os.environ.get(
        "AUTH_POST_LOGIN_REDIRECT",
        "/tests-ui/",
    )
    auth_session_ttl_hours = max(
        1,
        int(os.environ.get("AUTH_SESSION_TTL_HOURS", "12")),
    )
    auth_cookie_name = os.environ.get(
        "AUTH_COOKIE_NAME",
        "audit_session",
    ).strip() or "audit_session"
    secure_default = bool(
        google_redirect_uri and google_redirect_uri.startswith("https://")
    )
    auth_cookie_secure = os.environ.get(
        "AUTH_COOKIE_SECURE",
        "true" if secure_default else "false",
    ).strip().lower() in {"1", "true", "yes", "on"}
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
        google_client_id=google_client_id,
        google_client_secret=google_client_secret,
        google_redirect_uri=google_redirect_uri,
        google_allowed_domains=google_allowed_domains,
        auth_post_login_redirect=auth_post_login_redirect,
        auth_session_ttl_hours=auth_session_ttl_hours,
        auth_cookie_name=auth_cookie_name,
        auth_cookie_secure=auth_cookie_secure,
    )
