"""create outbox_events and attendance_records tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-29

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

# create_type=True (the default) means op.create_table below creates this
# enum type as part of creating the table — no separate .create() call
# needed (and calling .create() explicitly here duplicates that, raising
# DuplicateObjectError).
_outbox_status = postgresql.ENUM("pending", "published", "failed", name="outbox_status")


def upgrade() -> None:
    op.create_table(
        "outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.String(), nullable=False),
        sa.Column("status", _outbox_status, nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_outbox_events_event_type", "outbox_events", ["event_type"])
    op.create_index("ix_outbox_events_status", "outbox_events", ["status"])

    op.create_table(
        "attendance_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("recorded_on", sa.Date(), nullable=False),
    )
    op.create_index("ix_attendance_records_course_id", "attendance_records", ["course_id"])
    op.create_unique_constraint(
        "uq_attendance_student_course_day",
        "attendance_records",
        ["student_id", "course_id", "recorded_on"],
    )


def downgrade() -> None:
    op.drop_table("attendance_records")
    op.drop_table("outbox_events")
    _outbox_status.drop(op.get_bind(), checkfirst=True)  # not auto-dropped by drop_table
