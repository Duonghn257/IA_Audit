"""Provider-neutral user and server-side session lifecycle."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Protocol
from uuid import uuid4

from app.domain.auth import AuthIdentity, AuthSessionRecord, AuthUser


class AuthRepository(Protocol):
    def upsert_user(self, identity: AuthIdentity) -> AuthUser: ...

    def create_session(
        self,
        *,
        session_id: str,
        user_id: str,
        token_hash: str,
        csrf_token: str,
        expires_at: datetime,
    ) -> AuthSessionRecord: ...

    def get_active_session(
        self,
        token_hash: str,
        *,
        now: datetime,
    ) -> AuthSessionRecord | None: ...

    def revoke_session(self, token_hash: str, *, now: datetime) -> None: ...

    def delete_expired_sessions(self, *, now: datetime) -> int: ...


class AuthService:
    def __init__(
        self,
        repository: AuthRepository,
        *,
        session_ttl_hours: int = 12,
    ) -> None:
        self._repository = repository
        self._session_ttl = timedelta(hours=session_ttl_hours)

    def sign_in(self, identity: AuthIdentity) -> tuple[AuthSessionRecord, str]:
        now = datetime.now(timezone.utc)
        self._repository.delete_expired_sessions(now=now)
        user = self._repository.upsert_user(identity)
        raw_token = secrets.token_urlsafe(48)
        session = self._repository.create_session(
            session_id=str(uuid4()),
            user_id=user.user_id,
            token_hash=self._hash_token(raw_token),
            csrf_token=secrets.token_urlsafe(32),
            expires_at=now + self._session_ttl,
        )
        return session, raw_token

    def authenticate(self, raw_token: str | None) -> AuthSessionRecord | None:
        if not raw_token:
            return None
        return self._repository.get_active_session(
            self._hash_token(raw_token),
            now=datetime.now(timezone.utc),
        )

    def sign_out(self, raw_token: str | None) -> None:
        if not raw_token:
            return
        self._repository.revoke_session(
            self._hash_token(raw_token),
            now=datetime.now(timezone.utc),
        )

    @staticmethod
    def _hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
