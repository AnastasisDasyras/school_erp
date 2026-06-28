"""create students table

Revision ID: 0001
Revises:
Create Date: 2026-06-26

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "students",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("enrolled_on", sa.Date(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_unique_constraint("uq_students_email", "students", ["email"])
    op.create_index("ix_students_email", "students", ["email"])
    op.create_index("ix_students_last_name_first_name", "students", ["last_name", "first_name"])


def downgrade() -> None:
    op.drop_index("ix_students_last_name_first_name", table_name="students")
    op.drop_index("ix_students_email", table_name="students")
    op.drop_constraint("uq_students_email", "students", type_="unique")
    op.drop_table("students")
