from __future__ import annotations

import uuid

from app.modules.courses.application.dto import (
    CoursePage,
    CourseView,
    CreateCourseInput,
    UpdateCourseInput,
)
from app.modules.courses.application.exceptions import CourseNotFoundError
from app.modules.courses.application.ports import CourseRepository
from app.modules.courses.domain.course import Course


def _to_view(course: Course) -> CourseView:
    return CourseView(
        id=course.id,
        title=course.title,
        teacher_id=course.teacher_id,
        capacity=course.capacity,
        available_seats=course.available_seats,
        is_active=course.is_active,
    )


class CourseService:
    def __init__(self, repository: CourseRepository) -> None:
        self._repository = repository

    async def create(self, data: CreateCourseInput) -> CourseView:
        course = Course.create(
            title=data.title, teacher_id=data.teacher_id, capacity=data.capacity
        )
        await self._repository.add(course)
        return _to_view(course)

    async def get(self, course_id: uuid.UUID) -> CourseView:
        course = await self._repository.get(course_id)
        if course is None:
            raise CourseNotFoundError(course_id)
        return _to_view(course)

    async def list(self, *, offset: int, limit: int, search: str | None) -> CoursePage:
        courses = await self._repository.list(offset=offset, limit=limit, search=search)
        total = await self._repository.count(search=search)
        return CoursePage(
            items=[_to_view(c) for c in courses],
            total=total,
            offset=offset,
            limit=limit,
        )

    async def update(self, course_id: uuid.UUID, data: UpdateCourseInput) -> CourseView:
        course = await self._repository.get(course_id)
        if course is None:
            raise CourseNotFoundError(course_id)
        course.update_details(
            title=data.title, teacher_id=data.teacher_id, capacity=data.capacity
        )
        await self._repository.update(course)
        return _to_view(course)

    async def deactivate(self, course_id: uuid.UUID) -> None:
        course = await self._repository.get(course_id)
        if course is None:
            raise CourseNotFoundError(course_id)
        course.deactivate()
        await self._repository.update(course)

    async def delete(self, course_id: uuid.UUID) -> None:
        course = await self._repository.get(course_id)
        if course is None:
            raise CourseNotFoundError(course_id)
        await self._repository.delete(course_id)
