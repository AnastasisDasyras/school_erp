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
from app.modules.students.application.service import StudentService
from app.shared.cache.cache_aside import cached
from app.shared.cache.ports import Cache

_LIST_CACHE_PREFIX = "students:list:"
_LIST_CACHE_TTL_SECONDS = 30


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


class CachedStudentService:
    """Caching decorator around StudentService.

    Caching is a cross-cutting concern, so it lives here rather than in the
    business-logic service. Reads (`list`) go through cache-aside; writes
    delegate and then invalidate the list cache. The wrapped service stays a
    pure unit-testable use-case class, and these cache tests need only a fake
    Cache plus a fake inner service — no database, no Redis.
    """

    def __init__(self, inner: StudentService, cache: Cache) -> None:
        self._inner = inner
        self._cache = cache

    async def get(self, student_id: uuid.UUID) -> StudentView:
        return await self._inner.get(student_id)

    async def list(self, *, offset: int, limit: int, search: str | None) -> StudentPage:
        key = f"{_LIST_CACHE_PREFIX}{offset}:{limit}:{search or ''}"
        return await cached(
            self._cache,
            key,
            ttl_seconds=_LIST_CACHE_TTL_SECONDS,
            loader=lambda: self._inner.list(offset=offset, limit=limit, search=search),
            to_json=_page_to_json,
            from_json=_page_from_json,
        )

    async def create(self, data: CreateStudentInput) -> StudentView:
        result = await self._inner.create(data)
        await self._invalidate_list_cache()
        return result

    async def update(self, student_id: uuid.UUID, data: UpdateStudentInput) -> StudentView:
        result = await self._inner.update(student_id, data)
        await self._invalidate_list_cache()
        return result

    async def deactivate(self, student_id: uuid.UUID) -> None:
        await self._inner.deactivate(student_id)
        await self._invalidate_list_cache()

    async def delete(self, student_id: uuid.UUID) -> None:
        await self._inner.delete(student_id)
        await self._invalidate_list_cache()

    async def _invalidate_list_cache(self) -> None:
        await self._cache.delete_prefix(_LIST_CACHE_PREFIX)
