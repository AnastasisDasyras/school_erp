from __future__ import annotations

import uuid

from app.modules.teachers.domain.teacher import Teacher


class InMemoryTeacherRepository:
    def __init__(self) -> None:
        self._teachers: dict[uuid.UUID, Teacher] = {}

    async def add(self, teacher: Teacher) -> None:
        self._teachers[teacher.id] = teacher

    async def get(self, teacher_id: uuid.UUID) -> Teacher | None:
        return self._teachers.get(teacher_id)

    async def get_by_email(self, email: str) -> Teacher | None:
        return next((t for t in self._teachers.values() if t.email == email), None)

    async def list(self, *, offset: int, limit: int, search: str | None) -> list[Teacher]:
        teachers = list(self._teachers.values())
        if search:
            needle = search.lower()
            teachers = [
                t
                for t in teachers
                if needle in t.first_name.lower()
                or needle in t.last_name.lower()
                or needle in t.email.lower()
                or needle in t.department.lower()
            ]
        teachers.sort(key=lambda t: (t.last_name, t.first_name))
        return teachers[offset : offset + limit]

    async def count(self, *, search: str | None) -> int:
        return len(await self.list(offset=0, limit=10_000, search=search))

    async def update(self, teacher: Teacher) -> None:
        self._teachers[teacher.id] = teacher

    async def delete(self, teacher_id: uuid.UUID) -> None:
        self._teachers.pop(teacher_id, None)
