from __future__ import annotations

import uuid

from app.modules.courses.domain.course import Course
from app.modules.enrollment.domain.enrollment import Enrollment


class InMemoryCourseRepository:
    """Fake for the CourseRepository port. No real row locking — single-threaded
    tests don't need it; `get_for_update` just returns the same in-memory object."""

    def __init__(self) -> None:
        self._courses: dict[uuid.UUID, Course] = {}

    async def add(self, course: Course) -> None:
        self._courses[course.id] = course

    async def get(self, course_id: uuid.UUID) -> Course | None:
        return self._courses.get(course_id)

    async def get_for_update(self, course_id: uuid.UUID) -> Course | None:
        return self._courses.get(course_id)

    async def list(self, *, offset: int, limit: int, search: str | None) -> list[Course]:
        return list(self._courses.values())[offset : offset + limit]

    async def count(self, *, search: str | None) -> int:
        return len(self._courses)

    async def update(self, course: Course) -> None:
        self._courses[course.id] = course

    async def delete(self, course_id: uuid.UUID) -> None:
        self._courses.pop(course_id, None)


class InMemoryEnrollmentRepository:
    def __init__(self) -> None:
        self._enrollments: dict[uuid.UUID, Enrollment] = {}

    async def add(self, enrollment: Enrollment) -> None:
        self._enrollments[enrollment.id] = enrollment

    async def exists(self, *, student_id: uuid.UUID, course_id: uuid.UUID) -> bool:
        return any(
            e.student_id == student_id and e.course_id == course_id
            for e in self._enrollments.values()
        )

    async def list_for_student(self, student_id: uuid.UUID) -> list[Enrollment]:
        return [e for e in self._enrollments.values() if e.student_id == student_id]

    async def list_for_course(self, course_id: uuid.UUID) -> list[Enrollment]:
        return [e for e in self._enrollments.values() if e.course_id == course_id]
