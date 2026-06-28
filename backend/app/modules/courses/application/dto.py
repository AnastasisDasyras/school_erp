from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class CreateCourseInput:
    title: str
    teacher_id: uuid.UUID
    capacity: int


@dataclass(frozen=True)
class UpdateCourseInput:
    title: str
    teacher_id: uuid.UUID
    capacity: int


@dataclass(frozen=True)
class CoursePage:
    items: list[CourseView]
    total: int
    offset: int
    limit: int


@dataclass(frozen=True)
class CourseView:
    id: uuid.UUID
    title: str
    teacher_id: uuid.UUID
    capacity: int
    available_seats: int
    is_active: bool
