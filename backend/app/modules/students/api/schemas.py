from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, EmailStr, Field

from app.modules.students.application.dto import StudentPage, StudentView


class StudentCreateRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    date_of_birth: date


class StudentUpdateRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    date_of_birth: date


class StudentResponse(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    full_name: str
    email: str
    date_of_birth: date
    enrolled_on: date
    is_active: bool

    @classmethod
    def from_view(cls, view: StudentView) -> StudentResponse:
        return cls(**view.__dict__)


class StudentListResponse(BaseModel):
    items: list[StudentResponse]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_page(cls, page: StudentPage) -> StudentListResponse:
        return cls(
            items=[StudentResponse.from_view(v) for v in page.items],
            total=page.total,
            offset=page.offset,
            limit=page.limit,
        )
