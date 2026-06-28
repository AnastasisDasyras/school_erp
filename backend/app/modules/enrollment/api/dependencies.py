from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.courses.infrastructure.repository import SqlAlchemyCourseRepository
from app.modules.enrollment.application.service import EnrollmentService
from app.modules.enrollment.infrastructure.repository import SqlAlchemyEnrollmentRepository
from app.shared.database.session import get_session


def get_enrollment_service(session: AsyncSession = Depends(get_session)) -> EnrollmentService:
    """Wires both repositories onto the *same* session so the enrollment
    insert and the course seat decrement share one DB transaction."""
    enrollments = SqlAlchemyEnrollmentRepository(session)
    courses = SqlAlchemyCourseRepository(session)
    return EnrollmentService(enrollments, courses)
