from __future__ import annotations

import uuid

from app.modules.students.domain.student import Student


class InMemoryStudentRepository:
    """Fake adapter for the StudentRepository port — no database, no SQLAlchemy.

    This is the entire point of depending on a Protocol instead of a concrete
    class: the service can be unit tested in microseconds.
    """

    def __init__(self) -> None:
        self._students: dict[uuid.UUID, Student] = {}

    async def add(self, student: Student) -> None:
        self._students[student.id] = student

    async def get(self, student_id: uuid.UUID) -> Student | None:
        return self._students.get(student_id)

    async def get_by_email(self, email: str) -> Student | None:
        return next((s for s in self._students.values() if s.email == email), None)

    async def list(self, *, offset: int, limit: int, search: str | None) -> list[Student]:
        students = list(self._students.values())
        if search:
            needle = search.lower()
            students = [
                s
                for s in students
                if needle in s.first_name.lower()
                or needle in s.last_name.lower()
                or needle in s.email.lower()
            ]
        students.sort(key=lambda s: (s.last_name, s.first_name))
        return students[offset : offset + limit]

    async def count(self, *, search: str | None) -> int:
        return len(await self.list(offset=0, limit=10_000, search=search))

    async def update(self, student: Student) -> None:
        self._students[student.id] = student

    async def delete(self, student_id: uuid.UUID) -> None:
        self._students.pop(student_id, None)
