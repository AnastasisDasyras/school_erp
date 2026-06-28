from __future__ import annotations

import uuid
from typing import Protocol

from app.modules.enrollment.domain.enrollment import Enrollment


class EnrollmentRepository(Protocol):
    async def add(self, enrollment: Enrollment) -> None: ...

    async def exists(self, *, student_id: uuid.UUID, course_id: uuid.UUID) -> bool: ...

    async def list_for_student(self, student_id: uuid.UUID) -> list[Enrollment]: ...

    async def list_for_course(self, course_id: uuid.UUID) -> list[Enrollment]: ...
