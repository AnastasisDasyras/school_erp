from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class CreateStudentInput:
    first_name: str
    last_name: str
    email: str
    date_of_birth: date


@dataclass(frozen=True)
class UpdateStudentInput:
    first_name: str
    last_name: str
    email: str
    date_of_birth: date


@dataclass(frozen=True)
class StudentPage:
    items: list[StudentView]
    total: int
    offset: int
    limit: int


@dataclass(frozen=True)
class StudentView:
    id: uuid.UUID
    first_name: str
    last_name: str
    full_name: str
    email: str
    date_of_birth: date
    enrolled_on: date
    is_active: bool
