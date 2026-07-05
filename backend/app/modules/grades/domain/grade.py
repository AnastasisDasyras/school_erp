from __future__ import annotations

import uuid
from dataclasses import dataclass


class InvalidGradeError(ValueError):
    pass


class StaleGradeError(Exception):
    """Raised when an optimistic-lock version conflict is detected.

    The caller should reload the grade and retry — see GradeService.submit().
    """


@dataclass
class Grade:
    """Domain entity for a student's grade on a course.

    `version` is the optimistic-lock counter. Every time a grade is updated
    the DB increments it. If two writers load version=1 and both try to save,
    the second UPDATE finds version=2 (already bumped by the first) and
    updates 0 rows — the repository raises StaleGradeError and the service
    retries from a fresh read.

    This is the correct pattern for infrequently-contended writes (grade
    corrections) where you'd rather retry than hold a lock across a round-trip.
    """

    id: uuid.UUID
    student_id: uuid.UUID
    course_id: uuid.UUID
    score: float          # 0.0 – 100.0
    letter: str           # A / B / C / D / F
    version: int = 0      # optimistic lock counter

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not (0.0 <= self.score <= 100.0):
            raise InvalidGradeError(f"score must be 0–100, got {self.score}")
        if self.letter not in {"A", "B", "C", "D", "F"}:
            raise InvalidGradeError(f"letter must be A/B/C/D/F, got {self.letter!r}")

    @classmethod
    def create(
        cls,
        *,
        student_id: uuid.UUID,
        course_id: uuid.UUID,
        score: float,
    ) -> Grade:
        return cls(
            id=uuid.uuid4(),
            student_id=student_id,
            course_id=course_id,
            score=score,
            letter=_score_to_letter(score),
        )

    def update_score(self, score: float) -> None:
        self.score = score
        self.letter = _score_to_letter(score)
        self._validate()


def _score_to_letter(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"
