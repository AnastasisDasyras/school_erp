import asyncio
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import context
from reporting.config import get_settings
from reporting.database import Base, make_engine
from reporting import models  # noqa: F401 — registers AuditLogEntry on Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        version_table="alembic_version_reporting",
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection) -> None:  # type: ignore[no-untyped-def]
    # version_table: use a separate table from the monolith's alembic_version
    # so both Alembic histories coexist in the same Postgres instance without
    # colliding — critical since in local dev they share one DB.
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table="alembic_version_reporting",
    )
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
