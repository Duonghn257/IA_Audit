"""Constrain issue risk category values.

Revision ID: 20260827_05
Revises: eef4c5957406
Create Date: 2026-08-27
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260827_05"
down_revision: Union[str, Sequence[str], None] = "eef4c5957406"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CONSTRAINT_NAME = "ck_issues_risk_category"
_CONSTRAINT_SQL = (
    "risk_category IS NULL OR risk_category IN "
    "('Compliance', 'Operational', 'Strategic', 'Financial')"
)


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        # NOT VALID preserves legacy free-text rows while enforcing the four
        # allowed values for every new or updated row.
        op.execute(
            f"ALTER TABLE issues ADD CONSTRAINT {_CONSTRAINT_NAME} "
            f"CHECK ({_CONSTRAINT_SQL}) NOT VALID"
        )
        return

    with op.batch_alter_table("issues") as batch_op:
        batch_op.create_check_constraint(
            _CONSTRAINT_NAME,
            _CONSTRAINT_SQL,
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            f"ALTER TABLE issues DROP CONSTRAINT {_CONSTRAINT_NAME}"
        )
        return

    with op.batch_alter_table("issues") as batch_op:
        batch_op.drop_constraint(
            _CONSTRAINT_NAME,
            type_="check",
        )
