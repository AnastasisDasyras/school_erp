from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.current_user import CurrentUser, get_current_user
from app.modules.students.api.dependencies import get_student_service
from app.modules.students.api.schemas import (
    StudentCreateRequest,
    StudentListResponse,
    StudentResponse,
    StudentUpdateRequest,
)
from app.modules.students.application.cached_service import CachedStudentService
from app.modules.students.application.dto import CreateStudentInput, UpdateStudentInput
from app.modules.students.application.exceptions import (
    DuplicateStudentEmailError,
    StudentNotFoundError,
)
from app.shared.database.session import get_session

router = APIRouter(prefix="/students", tags=["students"])


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def create_student(
    body: StudentCreateRequest,
    service: CachedStudentService = Depends(get_student_service),
    session: AsyncSession = Depends(get_session),
    _user: CurrentUser = Depends(get_current_user),
) -> StudentResponse:
    try:
        view = await service.create(
            CreateStudentInput(
                first_name=body.first_name,
                last_name=body.last_name,
                email=body.email,
                date_of_birth=body.date_of_birth,
            )
        )
    except DuplicateStudentEmailError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, f"email already in use: {exc}") from exc
    await session.commit()
    return StudentResponse.from_view(view)


@router.get("", response_model=StudentListResponse)
async def list_students(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=200),
    service: CachedStudentService = Depends(get_student_service),
    _user: CurrentUser = Depends(get_current_user),
) -> StudentListResponse:
    page = await service.list(offset=offset, limit=limit, search=search)
    return StudentListResponse.from_page(page)


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: uuid.UUID,
    service: CachedStudentService = Depends(get_student_service),
    _user: CurrentUser = Depends(get_current_user),
) -> StudentResponse:
    try:
        view = await service.get(student_id)
    except StudentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "student not found") from exc
    return StudentResponse.from_view(view)


@router.put("/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: uuid.UUID,
    body: StudentUpdateRequest,
    service: CachedStudentService = Depends(get_student_service),
    session: AsyncSession = Depends(get_session),
    _user: CurrentUser = Depends(get_current_user),
) -> StudentResponse:
    try:
        view = await service.update(
            student_id,
            UpdateStudentInput(
                first_name=body.first_name,
                last_name=body.last_name,
                email=body.email,
                date_of_birth=body.date_of_birth,
            ),
        )
    except StudentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "student not found") from exc
    except DuplicateStudentEmailError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, f"email already in use: {exc}") from exc
    await session.commit()
    return StudentResponse.from_view(view)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(
    student_id: uuid.UUID,
    service: CachedStudentService = Depends(get_student_service),
    session: AsyncSession = Depends(get_session),
    _user: CurrentUser = Depends(get_current_user),
) -> None:
    try:
        await service.delete(student_id)
    except StudentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "student not found") from exc
    await session.commit()
