from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.grades.domain.grade import Grade, StaleGradeError
from app.modules.grades.infrastructure.orm import GradeModel


def _to_domain(row: GradeModel) -> Grade:
    return Grade(
        id=row.id,
        student_id=row.student_id,
        course_id=row.course_id,
        score=row.score,
        letter=row.letter,
        version=row.version,
    )


class SqlAlchemyGradeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, grade_id: uuid.UUID) -> Grade | None:
        # populate_existing forces a fresh DB read that overwrites any stale
        # copy in the identity map. This is what makes the optimistic-lock
        # retry work: after a StaleGradeError the service reloads via get(),
        # and it MUST see the concurrent writer's committed version bump rather
        # than the cached row it originally loaded — otherwise every retry
        # re-issues WHERE version=<stale> and can never succeed.
        stmt = (
            select(GradeModel)
            .where(GradeModel.id == grade_id)
            .execution_options(populate_existing=True)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_domain(row) if row else None

    async def get_for_student_course(
        self, student_id: uuid.UUID, course_id: uuid.UUID
    ) -> Grade | None:
        stmt = select(GradeModel).where(
            GradeModel.student_id == student_id,
            GradeModel.course_id == course_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_domain(row) if row else None

    async def list_for_student(self, student_id: uuid.UUID) -> list[Grade]:
        stmt = select(GradeModel).where(GradeModel.student_id == student_id)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]

    async def list_for_course(self, course_id: uuid.UUID) -> list[Grade]:
        stmt = select(GradeModel).where(GradeModel.course_id == course_id)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]

    async def add(self, grade: Grade) -> None:
        self._session.add(
            GradeModel(
                id=grade.id,
                student_id=grade.student_id,
                course_id=grade.course_id,
                score=grade.score,
                letter=grade.letter,
                version=grade.version,
            )
        )

    async def update(self, grade: Grade) -> None:
        """Optimistic-lock UPDATE: only succeeds if version in DB matches what we read.

        The WHERE id=? AND version=? is the lock check. If another writer
        already committed a version bump, rowcount == 0 → StaleGradeError.
        The service catches StaleGradeError and retries from a fresh DB read.
        """
        stmt = (
            update(GradeModel)
            .where(GradeModel.id == grade.id, GradeModel.version == grade.version)
            .values(
                score=grade.score,
                letter=grade.letter,
                version=grade.version + 1,
            )
        )
        result = await self._session.execute(stmt)
        if result.rowcount == 0:
            raise StaleGradeError(
                f"Grade {grade.id} was modified concurrently (version={grade.version})"
            )
        grade.version += 1
