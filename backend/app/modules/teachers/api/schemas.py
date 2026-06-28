from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field

from app.modules.teachers.application.dto import TeacherPage, TeacherView


class TeacherCreateRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    department: str = Field(min_length=1, max_length=100)


class TeacherUpdateRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    department: str = Field(min_length=1, max_length=100)


class TeacherResponse(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    full_name: str
    email: str
    department: str
    is_active: bool

    @classmethod
    def from_view(cls, view: TeacherView) -> TeacherResponse:
        return cls(**view.__dict__)


class TeacherListResponse(BaseModel):
    items: list[TeacherResponse]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_page(cls, page: TeacherPage) -> TeacherListResponse:
        return cls(
            items=[TeacherResponse.from_view(v) for v in page.items],
            total=page.total,
            offset=page.offset,
            limit=page.limit,
        )
