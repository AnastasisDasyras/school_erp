from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel

from app.modules.enrollment.application.dto import EnrollmentView


class EnrollRequest(BaseModel):
    student_id: uuid.UUID
    course_id: uuid.UUID


class EnrollmentResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    course_id: uuid.UUID
    enrolled_on: date

    @classmethod
    def from_view(cls, view: EnrollmentView) -> EnrollmentResponse:
        return cls(**view.__dict__)
