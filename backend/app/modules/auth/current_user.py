from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.modules.auth.domain.user import Role
from app.modules.auth.infrastructure.tokens import InvalidTokenError, JoseTokenIssuer
from app.shared.config.settings import Settings, get_settings

bearer_scheme = HTTPBearer(auto_error=True)


@dataclass(frozen=True)
class CurrentUser:
    id: uuid.UUID
    role: Role


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    """Decodes the bearer JWT into a CurrentUser.

    Every other module depends on this function, never on JWT/jose details
    directly — that's the seam that let Phase 0's fake-admin stub become a
    real implementation here without touching a single other module.
    """
    tokens = JoseTokenIssuer(settings)
    try:
        payload = tokens.decode(credentials.credentials)
    except InvalidTokenError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "invalid or expired token"
        ) from exc

    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not an access token")

    try:
        user_id = uuid.UUID(str(payload["sub"]))
        role = Role(payload["role"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "malformed token") from exc

    return CurrentUser(id=user_id, role=role)


def require_role(*allowed: Role) -> Callable[[CurrentUser], CurrentUser]:
    """RBAC dependency factory: `Depends(require_role(Role.ADMIN))`.

    Kept separate from get_current_user so endpoints can opt into "any
    authenticated user" (just get_current_user) or a specific role set
    without duplicating the JWT-decoding logic.
    """

    def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient role")
        return user

    return _check
