"""add current central guideline and template assets

Revision ID: 20260903_06
Revises: 20260827_05
Create Date: 2026-09-03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20260903_06"
down_revision: str | None = "20260827_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "central_assets",
        sa.Column("asset_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("uploaded_by", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("asset_id"),
        sa.UniqueConstraint("kind", "filename"),
    )
    op.create_index("ix_central_assets_kind", "central_assets", ["kind"])
    op.create_index(
        "ix_central_assets_content_hash",
        "central_assets",
        ["content_hash"],
    )
    op.create_index(
        "ix_central_assets_uploaded_by",
        "central_assets",
        ["uploaded_by"],
    )


def downgrade() -> None:
    op.drop_index("ix_central_assets_uploaded_by", table_name="central_assets")
    op.drop_index("ix_central_assets_content_hash", table_name="central_assets")
    op.drop_index("ix_central_assets_kind", table_name="central_assets")
    op.drop_table("central_assets")
