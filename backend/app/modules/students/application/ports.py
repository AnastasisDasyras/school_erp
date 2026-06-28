from __future__ import annotations

import uuid
from typing import Protocol

from app.modules.students.domain.student import Student


class StudentRepository(Protocol):
    """Port: the application layer depends on this shape, never on SQLAlchemy.

    `infrastructure/repository.py` provides the real (Postgres) adapter; tests
    can provide an in-memory fake — that's the dependency-inversion payoff.
    """

    async def add(self, student: Student) -> None: ...

    async def get(self, student_id: uuid.UUID) -> Student | None: ...

    async def get_by_email(self, email: str) -> Student | None: ...

    async def list(self, *, offset: int, limit: int, search: str | None) -> list[Student]: ...

    async def count(self, *, search: str | None) -> int: ...

    async def update(self, student: Student) -> None: ...

    async def delete(self, student_id: uuid.UUID) -> None: ...
