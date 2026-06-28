from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class CreateTeacherInput:
    first_name: str
    last_name: str
    email: str
    department: str


@dataclass(frozen=True)
class UpdateTeacherInput:
    first_name: str
    last_name: str
    email: str
    department: str


@dataclass(frozen=True)
class TeacherPage:
    items: list[TeacherView]
    total: int
    offset: int
    limit: int


@dataclass(frozen=True)
class TeacherView:
    id: uuid.UUID
    first_name: str
    last_name: str
    full_name: str
    email: str
    department: str
    is_active: bool
