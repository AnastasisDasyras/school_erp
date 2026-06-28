from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.students.application.service import StudentService
from app.modules.students.infrastructure.repository import SqlAlchemyStudentRepository
from app.shared.database.session import get_session


def get_student_service(session: AsyncSession = Depends(get_session)) -> StudentService:
    repository = SqlAlchemyStudentRepository(session)
    return StudentService(repository)
