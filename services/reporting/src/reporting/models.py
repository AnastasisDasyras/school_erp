import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from reporting.database import Base


class AuditLogEntry(Base):
    """The Reporting service's own table — it never reads from the monolith's
    tables, and the monolith never reads from this one. Separate data ownership
    is what makes this a genuine microservice, not just code running in a
    different container. In a real deployment this would be its own RDS instance.
    """

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[str] = mapped_column(String, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
