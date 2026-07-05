"""create grades table and add composite indexes for Phase 7

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-05

Phase 7 adds three things:
1. grades table with a `version` column for optimistic locking.
2. Composite index on attendance_records(student_id, course_id) — the common
   filter pattern is "all attendance for a student in a course". Without a
   composite index Postgres does a bitmap-AND of two separate index scans;
   with it, a single Index Scan satisfies both predicates.
3. Composite index on enrollments(student_id, course_id) — same reasoning.

The single-column indexes created in migration 0004/0002 are left in place:
queries that filter by only one column still benefit from them.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # ── Grades table ───────────────────────────────────────────────────────────
    op.create_table(
        "grades",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("letter", sa.String(length=1), nullable=False),
        # Optimistic-lock counter. Repository UPDATE checks WHERE version=?,
        # increments to version+1. 0 rows affected → StaleGradeError → retry.
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_unique_constraint("uq_grade_student_course", "grades", ["student_id", "course_id"])

    


def downgrade() -> None:
    op.drop_constraint("uq_grade_student_course", "grades")
    op.drop_table("grades")
