from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel

from app.modules.attendance.application.dto import AttendanceView
from app.modules.attendance.domain.attendance import AttendanceStatus


class RecordAttendanceRequest(BaseModel):
    student_id: uuid.UUID
    course_id: uuid.UUID
    status: AttendanceStatus


class AttendanceResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    course_id: uuid.UUID
    status: AttendanceStatus
    recorded_on: date

    @classmethod
    def from_view(cls, view: AttendanceView) -> AttendanceResponse:
        return cls(**view.__dict__)
