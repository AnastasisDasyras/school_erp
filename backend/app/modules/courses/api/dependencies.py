from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.courses.application.service import CourseService
from app.modules.courses.infrastructure.repository import SqlAlchemyCourseRepository
from app.shared.database.session import get_session


def get_course_service(session: AsyncSession = Depends(get_session)) -> CourseService:
    repository = SqlAlchemyCourseRepository(session)
    return CourseService(repository)
