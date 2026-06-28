from dataclasses import dataclass


@dataclass(frozen=True)
class CurrentUser:
    id: str
    role: str


def get_current_user() -> CurrentUser:
    """Stub for Phase 0 so other modules can depend on a 'current user' shape.

    Replaced in Phase 1 by real JWT decoding + RBAC. Modules should depend on
    this function (a FastAPI dependency), never on JWT details directly —
    that's the seam that makes the Phase 1 swap a one-file change.
    """
    return CurrentUser(id="00000000-0000-0000-0000-000000000000", role="admin")
