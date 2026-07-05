from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class SubmitGradeInput:
    student_id: uuid.UUID
    course_id: uuid.UUID
    score: float


@dataclass(frozen=True)
class GradeView:
    id: uuid.UUID
    student_id: uuid.UUID
    course_id: uuid.UUID
    score: float
    letter: str
    version: int
