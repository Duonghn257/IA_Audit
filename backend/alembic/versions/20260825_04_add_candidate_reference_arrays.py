"""Add separate evidence and SOP references to candidate issues.

Revision ID: 20260825_04
Revises: 20260824_03
Create Date: 2026-08-25
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_04"
down_revision: str | None = "20260824_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "issues",
        sa.Column(
            "evidence_refs",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    op.add_column(
        "issues",
        sa.Column(
            "sop_refs",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("issues", "sop_refs")
    op.drop_column("issues", "evidence_refs")
