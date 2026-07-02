from __future__ import annotations

import uuid
from datetime import date

from app.modules.attendance.domain.attendance import AttendanceRecord


class InMemoryAttendanceRepository:
    def __init__(self) -> None:
        self._records: list[AttendanceRecord] = []

    async def add(self, record: AttendanceRecord) -> None:
        self._records.append(record)

    async def exists_for_day(
        self, *, student_id: uuid.UUID, course_id: uuid.UUID, recorded_on: date
    ) -> bool:
        return any(
            r.student_id == student_id and r.course_id == course_id and r.recorded_on == recorded_on
            for r in self._records
        )
