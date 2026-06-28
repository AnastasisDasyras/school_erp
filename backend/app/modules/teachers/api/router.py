from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.current_user import CurrentUser, get_current_user, require_role
from app.modules.auth.domain.user import Role
from app.modules.teachers.api.dependencies import get_teacher_service
from app.modules.teachers.api.schemas import (
    TeacherCreateRequest,
    TeacherListResponse,
    TeacherResponse,
    TeacherUpdateRequest,
)
from app.modules.teachers.application.dto import CreateTeacherInput, UpdateTeacherInput
from app.modules.teachers.application.exceptions import (
    DuplicateTeacherEmailError,
    TeacherNotFoundError,
)
from app.modules.teachers.application.service import TeacherService
from app.shared.database.session import get_session

router = APIRouter(prefix="/teachers", tags=["teachers"])


@router.post("", response_model=TeacherResponse, status_code=status.HTTP_201_CREATED)
async def create_teacher(
    body: TeacherCreateRequest,
    service: TeacherService = Depends(get_teacher_service),
    session: AsyncSession = Depends(get_session),
    _user: CurrentUser = Depends(require_role(Role.ADMIN)),
) -> TeacherResponse:
    try:
        view = await service.create(
            CreateTeacherInput(
                first_name=body.first_name,
                last_name=body.last_name,
                email=body.email,
                department=body.department,
            )
        )
    except DuplicateTeacherEmailError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, f"email already in use: {exc}") from exc
    await session.commit()
    return TeacherResponse.from_view(view)


@router.get("", response_model=TeacherListResponse)
async def list_teachers(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=200),
    service: TeacherService = Depends(get_teacher_service),
    _user: CurrentUser = Depends(get_current_user),
) -> TeacherListResponse:
    page = await service.list(offset=offset, limit=limit, search=search)
    return TeacherListResponse.from_page(page)


@router.get("/{teacher_id}", response_model=TeacherResponse)
async def get_teacher(
    teacher_id: uuid.UUID,
    service: TeacherService = Depends(get_teacher_service),
    _user: CurrentUser = Depends(get_current_user),
) -> TeacherResponse:
    try:
        view = await service.get(teacher_id)
    except TeacherNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "teacher not found") from exc
    return TeacherResponse.from_view(view)


@router.put("/{teacher_id}", response_model=TeacherResponse)
async def update_teacher(
    teacher_id: uuid.UUID,
    body: TeacherUpdateRequest,
    service: TeacherService = Depends(get_teacher_service),
    session: AsyncSession = Depends(get_session),
    _user: CurrentUser = Depends(require_role(Role.ADMIN)),
) -> TeacherResponse:
    try:
        view = await service.update(
            teacher_id,
            UpdateTeacherInput(
                first_name=body.first_name,
                last_name=body.last_name,
                email=body.email,
                department=body.department,
            ),
        )
    except TeacherNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "teacher not found") from exc
    except DuplicateTeacherEmailError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, f"email already in use: {exc}") from exc
    await session.commit()
    return TeacherResponse.from_view(view)


@router.delete("/{teacher_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_teacher(
    teacher_id: uuid.UUID,
    service: TeacherService = Depends(get_teacher_service),
    session: AsyncSession = Depends(get_session),
    _user: CurrentUser = Depends(require_role(Role.ADMIN)),
) -> None:
    try:
        await service.delete(teacher_id)
    except TeacherNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "teacher not found") from exc
    await session.commit()
