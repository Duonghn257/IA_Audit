"""Add UAT audit workspace persistence.

Revision ID: 20260812_02
Revises: 20260729_01
Create Date: 2026-08-12
"""
from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260812_02"
down_revision: str | None = "20260729_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("uq_projects_name", "projects", ["name"], unique=True)

    op.create_table(
        "upload_sessions",
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("validation_report", sa.JSON(), nullable=True),
        sa.Column("actor_id", sa.String(length=255), nullable=False),
        sa.Column("actor_label", sa.String(length=255), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_index("ix_upload_sessions_state", "upload_sessions", ["state"])
    op.create_index(
        "ix_upload_sessions_expires_at", "upload_sessions", ["expires_at"]
    )
    op.create_table(
        "upload_files",
        sa.Column("file_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("relative_path", sa.String(length=1024), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("staging_object_key", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("logical_role", sa.String(length=32), nullable=True),
        sa.Column("upload_status", sa.String(length=32), nullable=False),
        sa.Column("readability_status", sa.String(length=32), nullable=True),
        sa.Column("validation_message", sa.Text(), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["session_id"], ["upload_sessions.session_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("file_id"),
        sa.UniqueConstraint("session_id", "relative_path"),
    )
    op.create_index("ix_upload_files_session_id", "upload_files", ["session_id"])
    op.create_index("ix_upload_files_content_hash", "upload_files", ["content_hash"])

    op.create_table(
        "source_snapshots",
        sa.Column("snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("manifest_hash", sa.String(length=128), nullable=False),
        sa.Column("manifest", sa.JSON(), nullable=False),
        sa.Column("source_object_prefix", sa.Text(), nullable=False),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.project_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("snapshot_id"),
        sa.UniqueConstraint("project_id"),
    )
    op.create_index(
        "ix_source_snapshots_project_id", "source_snapshots", ["project_id"]
    )
    op.create_table(
        "source_documents",
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("relative_path", sa.String(length=1024), nullable=False),
        sa.Column("logical_role", sa.String(length=32), nullable=False),
        sa.Column("original_object_key", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("upload_status", sa.String(length=32), nullable=False),
        sa.Column("parse_status", sa.String(length=32), nullable=False),
        sa.Column("parser_version", sa.String(length=64), nullable=True),
        sa.Column("derived_object_key", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["snapshot_id"], ["source_snapshots.snapshot_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("document_id"),
        sa.UniqueConstraint("snapshot_id", "relative_path"),
    )
    op.create_index(
        "ix_source_documents_snapshot_id", "source_documents", ["snapshot_id"]
    )
    op.create_index(
        "ix_source_documents_content_hash", "source_documents", ["content_hash"]
    )

    op.create_table(
        "project_versions",
        sa.Column("version_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=32), nullable=False),
        sa.Column("base_version_id", sa.String(length=36), nullable=True),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("issue_revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["base_version_id"], ["project_versions.version_id"]
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.project_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("version_id"),
        sa.UniqueConstraint("project_id", "sequence_no"),
    )
    op.create_index(
        "ix_project_versions_project_id", "project_versions", ["project_id"]
    )
    op.create_index(
        "ix_project_versions_base_version_id", "project_versions", ["base_version_id"]
    )
    op.create_index("ix_project_versions_state", "project_versions", ["state"])

    op.create_table(
        "audit_input_snapshots",
        sa.Column("snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("project_version_id", sa.String(length=36), nullable=False),
        sa.Column("issue_revision", sa.Integer(), nullable=False),
        sa.Column("input_hash", sa.String(length=128), nullable=False),
        sa.Column("issue_payload", sa.JSON(), nullable=False),
        sa.Column("central_asset_versions", sa.JSON(), nullable=False),
        sa.Column("run_manifest_object_key", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_version_id"], ["project_versions.version_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("snapshot_id"),
    )
    op.create_index(
        "ix_audit_input_snapshots_project_version_id",
        "audit_input_snapshots",
        ["project_version_id"],
    )
    op.create_index(
        "ix_audit_input_snapshots_input_hash",
        "audit_input_snapshots",
        ["input_hash"],
    )

    op.create_table(
        "issues",
        sa.Column("issue_id", sa.String(length=36), nullable=False),
        sa.Column("project_version_id", sa.String(length=36), nullable=False),
        sa.Column("origin", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("title_hint", sa.String(length=500), nullable=True),
        sa.Column("observed_gap", sa.Text(), nullable=False),
        sa.Column("evidence_summary", sa.Text(), nullable=True),
        sa.Column("risk_category", sa.String(length=128), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("validation_flags", sa.JSON(), nullable=False),
        sa.Column("row_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_version_id"], ["project_versions.version_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("issue_id"),
    )
    op.create_index("ix_issues_project_version_id", "issues", ["project_version_id"])
    op.create_index("ix_issues_status", "issues", ["status"])
    op.create_table(
        "issue_source_refs",
        sa.Column("reference_id", sa.String(length=36), nullable=False),
        sa.Column("issue_id", sa.String(length=36), nullable=False),
        sa.Column("ref_kind", sa.String(length=32), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("unit_id", sa.String(length=255), nullable=True),
        sa.Column("location", sa.JSON(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["document_id"], ["source_documents.document_id"]
        ),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.issue_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("reference_id"),
    )
    op.create_index("ix_issue_source_refs_issue_id", "issue_source_refs", ["issue_id"])
    op.create_index(
        "ix_issue_source_refs_document_id", "issue_source_refs", ["document_id"]
    )

    op.create_table(
        "jobs",
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("project_version_id", sa.String(length=36), nullable=False),
        sa.Column("job_type", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=True),
        sa.Column("input_hash", sa.String(length=128), nullable=False),
        sa.Column("completed_items", sa.Integer(), nullable=False),
        sa.Column("total_items", sa.Integer(), nullable=True),
        sa.Column("current_message", sa.Text(), nullable=True),
        sa.Column("checkpoint", sa.JSON(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("correlation_id", sa.String(length=64), nullable=False),
        sa.Column("lease_owner", sa.String(length=255), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("input_snapshot_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["input_snapshot_id"], ["audit_input_snapshots.snapshot_id"]
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.project_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["project_version_id"], ["project_versions.version_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("job_id"),
        sa.UniqueConstraint("input_snapshot_id"),
    )
    op.create_index("ix_jobs_project_id", "jobs", ["project_id"])
    op.create_index("ix_jobs_project_version_id", "jobs", ["project_version_id"])
    op.create_index("ix_jobs_job_type", "jobs", ["job_type"])
    op.create_index("ix_jobs_state", "jobs", ["state"])
    op.create_index("ix_jobs_input_hash", "jobs", ["input_hash"])
    op.create_index("ix_jobs_correlation_id", "jobs", ["correlation_id"])
    op.create_index(
        "ix_jobs_lease_expires_at", "jobs", ["lease_expires_at"]
    )
    op.create_table(
        "job_events",
        sa.Column("event_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("completed_items", sa.Integer(), nullable=False),
        sa.Column("total_items", sa.Integer(), nullable=True),
        sa.Column("warning", sa.Boolean(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.job_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_job_events_job_id", "job_events", ["job_id"])

    op.create_table(
        "output_revisions",
        sa.Column("output_id", sa.String(length=36), nullable=False),
        sa.Column("project_version_id", sa.String(length=36), nullable=False),
        sa.Column("audit_input_snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("run_manifest_object_key", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["audit_input_snapshot_id"], ["audit_input_snapshots.snapshot_id"]
        ),
        sa.ForeignKeyConstraint(
            ["project_version_id"], ["project_versions.version_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("output_id"),
        sa.UniqueConstraint("project_version_id", "ordinal"),
    )
    op.create_index(
        "ix_output_revisions_project_version_id",
        "output_revisions",
        ["project_version_id"],
    )
    op.create_index(
        "ix_output_revisions_audit_input_snapshot_id",
        "output_revisions",
        ["audit_input_snapshot_id"],
    )
    op.create_index("ix_output_revisions_status", "output_revisions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_output_revisions_status", table_name="output_revisions")
    op.drop_index(
        "ix_output_revisions_audit_input_snapshot_id", table_name="output_revisions"
    )
    op.drop_index(
        "ix_output_revisions_project_version_id", table_name="output_revisions"
    )
    op.drop_table("output_revisions")
    op.drop_index("ix_job_events_job_id", table_name="job_events")
    op.drop_table("job_events")
    op.drop_index("ix_jobs_lease_expires_at", table_name="jobs")
    op.drop_index("ix_jobs_correlation_id", table_name="jobs")
    op.drop_index("ix_jobs_input_hash", table_name="jobs")
    op.drop_index("ix_jobs_state", table_name="jobs")
    op.drop_index("ix_jobs_job_type", table_name="jobs")
    op.drop_index("ix_jobs_project_version_id", table_name="jobs")
    op.drop_index("ix_jobs_project_id", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index("ix_issue_source_refs_document_id", table_name="issue_source_refs")
    op.drop_index("ix_issue_source_refs_issue_id", table_name="issue_source_refs")
    op.drop_table("issue_source_refs")
    op.drop_index("ix_issues_status", table_name="issues")
    op.drop_index("ix_issues_project_version_id", table_name="issues")
    op.drop_table("issues")
    op.drop_index(
        "ix_audit_input_snapshots_input_hash", table_name="audit_input_snapshots"
    )
    op.drop_index(
        "ix_audit_input_snapshots_project_version_id",
        table_name="audit_input_snapshots",
    )
    op.drop_table("audit_input_snapshots")
    op.drop_index("ix_project_versions_state", table_name="project_versions")
    op.drop_index(
        "ix_project_versions_base_version_id", table_name="project_versions"
    )
    op.drop_index("ix_project_versions_project_id", table_name="project_versions")
    op.drop_table("project_versions")
    op.drop_index(
        "ix_source_documents_content_hash", table_name="source_documents"
    )
    op.drop_index(
        "ix_source_documents_snapshot_id", table_name="source_documents"
    )
    op.drop_table("source_documents")
    op.drop_index(
        "ix_source_snapshots_project_id", table_name="source_snapshots"
    )
    op.drop_table("source_snapshots")
    op.drop_index("ix_upload_files_content_hash", table_name="upload_files")
    op.drop_index("ix_upload_files_session_id", table_name="upload_files")
    op.drop_table("upload_files")
    op.drop_index("ix_upload_sessions_expires_at", table_name="upload_sessions")
    op.drop_index("ix_upload_sessions_state", table_name="upload_sessions")
    op.drop_table("upload_sessions")
    op.drop_index("uq_projects_name", table_name="projects")
