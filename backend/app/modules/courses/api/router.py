from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.current_user import CurrentUser, get_current_user, require_role
from app.modules.auth.domain.user import Role
from app.modules.courses.api.dependencies import get_course_service
from app.modules.courses.api.schemas import (
    CourseCreateRequest,
    CourseListResponse,
    CourseResponse,
    CourseUpdateRequest,
)
from app.modules.courses.application.dto import CreateCourseInput, UpdateCourseInput
from app.modules.courses.application.exceptions import CourseNotFoundError
from app.modules.courses.application.service import CourseService
from app.shared.database.session import get_session

router = APIRouter(prefix="/courses", tags=["courses"])


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    body: CourseCreateRequest,
    service: CourseService = Depends(get_course_service),
    session: AsyncSession = Depends(get_session),
    _user: CurrentUser = Depends(require_role(Role.ADMIN)),
) -> CourseResponse:
    view = await service.create(
        CreateCourseInput(title=body.title, teacher_id=body.teacher_id, capacity=body.capacity)
    )
    await session.commit()
    return CourseResponse.from_view(view)


@router.get("", response_model=CourseListResponse)
async def list_courses(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=200),
    service: CourseService = Depends(get_course_service),
    _user: CurrentUser = Depends(get_current_user),
) -> CourseListResponse:
    page = await service.list(offset=offset, limit=limit, search=search)
    return CourseListResponse.from_page(page)


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: uuid.UUID,
    service: CourseService = Depends(get_course_service),
    _user: CurrentUser = Depends(get_current_user),
) -> CourseResponse:
    try:
        view = await service.get(course_id)
    except CourseNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "course not found") from exc
    return CourseResponse.from_view(view)


@router.put("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: uuid.UUID,
    body: CourseUpdateRequest,
    service: CourseService = Depends(get_course_service),
    session: AsyncSession = Depends(get_session),
    _user: CurrentUser = Depends(require_role(Role.ADMIN)),
) -> CourseResponse:
    try:
        view = await service.update(
            course_id,
            UpdateCourseInput(
                title=body.title, teacher_id=body.teacher_id, capacity=body.capacity
            ),
        )
    except CourseNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "course not found") from exc
    await session.commit()
    return CourseResponse.from_view(view)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: uuid.UUID,
    service: CourseService = Depends(get_course_service),
    session: AsyncSession = Depends(get_session),
    _user: CurrentUser = Depends(require_role(Role.ADMIN)),
) -> None:
    try:
        await service.delete(course_id)
    except CourseNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "course not found") from exc
    await session.commit()
