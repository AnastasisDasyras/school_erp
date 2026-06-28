from __future__ import annotations

import uuid

from app.modules.teachers.application.dto import (
    CreateTeacherInput,
    TeacherPage,
    TeacherView,
    UpdateTeacherInput,
)
from app.modules.teachers.application.exceptions import (
    DuplicateTeacherEmailError,
    TeacherNotFoundError,
)
from app.modules.teachers.application.ports import TeacherRepository
from app.modules.teachers.domain.teacher import Teacher


def _to_view(teacher: Teacher) -> TeacherView:
    return TeacherView(
        id=teacher.id,
        first_name=teacher.first_name,
        last_name=teacher.last_name,
        full_name=teacher.full_name,
        email=teacher.email,
        department=teacher.department,
        is_active=teacher.is_active,
    )


class TeacherService:
    def __init__(self, repository: TeacherRepository) -> None:
        self._repository = repository

    async def create(self, data: CreateTeacherInput) -> TeacherView:
        if await self._repository.get_by_email(data.email) is not None:
            raise DuplicateTeacherEmailError(data.email)

        teacher = Teacher.create(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            department=data.department,
        )
        await self._repository.add(teacher)
        return _to_view(teacher)

    async def get(self, teacher_id: uuid.UUID) -> TeacherView:
        teacher = await self._repository.get(teacher_id)
        if teacher is None:
            raise TeacherNotFoundError(teacher_id)
        return _to_view(teacher)

    async def list(self, *, offset: int, limit: int, search: str | None) -> TeacherPage:
        teachers = await self._repository.list(offset=offset, limit=limit, search=search)
        total = await self._repository.count(search=search)
        return TeacherPage(
            items=[_to_view(t) for t in teachers],
            total=total,
            offset=offset,
            limit=limit,
        )

    async def update(self, teacher_id: uuid.UUID, data: UpdateTeacherInput) -> TeacherView:
        teacher = await self._repository.get(teacher_id)
        if teacher is None:
            raise TeacherNotFoundError(teacher_id)

        existing_with_email = await self._repository.get_by_email(data.email)
        if existing_with_email is not None and existing_with_email.id != teacher_id:
            raise DuplicateTeacherEmailError(data.email)

        teacher.update_details(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            department=data.department,
        )
        await self._repository.update(teacher)
        return _to_view(teacher)

    async def deactivate(self, teacher_id: uuid.UUID) -> None:
        teacher = await self._repository.get(teacher_id)
        if teacher is None:
            raise TeacherNotFoundError(teacher_id)
        teacher.deactivate()
        await self._repository.update(teacher)

    async def delete(self, teacher_id: uuid.UUID) -> None:
        teacher = await self._repository.get(teacher_id)
        if teacher is None:
            raise TeacherNotFoundError(teacher_id)
        await self._repository.delete(teacher_id)
