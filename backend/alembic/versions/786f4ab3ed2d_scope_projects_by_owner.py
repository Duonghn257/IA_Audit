"""scope projects by owner

Revision ID: 786f4ab3ed2d
Revises: 20260825_04
Create Date: 2026-08-25 16:12:57.596895
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "786f4ab3ed2d"
down_revision: Union[str, Sequence[str], None] = "20260825_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(
            sa.Column(
                "owner_user_id",
                sa.String(length=255),
                nullable=True,
            )
        )

    # Promotion writes the same timestamp to projects.created_at and
    # upload_sessions.promoted_at in one transaction. Only exact, unique
    # matches are trusted for ownership recovery.
    op.execute(
        sa.text(
            """
            UPDATE projects
            SET owner_user_id = (
                SELECT upload_sessions.actor_id
                FROM upload_sessions
                WHERE upload_sessions.state = :promoted_state
                  AND upload_sessions.promoted_at = projects.created_at
                LIMIT 1
            )
            WHERE (
                SELECT COUNT(*)
                FROM upload_sessions
                WHERE upload_sessions.state = :promoted_state
                  AND upload_sessions.promoted_at = projects.created_at
            ) = 1
            """
        ).bindparams(promoted_state="PROMOTED")
    )
    # Projects predating actor-aware uploads stay accessible only in the
    # deliberately shared UAT mode; they are not assigned to a Google user.
    op.execute(
        sa.text(
            """
            UPDATE projects
            SET owner_user_id = :shared_owner
            WHERE owner_user_id IS NULL
            """
        ).bindparams(shared_owner="uat_shared_user")
    )

    with op.batch_alter_table("projects") as batch_op:
        batch_op.alter_column(
            "owner_user_id",
            existing_type=sa.String(length=255),
            nullable=False,
        )

    op.drop_index("uq_projects_name", table_name="projects")
    op.create_index(
        "ix_projects_owner_user_id",
        "projects",
        ["owner_user_id"],
        unique=False,
    )
    op.create_index(
        "uq_projects_owner_name",
        "projects",
        ["owner_user_id", "name"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_projects_owner_name", table_name="projects")
    op.drop_index("ix_projects_owner_user_id", table_name="projects")
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("owner_user_id")
    op.create_index("uq_projects_name", "projects", ["name"], unique=True)
