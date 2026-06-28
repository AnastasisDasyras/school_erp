from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.students.domain.student import Student
from app.modules.students.infrastructure.orm import StudentModel


def _to_domain(row: StudentModel) -> Student:
    return Student(
        id=row.id,
        first_name=row.first_name,
        last_name=row.last_name,
        email=row.email,
        date_of_birth=row.date_of_birth,
        enrolled_on=row.enrolled_on,
        is_active=row.is_active,
    )


def _to_row(student: Student) -> StudentModel:
    return StudentModel(
        id=student.id,
        first_name=student.first_name,
        last_name=student.last_name,
        email=student.email,
        date_of_birth=student.date_of_birth,
        enrolled_on=student.enrolled_on,
        is_active=student.is_active,
    )


class SqlAlchemyStudentRepository:
    """Postgres adapter implementing the StudentRepository port."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, student: Student) -> None:
        self._session.add(_to_row(student))
        await self._session.flush()

    async def get(self, student_id: uuid.UUID) -> Student | None:
        row = await self._session.get(StudentModel, student_id)
        return _to_domain(row) if row else None

    async def get_by_email(self, email: str) -> Student | None:
        stmt = select(StudentModel).where(StudentModel.email == email)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_domain(row) if row else None

    async def list(self, *, offset: int, limit: int, search: str | None) -> list[Student]:
        stmt = select(StudentModel).order_by(StudentModel.last_name, StudentModel.first_name)
        stmt = _apply_search(stmt, search)
        stmt = stmt.offset(offset).limit(limit)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]

    async def count(self, *, search: str | None) -> int:
        stmt = select(func.count()).select_from(StudentModel)
        stmt = _apply_search(stmt, search)
        return (await self._session.execute(stmt)).scalar_one()

    async def update(self, student: Student) -> None:
        row = await self._session.get(StudentModel, student.id)
        if row is None:
            return
        row.first_name = student.first_name
        row.last_name = student.last_name
        row.email = student.email
        row.date_of_birth = student.date_of_birth
        row.is_active = student.is_active
        await self._session.flush()

    async def delete(self, student_id: uuid.UUID) -> None:
        row = await self._session.get(StudentModel, student_id)
        if row is not None:
            await self._session.delete(row)
            await self._session.flush()


def _apply_search(stmt, search: str | None):  # type: ignore[no-untyped-def]
    if not search:
        return stmt
    pattern = f"%{search}%"
    return stmt.where(
        or_(
            StudentModel.first_name.ilike(pattern),
            StudentModel.last_name.ilike(pattern),
            StudentModel.email.ilike(pattern),
        )
    )
