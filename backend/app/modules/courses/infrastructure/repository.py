from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.courses.domain.course import Course
from app.modules.courses.infrastructure.orm import CourseModel


def _to_domain(row: CourseModel) -> Course:
    return Course(
        id=row.id,
        title=row.title,
        teacher_id=row.teacher_id,
        capacity=row.capacity,
        available_seats=row.available_seats,
        is_active=row.is_active,
    )


def _to_row(course: Course) -> CourseModel:
    return CourseModel(
        id=course.id,
        title=course.title,
        teacher_id=course.teacher_id,
        capacity=course.capacity,
        available_seats=course.available_seats,
        is_active=course.is_active,
    )


class SqlAlchemyCourseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, course: Course) -> None:
        self._session.add(_to_row(course))
        await self._session.flush()

    async def get(self, course_id: uuid.UUID) -> Course | None:
        row = await self._session.get(CourseModel, course_id)
        return _to_domain(row) if row else None

    async def get_for_update(self, course_id: uuid.UUID) -> Course | None:
        stmt = select(CourseModel).where(CourseModel.id == course_id).with_for_update()
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_domain(row) if row else None

    async def list(self, *, offset: int, limit: int, search: str | None) -> list[Course]:
        stmt = select(CourseModel).order_by(CourseModel.title)
        stmt = _apply_search(stmt, search)
        stmt = stmt.offset(offset).limit(limit)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]

    async def count(self, *, search: str | None) -> int:
        stmt = select(func.count()).select_from(CourseModel)
        stmt = _apply_search(stmt, search)
        return (await self._session.execute(stmt)).scalar_one()

    async def update(self, course: Course) -> None:
        row = await self._session.get(CourseModel, course.id)
        if row is None:
            return
        row.title = course.title
        row.teacher_id = course.teacher_id
        row.capacity = course.capacity
        row.available_seats = course.available_seats
        row.is_active = course.is_active
        await self._session.flush()

    async def delete(self, course_id: uuid.UUID) -> None:
        row = await self._session.get(CourseModel, course_id)
        if row is not None:
            await self._session.delete(row)
            await self._session.flush()


def _apply_search(stmt, search: str | None):  # type: ignore[no-untyped-def]
    if not search:
        return stmt
    return stmt.where(CourseModel.title.ilike(f"%{search}%"))
