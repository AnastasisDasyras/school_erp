from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.attendance.domain.attendance import AttendanceRecord
from app.modules.attendance.infrastructure.orm import AttendanceModel


def _to_row(record: AttendanceRecord) -> AttendanceModel:
    return AttendanceModel(
        id=record.id,
        student_id=record.student_id,
        course_id=record.course_id,
        status=record.status.value,
        recorded_on=record.recorded_on,
    )


class SqlAlchemyAttendanceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: AttendanceRecord) -> None:
        self._session.add(_to_row(record))
        await self._session.flush()

    async def exists_for_day(
        self, *, student_id: uuid.UUID, course_id: uuid.UUID, recorded_on: date
    ) -> bool:
        stmt = select(AttendanceModel.id).where(
            AttendanceModel.student_id == student_id,
            AttendanceModel.course_id == course_id,
            AttendanceModel.recorded_on == recorded_on,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None
