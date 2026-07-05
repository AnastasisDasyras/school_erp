from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.modules.grades.application.dto import SubmitGradeInput


class SubmitGradeRequest(BaseModel):
    student_id: uuid.UUID
    course_id: uuid.UUID
    score: float = Field(..., ge=0.0, le=100.0)

    def to_input(self) -> SubmitGradeInput:
        return SubmitGradeInput(
            student_id=self.student_id,
            course_id=self.course_id,
            score=self.score,
        )


class GradeResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    course_id: uuid.UUID
    score: float
    letter: str
    version: int
