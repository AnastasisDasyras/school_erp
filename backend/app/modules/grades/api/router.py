from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.current_user import require_role
from app.modules.grades.api.dependencies import get_grade_service
from app.modules.grades.api.schemas import GradeResponse, SubmitGradeRequest
from app.modules.grades.application.exceptions import GradeConflictError, GradeNotFoundError
from app.modules.grades.application.service import GradeService
from app.modules.grades.domain.grade import InvalidGradeError
from app.shared.database.session import get_session

router = APIRouter(prefix="/grades", tags=["grades"])


@router.post("", response_model=GradeResponse, status_code=status.HTTP_201_CREATED)
async def submit_grade(
    body: SubmitGradeRequest,
    svc: GradeService = Depends(get_grade_service),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_role("teacher", "admin")),
) -> GradeResponse:
    try:
        view = await svc.submit(body.to_input())
    except InvalidGradeError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except GradeConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    await session.commit()
    return GradeResponse(**view.__dict__)


@router.get("/{grade_id}", response_model=GradeResponse)
async def get_grade(
    grade_id: uuid.UUID,
    svc: GradeService = Depends(get_grade_service),
) -> GradeResponse:
    try:
        view = await svc.get(grade_id)
    except GradeNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return GradeResponse(**view.__dict__)


@router.get("/student/{student_id}", response_model=list[GradeResponse])
async def list_for_student(
    student_id: uuid.UUID,
    svc: GradeService = Depends(get_grade_service),
) -> list[GradeResponse]:
    views = await svc.list_for_student(student_id)
    return [GradeResponse(**v.__dict__) for v in views]


@router.get("/course/{course_id}", response_model=list[GradeResponse])
async def list_for_course(
    course_id: uuid.UUID,
    svc: GradeService = Depends(get_grade_service),
) -> list[GradeResponse]:
    views = await svc.list_for_course(course_id)
    return [GradeResponse(**v.__dict__) for v in views]
