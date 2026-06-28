from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules.auth.api.router import router as auth_router
from app.modules.courses.api.router import router as courses_router
from app.modules.enrollment.api.router import router as enrollment_router
from app.modules.students.api.router import router as students_router
from app.modules.teachers.api.router import router as teachers_router
from app.shared.config import get_settings
from app.shared.middleware.logging import RequestContextMiddleware, configure_logging

settings = get_settings()
configure_logging(settings.log_level)

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
    return {"status": "ok"}
