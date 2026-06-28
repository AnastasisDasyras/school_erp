from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class EnrollInput:
    student_id: uuid.UUID
    course_id: uuid.UUID


@dataclass(frozen=True)
class EnrollmentView:
    id: uuid.UUID
    student_id: uuid.UUID
    course_id: uuid.UUID
    enrolled_on: date
