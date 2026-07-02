from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from app.modules.attendance.domain.attendance import AttendanceStatus


@dataclass(frozen=True)
class RecordAttendanceInput:
    student_id: uuid.UUID
    course_id: uuid.UUID
    status: AttendanceStatus


@dataclass(frozen=True)
class AttendanceView:
    id: uuid.UUID
    student_id: uuid.UUID
    course_id: uuid.UUID
    status: AttendanceStatus
    recorded_on: date
