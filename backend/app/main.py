from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules.students.api.router import router as students_router
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

app.include_router(students_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
