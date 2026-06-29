from __future__ import annotations

import json
import uuid
from dataclasses import asdict

from app.modules.courses.application.dto import (
    CoursePage,
    CourseView,
    CreateCourseInput,
    UpdateCourseInput,
)
from app.modules.courses.application.exceptions import CourseNotFoundError
from app.modules.courses.application.ports import CourseRepository
from app.modules.courses.domain.course import Course
from app.shared.cache.cache_aside import cached
from app.shared.cache.ports import Cache

LIST_CACHE_PREFIX = "courses:list:"
_LIST_CACHE_TTL_SECONDS = 30


def _to_view(course: Course) -> CourseView:
    return CourseView(
        id=course.id,
        title=course.title,
        teacher_id=course.teacher_id,
        capacity=course.capacity,
        available_seats=course.available_seats,
        is_active=course.is_active,
    )


def _page_to_json(page: CoursePage) -> str:
    payload = asdict(page)
    for item in payload["items"]:
        item["id"] = str(item["id"])
        item["teacher_id"] = str(item["teacher_id"])
    return json.dumps(payload)


def _page_from_json(raw: str) -> CoursePage:
    payload = json.loads(raw)
    items = [
        CourseView(
            **{**item, "id": uuid.UUID(item["id"]), "teacher_id": uuid.UUID(item["teacher_id"])}
        )
        for item in payload["items"]
    ]
    return CoursePage(
        items=items, total=payload["total"], offset=payload["offset"], limit=payload["limit"]
    )


class CourseService:
    """`LIST_CACHE_PREFIX` is exported (not prefixed `_`) because Enrollment
    also mutates a course's `available_seats` directly (ADR 0004) and must
    invalidate this same cache — otherwise a cached course list would show a
    stale seat count for up to the TTL after an enrollment."""

    def __init__(self, repository: CourseRepository, cache: Cache) -> None:
        self._repository = repository
        self._cache = cache

    async def create(self, data: CreateCourseInput) -> CourseView:
        course = Course.create(
            title=data.title, teacher_id=data.teacher_id, capacity=data.capacity
        )
        await self._repository.add(course)
        await self._invalidate_list_cache()
        return _to_view(course)

    async def get(self, course_id: uuid.UUID) -> CourseView:
        course = await self._repository.get(course_id)
        if course is None:
            raise CourseNotFoundError(course_id)
        return _to_view(course)

    async def list(self, *, offset: int, limit: int, search: str | None) -> CoursePage:
        async def _load() -> CoursePage:
            courses = await self._repository.list(offset=offset, limit=limit, search=search)
            total = await self._repository.count(search=search)
            return CoursePage(
                items=[_to_view(c) for c in courses],
                total=total,
                offset=offset,
                limit=limit,
            )

        key = f"{LIST_CACHE_PREFIX}{offset}:{limit}:{search or ''}"
        return await cached(
            self._cache,
            key,
            ttl_seconds=_LIST_CACHE_TTL_SECONDS,
            loader=_load,
            to_json=_page_to_json,
            from_json=_page_from_json,
        )

    async def update(self, course_id: uuid.UUID, data: UpdateCourseInput) -> CourseView:
        course = await self._repository.get(course_id)
        if course is None:
            raise CourseNotFoundError(course_id)
        course.update_details(
            title=data.title, teacher_id=data.teacher_id, capacity=data.capacity
        )
        await self._repository.update(course)
        await self._invalidate_list_cache()
        return _to_view(course)

    async def deactivate(self, course_id: uuid.UUID) -> None:
        course = await self._repository.get(course_id)
        if course is None:
            raise CourseNotFoundError(course_id)
        course.deactivate()
        await self._repository.update(course)
        await self._invalidate_list_cache()

    async def delete(self, course_id: uuid.UUID) -> None:
        course = await self._repository.get(course_id)
        if course is None:
            raise CourseNotFoundError(course_id)
        await self._repository.delete(course_id)
        await self._invalidate_list_cache()

    async def _invalidate_list_cache(self) -> None:
        await self._cache.delete_prefix(LIST_CACHE_PREFIX)
