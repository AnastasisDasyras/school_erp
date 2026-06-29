from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import date

from app.modules.students.application.dto import (
    CreateStudentInput,
    StudentPage,
    StudentView,
    UpdateStudentInput,
)
from app.modules.students.application.exceptions import (
    DuplicateStudentEmailError,
    StudentNotFoundError,
)
from app.modules.students.application.ports import StudentRepository
from app.modules.students.domain.student import Student
from app.shared.cache.cache_aside import cached
from app.shared.cache.ports import Cache

_LIST_CACHE_PREFIX = "students:list:"
_LIST_CACHE_TTL_SECONDS = 30


def _to_view(student: Student) -> StudentView:
    return StudentView(
        id=student.id,
        first_name=student.first_name,
        last_name=student.last_name,
        full_name=student.full_name,
        email=student.email,
        date_of_birth=student.date_of_birth,
        enrolled_on=student.enrolled_on,
        is_active=student.is_active,
    )


def _page_to_json(page: StudentPage) -> str:
    payload = asdict(page)
    for item in payload["items"]:
        item["id"] = str(item["id"])
        item["date_of_birth"] = item["date_of_birth"].isoformat()
        item["enrolled_on"] = item["enrolled_on"].isoformat()
    return json.dumps(payload)


def _page_from_json(raw: str) -> StudentPage:
    payload = json.loads(raw)
    items = [
        StudentView(
            id=uuid.UUID(item["id"]),
            first_name=item["first_name"],
            last_name=item["last_name"],
            full_name=item["full_name"],
            email=item["email"],
            date_of_birth=date.fromisoformat(item["date_of_birth"]),
            enrolled_on=date.fromisoformat(item["enrolled_on"]),
            is_active=item["is_active"],
        )
        for item in payload["items"]
    ]
    return StudentPage(
        items=items, total=payload["total"], offset=payload["offset"], limit=payload["limit"]
    )


class StudentService:
    """Use cases for the Students bounded context.

    Depends only on the StudentRepository port — swap the adapter (Postgres,
    in-memory fake) and this class is untouched. This is what makes unit
    tests for business rules possible without a database. `cache` is
    optional: pass None (the default) to skip caching entirely, which is
    exactly what unit tests do.
    """

    def __init__(self, repository: StudentRepository, cache: Cache | None = None) -> None:
        self._repository = repository
        self._cache = cache

    async def create(self, data: CreateStudentInput) -> StudentView:
        if await self._repository.get_by_email(data.email) is not None:
            raise DuplicateStudentEmailError(data.email)

        student = Student.create(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            date_of_birth=data.date_of_birth,
        )
        await self._repository.add(student)
        await self._invalidate_list_cache()
        return _to_view(student)

    async def get(self, student_id: uuid.UUID) -> StudentView:
        student = await self._repository.get(student_id)
        if student is None:
            raise StudentNotFoundError(student_id)
        return _to_view(student)

    async def list(self, *, offset: int, limit: int, search: str | None) -> StudentPage:
        async def _load() -> StudentPage:
            students = await self._repository.list(offset=offset, limit=limit, search=search)
            total = await self._repository.count(search=search)
            return StudentPage(
                items=[_to_view(s) for s in students],
                total=total,
                offset=offset,
                limit=limit,
            )

        if self._cache is None:
            return await _load()

        key = f"{_LIST_CACHE_PREFIX}{offset}:{limit}:{search or ''}"
        return await cached(
            self._cache,
            key,
            ttl_seconds=_LIST_CACHE_TTL_SECONDS,
            loader=_load,
            to_json=_page_to_json,
            from_json=_page_from_json,
        )

    async def update(self, student_id: uuid.UUID, data: UpdateStudentInput) -> StudentView:
        student = await self._repository.get(student_id)
        if student is None:
            raise StudentNotFoundError(student_id)

        existing_with_email = await self._repository.get_by_email(data.email)
        if existing_with_email is not None and existing_with_email.id != student_id:
            raise DuplicateStudentEmailError(data.email)

        student.update_details(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            date_of_birth=data.date_of_birth,
        )

        await self._repository.update(student)
        await self._invalidate_list_cache()
        return _to_view(student)

    async def deactivate(self, student_id: uuid.UUID) -> None:
        student = await self._repository.get(student_id)
        if student is None:
            raise StudentNotFoundError(student_id)
        student.deactivate()
        await self._repository.update(student)
        await self._invalidate_list_cache()

    async def delete(self, student_id: uuid.UUID) -> None:
        student = await self._repository.get(student_id)
        if student is None:
            raise StudentNotFoundError(student_id)
        await self._repository.delete(student_id)
        await self._invalidate_list_cache()

    async def _invalidate_list_cache(self) -> None:
        if self._cache is not None:
            await self._cache.delete_prefix(_LIST_CACHE_PREFIX)
