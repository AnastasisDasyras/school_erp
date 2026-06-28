from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.api.router import router as auth_router
from app.modules.courses.api.router import router as courses_router
from app.modules.enrollment.api.router import router as enrollment_router
from app.modules.students.api.router import router as students_router
from app.modules.teachers.api.router import router as teachers_router
from app.shared.config import get_settings
from app.shared.database.session import get_session
from app.shared.middleware.logging import RequestContextMiddleware, configure_logging

settings = get_settings()
configure_logging(settings.log_level, settings.log_dir)

app = FastAPI(title=settings.app_name)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(students_router, prefix="/api/v1")
app.include_router(teachers_router, prefix="/api/v1")
app.include_router(courses_router, prefix="/api/v1")
app.include_router(enrollment_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness: is the process up at all. Always cheap, never touches the DB."""
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    """Readiness: can this instance actually serve traffic.

    Nginx's upstream healthcheck (Phase 2) hits this, not /health — a replica
    that's up but can't reach Postgres should be taken out of rotation, not
    handed requests it can only 500 on.
    """
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not ready") from exc
    return {"status": "ready"}
