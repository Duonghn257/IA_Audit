"""SQLAlchemy ORM models for the UAT audit workspace."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base


class UploadSessionModel(Base):
    __tablename__ = "upload_sessions"
    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    state: Mapped[str] = mapped_column(String(32), index=True)
    validation_report: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    actor_id: Mapped[str] = mapped_column(String(255))
    actor_label: Mapped[str] = mapped_column(String(255))
    actor_type: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    files: Mapped[list[UploadFileModel]] = relationship(back_populates="session", cascade="all, delete-orphan")


class UploadFileModel(Base):
    __tablename__ = "upload_files"
    __table_args__ = (UniqueConstraint("session_id", "relative_path"),)
    file_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("upload_sessions.session_id", ondelete="CASCADE"), index=True)
    relative_path: Mapped[str] = mapped_column(String(1024))
    size_bytes: Mapped[int] = mapped_column(Integer)
    content_type: Mapped[str | None] = mapped_column(String(255))
    staging_object_key: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String(128), index=True)
    logical_role: Mapped[str | None] = mapped_column(String(32))
    upload_status: Mapped[str] = mapped_column(String(32), default="PENDING")
    readability_status: Mapped[str | None] = mapped_column(String(32))
    validation_message: Mapped[str | None] = mapped_column(Text)
    modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    session: Mapped[UploadSessionModel] = relationship(back_populates="files")


class SourceSnapshotModel(Base):
    __tablename__ = "source_snapshots"
    __table_args__ = (UniqueConstraint("project_id"),)
    snapshot_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id", ondelete="CASCADE"), index=True)
    manifest_hash: Mapped[str] = mapped_column(String(128))
    manifest: Mapped[dict[str, Any]] = mapped_column(JSON)
    source_object_prefix: Mapped[str] = mapped_column(Text)
    promoted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    documents: Mapped[list[SourceDocumentModel]] = relationship(back_populates="snapshot", cascade="all, delete-orphan")


class SourceDocumentModel(Base):
    __tablename__ = "source_documents"
    __table_args__ = (UniqueConstraint("snapshot_id", "relative_path"),)
    document_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("source_snapshots.snapshot_id", ondelete="CASCADE"), index=True)
    relative_path: Mapped[str] = mapped_column(String(1024))
    logical_role: Mapped[str] = mapped_column(String(32))
    original_object_key: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(128), index=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    content_type: Mapped[str | None] = mapped_column(String(255))
    upload_status: Mapped[str] = mapped_column(String(32))
    parse_status: Mapped[str] = mapped_column(String(32), default="PENDING")
    parser_version: Mapped[str | None] = mapped_column(String(64))
    derived_object_key: Mapped[str | None] = mapped_column(Text)
    snapshot: Mapped[SourceSnapshotModel] = relationship(back_populates="documents")


class ProjectVersionModel(Base):
    __tablename__ = "project_versions"
    __table_args__ = (UniqueConstraint("project_id", "sequence_no"),)
    version_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id", ondelete="CASCADE"), index=True)
    sequence_no: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String(32))
    base_version_id: Mapped[str | None] = mapped_column(ForeignKey("project_versions.version_id"), index=True)
    state: Mapped[str] = mapped_column(String(32), index=True)
    issue_revision: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    issues: Mapped[list[IssueModel]] = relationship(back_populates="version", cascade="all, delete-orphan", foreign_keys="IssueModel.project_version_id")


class IssueModel(Base):
    __tablename__ = "issues"
    issue_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_version_id: Mapped[str] = mapped_column(ForeignKey("project_versions.version_id", ondelete="CASCADE"), index=True)
    origin: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), index=True)
    title_hint: Mapped[str | None] = mapped_column(String(500))
    observed_gap: Mapped[str] = mapped_column(Text)
    evidence_summary: Mapped[str | None] = mapped_column(Text)
    evidence_refs: Mapped[list[str]] = mapped_column(JSON, default=list)
    sop_refs: Mapped[list[str]] = mapped_column(JSON, default=list)
    risk_category: Mapped[str | None] = mapped_column(String(128))
    confidence: Mapped[float | None] = mapped_column(Float)
    validation_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    row_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    version: Mapped[ProjectVersionModel] = relationship(back_populates="issues")
    source_refs: Mapped[list[IssueSourceRefModel]] = relationship(back_populates="issue", cascade="all, delete-orphan")


class IssueSourceRefModel(Base):
    __tablename__ = "issue_source_refs"
    reference_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    issue_id: Mapped[str] = mapped_column(ForeignKey("issues.issue_id", ondelete="CASCADE"), index=True)
    ref_kind: Mapped[str] = mapped_column(String(32))
    document_id: Mapped[str] = mapped_column(ForeignKey("source_documents.document_id"), index=True)
    unit_id: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[dict[str, Any]] = mapped_column(JSON)
    quote: Mapped[str | None] = mapped_column(Text)
    issue: Mapped[IssueModel] = relationship(back_populates="source_refs")


class JobModel(Base):
    __tablename__ = "jobs"
    job_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id", ondelete="CASCADE"), index=True)
    project_version_id: Mapped[str] = mapped_column(ForeignKey("project_versions.version_id", ondelete="CASCADE"), index=True)
    job_type: Mapped[str] = mapped_column(String(32), index=True)
    state: Mapped[str] = mapped_column(String(32), index=True)
    stage: Mapped[str | None] = mapped_column(String(64))
    input_hash: Mapped[str] = mapped_column(String(128), index=True)
    completed_items: Mapped[int] = mapped_column(Integer, default=0)
    total_items: Mapped[int | None] = mapped_column(Integer)
    current_message: Mapped[str | None] = mapped_column(Text)
    checkpoint: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    correlation_id: Mapped[str] = mapped_column(String(64), index=True)
    lease_owner: Mapped[str | None] = mapped_column(String(255))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
    input_snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("audit_input_snapshots.snapshot_id"), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    events: Mapped[list[JobEventModel]] = relationship(back_populates="job", cascade="all, delete-orphan")


class JobEventModel(Base):
    __tablename__ = "job_events"
    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.job_id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(Text)
    completed_items: Mapped[int] = mapped_column(Integer)
    total_items: Mapped[int | None] = mapped_column(Integer)
    warning: Mapped[bool] = mapped_column(Boolean, default=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    job: Mapped[JobModel] = relationship(back_populates="events")


class AuditInputSnapshotModel(Base):
    __tablename__ = "audit_input_snapshots"
    snapshot_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_version_id: Mapped[str] = mapped_column(ForeignKey("project_versions.version_id", ondelete="CASCADE"), index=True)
    issue_revision: Mapped[int] = mapped_column(Integer)
    input_hash: Mapped[str] = mapped_column(String(128), index=True)
    issue_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    central_asset_versions: Mapped[dict[str, Any]] = mapped_column(JSON)
    run_manifest_object_key: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OutputRevisionModel(Base):
    __tablename__ = "output_revisions"
    __table_args__ = (UniqueConstraint("project_version_id", "ordinal"),)
    output_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_version_id: Mapped[str] = mapped_column(ForeignKey("project_versions.version_id", ondelete="CASCADE"), index=True)
    audit_input_snapshot_id: Mapped[str] = mapped_column(ForeignKey("audit_input_snapshots.snapshot_id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), index=True)
    filename: Mapped[str] = mapped_column(String(512))
    object_key: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(128))
    run_manifest_object_key: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
