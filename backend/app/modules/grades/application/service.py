from __future__ import annotations

import uuid

import structlog

from app.modules.grades.application.dto import GradeView, SubmitGradeInput
from app.modules.grades.application.exceptions import GradeConflictError, GradeNotFoundError
from app.modules.grades.application.ports import GradeRepository
from app.modules.grades.domain.grade import Grade, StaleGradeError

log = structlog.get_logger("grades.service")

_MAX_OPTIMISTIC_RETRIES = 3


def _to_view(grade: Grade) -> GradeView:
    return GradeView(
        id=grade.id,
        student_id=grade.student_id,
        course_id=grade.course_id,
        score=grade.score,
        letter=grade.letter,
        version=grade.version,
    )


class GradeService:
    """Grades use-case service.

    submit() demonstrates optimistic locking:
    - If no grade exists yet: create and insert.
    - If a grade already exists: load it, update the score, and call
      repository.update(). The repository issues:
        UPDATE grades SET score=..., letter=..., version=version+1
        WHERE id=? AND version=?   ← the lock check
      If another writer already bumped the version, UPDATE affects 0 rows
      and the repository raises StaleGradeError. We reload from DB and
      retry up to _MAX_OPTIMISTIC_RETRIES times.

    This is the right pattern for grade corrections: they're rare and short,
    so the cost of an occasional retry is far cheaper than holding a
    SELECT ... FOR UPDATE across a network round-trip.
    """

    def __init__(self, grades: GradeRepository) -> None:
        self._grades = grades

    async def submit(self, data: SubmitGradeInput) -> GradeView:
        existing = await self._grades.get_for_student_course(data.student_id, data.course_id)

        if existing is None:
            grade = Grade.create(
                student_id=data.student_id,
                course_id=data.course_id,
                score=data.score,
            )
            await self._grades.add(grade)
            return _to_view(grade)

        for attempt in range(1, _MAX_OPTIMISTIC_RETRIES + 1):
            existing.update_score(data.score)
            try:
                await self._grades.update(existing)
                return _to_view(existing)
            except StaleGradeError:
                log.warning(
                    "grade_optimistic_lock_retry",
                    attempt=attempt,
                    grade_id=str(existing.id),
                )
                if attempt == _MAX_OPTIMISTIC_RETRIES:
                    raise GradeConflictError() from None
                reloaded = await self._grades.get(existing.id)
                if reloaded is None:
                    raise GradeNotFoundError(existing.id) from None
                existing = reloaded

        raise GradeConflictError()  # unreachable, satisfies type checker

    async def get(self, grade_id: uuid.UUID) -> GradeView:
        grade = await self._grades.get(grade_id)
        if grade is None:
            raise GradeNotFoundError(grade_id)
        return _to_view(grade)

    async def list_for_student(self, student_id: uuid.UUID) -> list[GradeView]:
        return [_to_view(g) for g in await self._grades.list_for_student(student_id)]

    async def list_for_course(self, course_id: uuid.UUID) -> list[GradeView]:
        return [_to_view(g) for g in await self._grades.list_for_course(course_id)]
