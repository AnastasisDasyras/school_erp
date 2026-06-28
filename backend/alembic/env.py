import asyncio
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import context

# Import every module's ORM models so they register on Base.metadata for autogenerate.
from app.modules.auth.infrastructure import orm as auth_orm
from app.modules.courses.infrastructure import orm as courses_orm
from app.modules.enrollment.infrastructure import orm as enrollment_orm
from app.modules.students.infrastructure import orm as students_orm
from app.modules.teachers.infrastructure import orm as teachers_orm
from app.shared.config import get_settings
from app.shared.database.base import Base
from app.shared.database.session import make_engine

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection) -> None:  # type: ignore[no-untyped-def]
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine: AsyncEngine = make_engine()
    async with engine.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
