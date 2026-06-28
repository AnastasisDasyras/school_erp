from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.enrollment.domain.enrollment import Enrollment
from app.modules.enrollment.infrastructure.orm import EnrollmentModel


def _to_domain(row: EnrollmentModel) -> Enrollment:
    return Enrollment(
        id=row.id,
        student_id=row.student_id,
        course_id=row.course_id,
        enrolled_on=row.enrolled_on,
    )


def _to_row(enrollment: Enrollment) -> EnrollmentModel:
    return EnrollmentModel(
        id=enrollment.id,
        student_id=enrollment.student_id,
        course_id=enrollment.course_id,
        enrolled_on=enrollment.enrolled_on,
    )


class SqlAlchemyEnrollmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, enrollment: Enrollment) -> None:
        self._session.add(_to_row(enrollment))
        await self._session.flush()

    async def exists(self, *, student_id: uuid.UUID, course_id: uuid.UUID) -> bool:
        stmt = select(EnrollmentModel.id).where(
            EnrollmentModel.student_id == student_id,
            EnrollmentModel.course_id == course_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def list_for_student(self, student_id: uuid.UUID) -> list[Enrollment]:
        stmt = select(EnrollmentModel).where(EnrollmentModel.student_id == student_id)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]

    async def list_for_course(self, course_id: uuid.UUID) -> list[Enrollment]:
        stmt = select(EnrollmentModel).where(EnrollmentModel.course_id == course_id)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]
