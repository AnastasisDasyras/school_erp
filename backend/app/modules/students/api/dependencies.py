from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.students.application.service import StudentService
from app.modules.students.infrastructure.repository import SqlAlchemyStudentRepository
from app.shared.cache.client import get_redis
from app.shared.cache.redis_cache import RedisCache
from app.shared.database.session import get_session


def get_student_service(
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> StudentService:
    repository = SqlAlchemyStudentRepository(session)
    cache = RedisCache(redis)
    return StudentService(repository, cache)
