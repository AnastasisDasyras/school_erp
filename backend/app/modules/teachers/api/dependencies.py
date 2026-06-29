from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.teachers.application.service import TeacherService
from app.modules.teachers.infrastructure.repository import SqlAlchemyTeacherRepository
from app.shared.cache.client import get_redis
from app.shared.cache.redis_cache import RedisCache
from app.shared.database.session import get_session


def get_teacher_service(
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> TeacherService:
    repository = SqlAlchemyTeacherRepository(session)
    cache = RedisCache(redis)
    return TeacherService(repository, cache)
