import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class OutboxStatus(StrEnum):
    PENDING = "pending"
    PUBLISHED = "published"
    FAILED = "failed"


class OutboxEventModel(Base):
    """The outbox: a row here is written in the *same* DB transaction as the
    business write that caused it (e.g. recording attendance). A separate
    relay process polls for PENDING rows and publishes them to SNS — this is
    what makes "write to Postgres" and "publish to SNS" atomic *as observed
    by the rest of the system*, without a distributed transaction across two
    different infrastructure systems (which isn't possible to do atomically
    at all). See ADR 0008.
    """

    __tablename__ = "outbox_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[OutboxStatus] = mapped_column(
        # values_callable: send the enum's *value* ("pending") to Postgres,
        # not its member name ("PENDING") — SQLAlchemy's default for a
        # StrEnum sends the name, which doesn't match the lowercase values
        # the `outbox_status` Postgres enum type was created with.
        Enum(
            OutboxStatus,
            name="outbox_status",
            values_callable=lambda enum: [e.value for e in enum],
        ),
        nullable=False,
        default=OutboxStatus.PENDING,
        index=True,
    )
    attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
