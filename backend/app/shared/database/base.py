from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base. Each module's infrastructure layer defines its own ORM models."""
