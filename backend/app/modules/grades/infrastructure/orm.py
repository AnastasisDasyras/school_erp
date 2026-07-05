import uuid

from sqlalchemy import Float, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class GradeModel(Base):
    """ORM mapping for grades.

    `version` is the optimistic-lock counter. The repository's update()
    method issues:
        UPDATE grades SET ..., version = version + 1 WHERE id = ? AND version = ?
    If the WHERE matches 0 rows (another writer already bumped version),
    update() raises StaleGradeError so the service can retry.

    The composite index on (student_id, course_id) is the Phase 7 index
    demo target: a query filtering by both columns should use this index
    rather than two separate single-column index scans.
    """

    __tablename__ = "grades"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", name="uq_grade_student_course"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    letter: Mapped[str] = mapped_column(String(1), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
