from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.courses.application.service import CourseService
from app.modules.courses.infrastructure.repository import SqlAlchemyCourseRepository
from app.shared.cache.client import get_redis
from app.shared.cache.redis_cache import RedisCache
from app.shared.database.session import get_session


def get_course_service(
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> CourseService:
    repository = SqlAlchemyCourseRepository(session)
    cache = RedisCache(redis)
    return CourseService(repository, cache)
