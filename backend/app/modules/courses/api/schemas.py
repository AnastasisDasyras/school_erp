from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.modules.courses.application.dto import CoursePage, CourseView


class CourseCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    teacher_id: uuid.UUID
    capacity: int = Field(gt=0)


class CourseUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    teacher_id: uuid.UUID
    capacity: int = Field(gt=0)


class CourseResponse(BaseModel):
    id: uuid.UUID
    title: str
    teacher_id: uuid.UUID
    capacity: int
    available_seats: int
    is_active: bool

    @classmethod
    def from_view(cls, view: CourseView) -> CourseResponse:
        return cls(**view.__dict__)


class CourseListResponse(BaseModel):
    items: list[CourseResponse]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_page(cls, page: CoursePage) -> CourseListResponse:
        return cls(
            items=[CourseResponse.from_view(v) for v in page.items],
            total=page.total,
            offset=page.offset,
            limit=page.limit,
        )
