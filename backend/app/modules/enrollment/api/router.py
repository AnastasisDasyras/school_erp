from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.current_user import CurrentUser, get_current_user, require_role
from app.modules.auth.domain.user import Role
from app.modules.courses.application.exceptions import CourseNotFoundError
from app.modules.courses.application.service import LIST_CACHE_PREFIX as COURSES_LIST_CACHE_PREFIX
from app.modules.enrollment.api.dependencies import get_enrollment_service, get_idempotency_store
from app.modules.enrollment.api.schemas import EnrollmentResponse, EnrollRequest
from app.modules.enrollment.application.dto import EnrollInput
from app.modules.enrollment.application.exceptions import AlreadyEnrolledError, CourseFullError
from app.modules.enrollment.application.service import EnrollmentService
from app.modules.enrollment.infrastructure.repository import SqlAlchemyEnrollmentRepository
from app.shared.cache.client import get_redis
from app.shared.cache.redis_cache import RedisCache
from app.shared.database.session import get_session
from app.shared.idempotency.ports import StoredResponse
from app.shared.idempotency.repository import SqlAlchemyIdempotencyStore

router = APIRouter(prefix="/enrollments", tags=["enrollment"])

_IDEMPOTENCY_ENDPOINT = "POST /enrollments"


@router.post("", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def enroll(
    body: EnrollRequest,
    response: Response,
    service: EnrollmentService = Depends(get_enrollment_service),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    idempotency_store: SqlAlchemyIdempotencyStore = Depends(get_idempotency_store),
    user: CurrentUser = Depends(require_role(Role.ADMIN, Role.STUDENT)),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> EnrollmentResponse:
    """Single transaction: insert enrollment + decrement course seats.

    On AlreadyEnrolledError/CourseFullError we re-raise as an HTTP error and
    let FastAPI's exception handling return without calling commit — the
    AsyncSession context manager (get_session) rolls back automatically on
    exit if commit was never called, so a failed enrollment leaves the course
    seat count untouched. That's the rollback demo: try enrolling into a
    full course and `available_seats` never moves.

    The cached courses list is invalidated *after* commit, not inside the
    service — invalidating before a commit that might still roll back would
    let a reader observe a "fresh" cache miss, re-query Postgres, and cache
    a seat count that a moment later turns out to have never actually changed.

    Idempotency: if the client sends an `Idempotency-Key` header, a retry
    with the same key replays the stored response instead of re-running
    `enroll()` — without this, a client that never saw the first response
    (network blip) could retry and either get a confusing 409
    "already enrolled" or, for an operation without that natural guard,
    silently double the side effect. The stored response is saved in the
    *same* transaction as the enrollment write (see SqlAlchemyIdempotencyStore)
    so a rollback undoes the idempotency record along with the enrollment.
    """
    if idempotency_key is not None:
        cached_response = await idempotency_store.get(
            key=idempotency_key, endpoint=_IDEMPOTENCY_ENDPOINT
        )
        if cached_response is not None:
            response.status_code = cached_response.status_code
            response.headers["Idempotency-Replayed"] = "true"
            return EnrollmentResponse.model_validate_json(cached_response.body)

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

    enrollment_response = EnrollmentResponse.from_view(view)

    if idempotency_key is not None:
        await idempotency_store.save(
            key=idempotency_key,
            endpoint=_IDEMPOTENCY_ENDPOINT,
            user_id=user.id,
            response=StoredResponse(
                status_code=status.HTTP_201_CREATED,
                body=enrollment_response.model_dump_json(),
            ),
        )

    await session.commit()
    await RedisCache(redis).delete_prefix(COURSES_LIST_CACHE_PREFIX)
    return enrollment_response


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
