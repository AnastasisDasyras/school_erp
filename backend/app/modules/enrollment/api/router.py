from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.current_user import CurrentUser, get_current_user, require_role
from app.modules.auth.domain.user import Role
from app.modules.courses.application.exceptions import CourseNotFoundError
from app.modules.enrollment.api.dependencies import get_enrollment_service
from app.modules.enrollment.api.schemas import EnrollmentResponse, EnrollRequest
from app.modules.enrollment.application.dto import EnrollInput
from app.modules.enrollment.application.exceptions import AlreadyEnrolledError, CourseFullError
from app.modules.enrollment.application.service import EnrollmentService
from app.modules.enrollment.infrastructure.repository import SqlAlchemyEnrollmentRepository
from app.shared.database.session import get_session

router = APIRouter(prefix="/enrollments", tags=["enrollment"])


@router.post("", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def enroll(
    body: EnrollRequest,
    service: EnrollmentService = Depends(get_enrollment_service),
    session: AsyncSession = Depends(get_session),
    _user: CurrentUser = Depends(require_role(Role.ADMIN, Role.STUDENT)),
) -> EnrollmentResponse:
    """Single transaction: insert enrollment + decrement course seats.

    On AlreadyEnrolledError/CourseFullError we re-raise as an HTTP error and
    let FastAPI's exception handling return without calling commit — the
    AsyncSession context manager (get_session) rolls back automatically on
    exit if commit was never called, so a failed enrollment leaves the course
    seat count untouched. That's the rollback demo: try enrolling into a
    full course and `available_seats` never moves.
    """
    try:
        view = await service.enroll(
            EnrollInput(student_id=body.student_id, course_id=body.course_id)
        )
    except AlreadyEnrolledError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "student already enrolled in course") from exc
    except CourseFullError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "course has no available seats") from exc
    except CourseNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "course not found") from exc
    await session.commit()
    return EnrollmentResponse.from_view(view)


@router.get("/students/{student_id}", response_model=list[EnrollmentResponse])
async def list_enrollments_for_student(
    student_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _user: CurrentUser = Depends(get_current_user),
) -> list[EnrollmentResponse]:
    repository = SqlAlchemyEnrollmentRepository(session)
    enrollments = await repository.list_for_student(student_id)
    return [
        EnrollmentResponse(
            id=e.id, student_id=e.student_id, course_id=e.course_id, enrolled_on=e.enrolled_on
        )
        for e in enrollments
    ]


@router.get("/courses/{course_id}", response_model=list[EnrollmentResponse])
async def list_enrollments_for_course(
    course_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _user: CurrentUser = Depends(get_current_user),
) -> list[EnrollmentResponse]:
    repository = SqlAlchemyEnrollmentRepository(session)
    enrollments = await repository.list_for_course(course_id)
    return [
        EnrollmentResponse(
            id=e.id, student_id=e.student_id, course_id=e.course_id, enrolled_on=e.enrolled_on
        )
        for e in enrollments
    ]
