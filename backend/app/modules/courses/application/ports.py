from __future__ import annotations

import uuid
from typing import Protocol

from app.modules.courses.domain.course import Course


class CourseRepository(Protocol):
    async def add(self, course: Course) -> None: ...

    async def get(self, course_id: uuid.UUID) -> Course | None: ...

    async def get_for_update(self, course_id: uuid.UUID) -> Course | None:
        """Locks the row (SELECT ... FOR UPDATE) — used by Enrollment to
        prevent a race on available_seats under concurrent enrollments."""
        ...

    async def list(self, *, offset: int, limit: int, search: str | None) -> list[Course]: ...

    async def count(self, *, search: str | None) -> int: ...

    async def update(self, course: Course) -> None: ...

    async def delete(self, course_id: uuid.UUID) -> None: ...
