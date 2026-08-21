"""SQLAlchemy implementation of persistent project metadata."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import select
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship
from sqlalchemy.orm import sessionmaker

from app.domain.projects import (
    ProjectEvent,
    ProjectNotFoundError,
    ProjectRecord,
    ProjectStatus,
    ProjectTransitionError,
)
from app.infrastructure.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ProjectModel(Base):
    __tablename__ = "projects"
    __table_args__ = (
        Index("uq_projects_name", "name", unique=True),
    )

    project_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(
        String(32),
        default="FILE_UPLOAD",
    )
    status: Mapped[str] = mapped_column(String(32), index=True)
    current_activity: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    storage_path: Mapped[str | None] = mapped_column(Text)
    output_path: Mapped[str | None] = mapped_column(Text)
    version: Mapped[str | None] = mapped_column(String(32))
    issue_count: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    raw_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )
    raw_deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    events: Mapped[list["ProjectEventModel"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ProjectEventModel(Base):
    __tablename__ = "project_events"

    event_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        index=True,
    )
    stage: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(Text)
    completed_steps: Mapped[int] = mapped_column(Integer)
    total_steps: Mapped[int] = mapped_column(Integer)
    warning: Mapped[bool] = mapped_column(Boolean, default=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    project: Mapped[ProjectModel] = relationship(back_populates="events")


class SqlAlchemyProjectRepository:
    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def create(
        self,
        *,
        project_id: str,
        name: str,
        raw_expires_at: datetime,
    ) -> ProjectRecord:
        now = _utcnow()
        model = ProjectModel(
            project_id=project_id,
            name=name,
            source_type="FILE_UPLOAD",
            status=ProjectStatus.UPLOADING.value,
            current_activity="Receiving project folder...",
            created_at=now,
            updated_at=now,
            raw_expires_at=raw_expires_at,
        )
        with self._sessions.begin() as session:
            session.add(model)
        return _to_record(model)

    def set_upload_saved(
        self,
        project_id: str,
        *,
        storage_path: str,
    ) -> ProjectRecord:
        with self._sessions.begin() as session:
            model = _get_model(session, project_id)
            _require_status(model, ProjectStatus.UPLOADING)
            model.storage_path = storage_path
            model.current_activity = "Project folder uploaded"
            model.updated_at = _utcnow()
        return _to_record(model)

    def mark_processing(self, project_id: str) -> ProjectRecord:
        with self._sessions.begin() as session:
            model = _get_model(session, project_id)
            _require_status(model, ProjectStatus.UPLOADING)
            now = _utcnow()
            model.status = ProjectStatus.PROCESSING.value
            model.current_activity = "Queued for processing..."
            model.started_at = now
            model.updated_at = now
        return _to_record(model)

    def append_progress(
        self,
        project_id: str,
        *,
        stage: str,
        message: str,
        completed_steps: int,
        total_steps: int,
        warning: bool,
    ) -> ProjectEvent:
        with self._sessions.begin() as session:
            project = _get_model(session, project_id)
            occurred_at = _utcnow()
            event = ProjectEventModel(
                project_id=project_id,
                stage=stage,
                message=message,
                completed_steps=completed_steps,
                total_steps=total_steps,
                warning=warning,
                occurred_at=occurred_at,
            )
            project.current_activity = message
            project.updated_at = occurred_at
            session.add(event)
            session.flush()
        return _to_event(event)

    def mark_completed(
        self,
        project_id: str,
        *,
        output_path: str,
        version: str,
        issue_count: int,
    ) -> ProjectRecord:
        with self._sessions.begin() as session:
            model = _get_model(session, project_id)
            _require_status(model, ProjectStatus.PROCESSING)
            now = _utcnow()
            model.status = ProjectStatus.COMPLETED.value
            model.current_activity = "DOCX ready to download"
            model.output_path = output_path
            model.version = version
            model.issue_count = issue_count
            model.completed_at = now
            model.updated_at = now
        return _to_record(model)

    def mark_failed(self, project_id: str, error: str) -> ProjectRecord:
        with self._sessions.begin() as session:
            model = _get_model(session, project_id)
            if ProjectStatus(model.status).is_terminal:
                raise ProjectTransitionError(
                    f"Project {project_id} is already terminal"
                )
            now = _utcnow()
            model.status = ProjectStatus.FAILED.value
            model.current_activity = "Processing failed"
            model.error = error
            model.completed_at = now
            model.updated_at = now
        return _to_record(model)

    def get(self, project_id: str) -> ProjectRecord:
        with self._sessions() as session:
            return _to_record(_get_model(session, project_id))

    def list(self) -> list[ProjectRecord]:
        with self._sessions() as session:
            models = session.scalars(
                select(ProjectModel).order_by(ProjectModel.created_at.desc())
            ).all()
            return [_to_record(model) for model in models]

    def list_events(
        self,
        project_id: str,
        *,
        after_event_id: int = 0,
    ) -> list[ProjectEvent]:
        with self._sessions() as session:
            _get_model(session, project_id)
            models = session.scalars(
                select(ProjectEventModel)
                .where(
                    ProjectEventModel.project_id == project_id,
                    ProjectEventModel.event_id > after_event_id,
                )
                .order_by(ProjectEventModel.event_id)
            ).all()
            return [_to_event(model) for model in models]

    def list_expired_raw(self, now: datetime) -> list[ProjectRecord]:
        with self._sessions() as session:
            models = session.scalars(
                select(ProjectModel).where(
                    ProjectModel.raw_deleted_at.is_(None),
                    ProjectModel.raw_expires_at.is_not(None),
                    ProjectModel.raw_expires_at <= now,
                    ProjectModel.status.in_(
                        [
                            ProjectStatus.COMPLETED.value,
                            ProjectStatus.FAILED.value,
                        ]
                    ),
                )
            ).all()
            return [_to_record(model) for model in models]

    def mark_raw_deleted(
        self,
        project_id: str,
        deleted_at: datetime,
    ) -> ProjectRecord:
        with self._sessions.begin() as session:
            model = _get_model(session, project_id)
            model.raw_deleted_at = deleted_at
            model.storage_path = None
            model.updated_at = deleted_at
        return _to_record(model)


def _get_model(session: Session, project_id: str) -> ProjectModel:
    model = session.get(ProjectModel, project_id)
    if model is None:
        raise ProjectNotFoundError(project_id)
    return model


def _require_status(
    model: ProjectModel,
    expected: ProjectStatus,
) -> None:
    if model.status != expected.value:
        raise ProjectTransitionError(
            f"Project {model.project_id} is {model.status}, "
            f"expected {expected.value}"
        )


def _to_record(model: ProjectModel) -> ProjectRecord:
    return ProjectRecord(
        project_id=model.project_id,
        name=model.name,
        source_type=model.source_type,
        status=ProjectStatus(model.status),
        current_activity=model.current_activity,
        created_at=_as_utc(model.created_at),
        updated_at=_as_utc(model.updated_at),
        started_at=_as_utc(model.started_at),
        completed_at=_as_utc(model.completed_at),
        storage_path=model.storage_path,
        output_path=model.output_path,
        version=model.version,
        issue_count=model.issue_count,
        error=model.error,
        raw_expires_at=_as_utc(model.raw_expires_at),
        raw_deleted_at=_as_utc(model.raw_deleted_at),
    )


def _to_event(model: ProjectEventModel) -> ProjectEvent:
    return ProjectEvent(
        event_id=model.event_id,
        project_id=model.project_id,
        stage=model.stage,
        message=model.message,
        completed_steps=model.completed_steps,
        total_steps=model.total_steps,
        warning=model.warning,
        occurred_at=_as_utc(model.occurred_at),
    )


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
