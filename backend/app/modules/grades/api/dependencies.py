from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.grades.application.service import GradeService
from app.modules.grades.infrastructure.repository import SqlAlchemyGradeRepository
from app.shared.database.session import get_session


def get_grade_service(session: AsyncSession = Depends(get_session)) -> GradeService:
    return GradeService(SqlAlchemyGradeRepository(session))
