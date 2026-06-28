from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.application.service import AuthService
from app.modules.auth.infrastructure.password import PasslibPasswordHasher
from app.modules.auth.infrastructure.repository import SqlAlchemyUserRepository
from app.modules.auth.infrastructure.tokens import JoseTokenIssuer
from app.shared.config.settings import Settings, get_settings
from app.shared.database.session import get_session


def get_token_issuer(settings: Settings = Depends(get_settings)) -> JoseTokenIssuer:
    return JoseTokenIssuer(settings)


def get_auth_service(
    session: AsyncSession = Depends(get_session),
    tokens: JoseTokenIssuer = Depends(get_token_issuer),
) -> AuthService:
    repository = SqlAlchemyUserRepository(session)
    hasher = PasslibPasswordHasher()
    return AuthService(repository, hasher, tokens)
