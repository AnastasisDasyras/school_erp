from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


class InvalidAttendanceError(ValueError):
    pass


class AttendanceStatus(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"


@dataclass
class AttendanceRecord:
    id: uuid.UUID
    student_id: uuid.UUID
    course_id: uuid.UUID
    status: AttendanceStatus
    recorded_on: date = field(default_factory=date.today)

    @classmethod
    def create(
        cls, *, student_id: uuid.UUID, course_id: uuid.UUID, status: AttendanceStatus
    ) -> AttendanceRecord:
        return cls(id=uuid.uuid4(), student_id=student_id, course_id=course_id, status=status)
