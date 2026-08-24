"""SQLAlchemy persistence for users and opaque browser sessions."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, delete, select
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship, sessionmaker

from app.domain.auth import AuthIdentity, AuthSessionRecord, AuthUser
from app.infrastructure.database import Base


class AuthUserModel(Base):
    __tablename__ = "auth_users"
    __table_args__ = (
        UniqueConstraint("provider", "provider_subject", name="uq_auth_user_provider_subject"),
    )

    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32))
    provider_subject: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(320), index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean)
    display_name: Mapped[str] = mapped_column(String(255))
    picture_url: Mapped[str | None] = mapped_column(String(2048))
    hosted_domain: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sessions: Mapped[list["AuthSessionModel"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class AuthSessionModel(Base):
    __tablename__ = "auth_sessions"

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("auth_users.user_id", ondelete="CASCADE"),
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_token: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    user: Mapped[AuthUserModel] = relationship(back_populates="sessions")


class SqlAlchemyAuthRepository:
    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def upsert_user(self, identity: AuthIdentity) -> AuthUser:
        now = datetime.now(timezone.utc)
        with self._sessions.begin() as session:
            model = session.scalar(
                select(AuthUserModel).where(
                    AuthUserModel.provider == identity.provider,
                    AuthUserModel.provider_subject == identity.provider_subject,
                )
            )
            if model is None:
                model = AuthUserModel(
                    user_id=str(uuid4()),
                    provider=identity.provider,
                    provider_subject=identity.provider_subject,
                    email=identity.email,
                    email_verified=identity.email_verified,
                    display_name=identity.display_name,
                    picture_url=identity.picture_url,
                    hosted_domain=identity.hosted_domain,
                    created_at=now,
                    last_login_at=now,
                )
                session.add(model)
            else:
                model.email = identity.email
                model.email_verified = identity.email_verified
                model.display_name = identity.display_name
                model.picture_url = identity.picture_url
                model.hosted_domain = identity.hosted_domain
                model.last_login_at = now
            session.flush()
            return _to_user(model)

    def create_session(
        self,
        *,
        session_id: str,
        user_id: str,
        token_hash: str,
        csrf_token: str,
        expires_at: datetime,
    ) -> AuthSessionRecord:
        now = datetime.now(timezone.utc)
        with self._sessions.begin() as session:
            user = session.get(AuthUserModel, user_id)
            if user is None:
                raise LookupError(f"Auth user not found: {user_id}")
            model = AuthSessionModel(
                session_id=session_id,
                user_id=user_id,
                token_hash=token_hash,
                csrf_token=csrf_token,
                created_at=now,
                expires_at=expires_at,
                last_seen_at=now,
            )
            model.user = user
            session.add(model)
            session.flush()
            return _to_session(model)

    def get_active_session(
        self,
        token_hash: str,
        *,
        now: datetime,
    ) -> AuthSessionRecord | None:
        with self._sessions.begin() as session:
            model = session.scalar(
                select(AuthSessionModel).where(
                    AuthSessionModel.token_hash == token_hash,
                    AuthSessionModel.revoked_at.is_(None),
                    AuthSessionModel.expires_at > now,
                )
            )
            if model is None:
                return None
            model.last_seen_at = now
            session.flush()
            return _to_session(model)

    def revoke_session(self, token_hash: str, *, now: datetime) -> None:
        with self._sessions.begin() as session:
            model = session.scalar(
                select(AuthSessionModel).where(
                    AuthSessionModel.token_hash == token_hash,
                    AuthSessionModel.revoked_at.is_(None),
                )
            )
            if model is not None:
                model.revoked_at = now

    def delete_expired_sessions(self, *, now: datetime) -> int:
        with self._sessions.begin() as session:
            result = session.execute(
                delete(AuthSessionModel).where(AuthSessionModel.expires_at <= now)
            )
            return int(result.rowcount or 0)


def _to_user(model: AuthUserModel) -> AuthUser:
    return AuthUser(
        user_id=model.user_id,
        provider=model.provider,
        provider_subject=model.provider_subject,
        email=model.email,
        email_verified=model.email_verified,
        display_name=model.display_name,
        picture_url=model.picture_url,
        hosted_domain=model.hosted_domain,
        created_at=_as_utc(model.created_at),
        last_login_at=_as_utc(model.last_login_at),
    )


def _to_session(model: AuthSessionModel) -> AuthSessionRecord:
    return AuthSessionRecord(
        session_id=model.session_id,
        user=_to_user(model.user),
        csrf_token=model.csrf_token,
        created_at=_as_utc(model.created_at),
        expires_at=_as_utc(model.expires_at),
        last_seen_at=_as_utc(model.last_seen_at),
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
