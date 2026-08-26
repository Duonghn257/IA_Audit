"""add audit version creator metadata

Revision ID: eef4c5957406
Revises: 786f4ab3ed2d
Create Date: 2026-08-25 16:48:03.357492
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'eef4c5957406'
down_revision: Union[str, Sequence[str], None] = '786f4ab3ed2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("project_versions") as batch_op:
        batch_op.add_column(
            sa.Column("created_by_user_id", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column("created_by_name", sa.String(length=255), nullable=True)
        )

    op.execute(
        sa.text(
            """
            UPDATE project_versions
            SET created_by_user_id = (
                    SELECT projects.owner_user_id
                    FROM projects
                    WHERE projects.project_id = project_versions.project_id
                ),
                created_by_name = COALESCE(
                    (
                        SELECT auth_users.display_name
                        FROM auth_users
                        JOIN projects
                          ON projects.owner_user_id = auth_users.user_id
                        WHERE projects.project_id = project_versions.project_id
                    ),
                    (
                        SELECT CASE
                            WHEN projects.owner_user_id = :shared_owner
                            THEN :shared_name
                            ELSE projects.owner_user_id
                        END
                        FROM projects
                        WHERE projects.project_id = project_versions.project_id
                    )
                )
            """
        ).bindparams(
            shared_owner="uat_shared_user",
            shared_name="UAT shared user",
        )
    )

    with op.batch_alter_table("project_versions") as batch_op:
        batch_op.alter_column(
            "created_by_user_id",
            existing_type=sa.String(length=255),
            nullable=False,
        )
        batch_op.alter_column(
            "created_by_name",
            existing_type=sa.String(length=255),
            nullable=False,
        )
        batch_op.create_index(
            "ix_project_versions_created_by_user_id",
            ["created_by_user_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("project_versions") as batch_op:
        batch_op.drop_index("ix_project_versions_created_by_user_id")
        batch_op.drop_column("created_by_name")
        batch_op.drop_column("created_by_user_id")
