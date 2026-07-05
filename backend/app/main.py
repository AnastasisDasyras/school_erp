from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.attendance.api.router import router as attendance_router
from app.modules.auth.api.router import router as auth_router
from app.modules.courses.api.router import router as courses_router
from app.modules.enrollment.api.router import router as enrollment_router
from app.modules.grades.api.router import router as grades_router
from app.modules.students.api.router import router as students_router
from app.modules.teachers.api.router import router as teachers_router
from app.shared.config import get_settings
from app.shared.database.session import get_session
from app.shared.middleware.logging import RequestContextMiddleware, configure_logging
from app.shared.observability.middleware import PrometheusMiddleware
from app.shared.observability.setup import setup_tracing

settings = get_settings()
configure_logging(settings.log_level, settings.log_dir)

app = FastAPI(title=settings.app_name)

# OTel tracing — must be called before any request arrives.
# SQLAlchemy engine instrumentation is deferred to after the engine is created
# (see database/session.py); FastAPI auto-instrumentation happens here.
setup_tracing(app)

app.add_middleware(PrometheusMiddleware)
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
app.include_router(attendance_router, prefix="/api/v1")
app.include_router(grades_router, prefix="/api/v1")


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    """Prometheus scrape endpoint. Prometheus hits this every 15s (see prometheus.yml).

    include_in_schema=False keeps it out of the OpenAPI docs — it's an
    infrastructure endpoint, not part of the public API contract.
    """
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


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
