from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.teachers.domain.teacher import Teacher
from app.modules.teachers.infrastructure.orm import TeacherModel


def _to_domain(row: TeacherModel) -> Teacher:
    return Teacher(
        id=row.id,
        first_name=row.first_name,
        last_name=row.last_name,
        email=row.email,
        department=row.department,
        is_active=row.is_active,
    )


def _to_row(teacher: Teacher) -> TeacherModel:
    return TeacherModel(
        id=teacher.id,
        first_name=teacher.first_name,
        last_name=teacher.last_name,
        email=teacher.email,
        department=teacher.department,
        is_active=teacher.is_active,
    )


class SqlAlchemyTeacherRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, teacher: Teacher) -> None:
        self._session.add(_to_row(teacher))
        await self._session.flush()

    async def get(self, teacher_id: uuid.UUID) -> Teacher | None:
        row = await self._session.get(TeacherModel, teacher_id)
        return _to_domain(row) if row else None

    async def get_by_email(self, email: str) -> Teacher | None:
        stmt = select(TeacherModel).where(TeacherModel.email == email)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_domain(row) if row else None

    async def list(self, *, offset: int, limit: int, search: str | None) -> list[Teacher]:
        stmt = select(TeacherModel).order_by(TeacherModel.last_name, TeacherModel.first_name)
        stmt = _apply_search(stmt, search)
        stmt = stmt.offset(offset).limit(limit)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]

    async def count(self, *, search: str | None) -> int:
        stmt = select(func.count()).select_from(TeacherModel)
        stmt = _apply_search(stmt, search)
        return (await self._session.execute(stmt)).scalar_one()

    async def update(self, teacher: Teacher) -> None:
        row = await self._session.get(TeacherModel, teacher.id)
        if row is None:
            return
        row.first_name = teacher.first_name
        row.last_name = teacher.last_name
        row.email = teacher.email
        row.department = teacher.department
        row.is_active = teacher.is_active
        await self._session.flush()

    async def delete(self, teacher_id: uuid.UUID) -> None:
        row = await self._session.get(TeacherModel, teacher_id)
        if row is not None:
            await self._session.delete(row)
            await self._session.flush()


def _apply_search(stmt, search: str | None):  # type: ignore[no-untyped-def]
    if not search:
        return stmt
    pattern = f"%{search}%"
    return stmt.where(
        or_(
            TeacherModel.first_name.ilike(pattern),
            TeacherModel.last_name.ilike(pattern),
            TeacherModel.email.ilike(pattern),
            TeacherModel.department.ilike(pattern),
        )
    )
