from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date


class InvalidEnrollmentError(ValueError):
    """Raised when an Enrollment would be constructed in an invalid state."""


@dataclass
class Enrollment:
    id: uuid.UUID
    student_id: uuid.UUID
    course_id: uuid.UUID
    enrolled_on: date = field(default_factory=date.today)

    @classmethod
    def create(cls, *, student_id: uuid.UUID, course_id: uuid.UUID) -> Enrollment:
        return cls(id=uuid.uuid4(), student_id=student_id, course_id=course_id)
