"""Authentication domain records shared across providers and sessions."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AuthIdentity:
    provider: str
    provider_subject: str
    email: str
    email_verified: bool
    display_name: str
    picture_url: str | None = None
    hosted_domain: str | None = None


@dataclass(frozen=True)
class AuthUser:
    user_id: str
    provider: str
    provider_subject: str
    email: str
    email_verified: bool
    display_name: str
    picture_url: str | None
    hosted_domain: str | None
    created_at: datetime
    last_login_at: datetime


@dataclass(frozen=True)
class AuthSessionRecord:
    session_id: str
    user: AuthUser
    csrf_token: str
    created_at: datetime
    expires_at: datetime
    last_seen_at: datetime
