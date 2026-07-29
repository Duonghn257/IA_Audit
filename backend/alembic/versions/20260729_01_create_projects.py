"""Create projects and project events tables.

Revision ID: 20260729_01
Revises:
Create Date: 2026-07-29
"""
from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260729_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_activity", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("output_path", sa.Text(), nullable=True),
        sa.Column("version", sa.String(length=32), nullable=True),
        sa.Column("issue_count", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("raw_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("project_id"),
    )
    op.create_index(
        op.f("ix_projects_raw_expires_at"),
        "projects",
        ["raw_expires_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_projects_status"),
        "projects",
        ["status"],
        unique=False,
    )

    op.create_table(
        "project_events",
        sa.Column("event_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("completed_steps", sa.Integer(), nullable=False),
        sa.Column("total_steps", sa.Integer(), nullable=False),
        sa.Column("warning", sa.Boolean(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.project_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        op.f("ix_project_events_project_id"),
        "project_events",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_project_events_project_id"),
        table_name="project_events",
    )
    op.drop_table("project_events")
    op.drop_index(op.f("ix_projects_status"), table_name="projects")
    op.drop_index(
        op.f("ix_projects_raw_expires_at"),
        table_name="projects",
    )
    op.drop_table("projects")
