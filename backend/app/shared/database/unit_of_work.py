from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.session import SessionFactory


class UnitOfWork:
    """Defines a transaction boundary.

    Application services depend on this (or a module-specific subclass exposing
    typed repositories), not on the SQLAlchemy session directly — that's what
    keeps the application layer testable without a real database.
    """

    session: AsyncSession

    async def __aenter__(self) -> UnitOfWork:
        self.session = SessionFactory()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
        await self.session.close()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
