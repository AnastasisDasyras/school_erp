from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.teachers.application.service import TeacherService
from app.modules.teachers.infrastructure.repository import SqlAlchemyTeacherRepository
from app.shared.database.session import get_session


def get_teacher_service(session: AsyncSession = Depends(get_session)) -> TeacherService:
    repository = SqlAlchemyTeacherRepository(session)
    return TeacherService(repository)
