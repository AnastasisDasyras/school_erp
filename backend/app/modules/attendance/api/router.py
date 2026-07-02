from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.attendance.api.dependencies import get_attendance_service, get_idempotency_store
from app.modules.attendance.api.schemas import AttendanceResponse, RecordAttendanceRequest
from app.modules.attendance.application.dto import RecordAttendanceInput
from app.modules.attendance.application.exceptions import AttendanceAlreadyRecordedError
from app.modules.attendance.application.service import AttendanceService
from app.modules.auth.current_user import CurrentUser, require_role
from app.modules.auth.domain.user import Role
from app.shared.database.session import get_session
from app.shared.idempotency.ports import StoredResponse
from app.shared.idempotency.repository import SqlAlchemyIdempotencyStore

router = APIRouter(prefix="/attendance", tags=["attendance"])

_IDEMPOTENCY_ENDPOINT = "POST /attendance"


@router.post("", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
async def record_attendance(
    body: RecordAttendanceRequest,
    response: Response,
    service: AttendanceService = Depends(get_attendance_service),
    session: AsyncSession = Depends(get_session),
    idempotency_store: SqlAlchemyIdempotencyStore = Depends(get_idempotency_store),
    user: CurrentUser = Depends(require_role(Role.ADMIN, Role.TEACHER)),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> AttendanceResponse:
    """Records attendance and writes an `AttendanceRecorded` outbox row in
    the same transaction (ADR 0008) — a separate relay process publishes it
    to SNS afterward; this endpoint never talks to SNS/boto3 itself.

    Idempotency matters more here than on most endpoints: once SNS/SQS
    delivery is in play (at-least-once, ADR 0008), a client retry isn't the
    only thing that can cause a duplicate-looking request — so the same
    `Idempotency-Key` header mechanism from ADR 0007 applies here unchanged.
    """
    if idempotency_key is not None:
        cached_response = await idempotency_store.get(
            key=idempotency_key, endpoint=_IDEMPOTENCY_ENDPOINT
        )
        if cached_response is not None:
            response.status_code = cached_response.status_code
            response.headers["Idempotency-Replayed"] = "true"
            return AttendanceResponse.model_validate_json(cached_response.body)

    try:
        view = await service.record(
            RecordAttendanceInput(
                student_id=body.student_id, course_id=body.course_id, status=body.status
            )
        )
    except AttendanceAlreadyRecordedError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "attendance already recorded for this student/course/day"
        ) from exc

    attendance_response = AttendanceResponse.from_view(view)

    if idempotency_key is not None:
        await idempotency_store.save(
            key=idempotency_key,
            endpoint=_IDEMPOTENCY_ENDPOINT,
            user_id=user.id,
            response=StoredResponse(
                status_code=status.HTTP_201_CREATED,
                body=attendance_response.model_dump_json(),
            ),
        )

    await session.commit()
    return attendance_response
