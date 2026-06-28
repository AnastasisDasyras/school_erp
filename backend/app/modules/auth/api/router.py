from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.api.dependencies import get_auth_service
from app.modules.auth.api.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.modules.auth.application.dto import LoginInput, RegisterUserInput
from app.modules.auth.application.exceptions import (
    DuplicateUserEmailError,
    InactiveUserError,
    InvalidCredentialsError,
)
from app.modules.auth.application.service import AuthService
from app.shared.database.session import get_session

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    try:
        view = await service.register(
            RegisterUserInput(email=body.email, password=body.password, role=body.role)
        )
    except DuplicateUserEmailError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, f"email already in use: {exc}") from exc
    await session.commit()
    return UserResponse.from_view(view)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    try:
        pair = await service.login(LoginInput(email=body.email, password=body.password))
    except (InvalidCredentialsError, InactiveUserError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials") from exc
    return TokenResponse.from_pair(pair)
