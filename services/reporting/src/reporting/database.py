from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from reporting.config import get_settings


class Base(DeclarativeBase):
    pass


def make_engine() -> AsyncEngine:
    return create_async_engine(get_settings().database_url, pool_pre_ping=True)


def make_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = make_engine()
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
