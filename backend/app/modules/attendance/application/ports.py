from __future__ import annotations

import uuid
from datetime import date
from typing import Protocol

from app.modules.attendance.domain.attendance import AttendanceRecord


class AttendanceRepository(Protocol):
    async def add(self, record: AttendanceRecord) -> None: ...

    async def exists_for_day(
        self, *, student_id: uuid.UUID, course_id: uuid.UUID, recorded_on: date
    ) -> bool: ...
