from commerceos.shared.value_objects.primitives import utc_now
from typing import Any
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import MetaData, DateTime, String, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# PostgreSQL-compatible naming convention
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    metadata = metadata
    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }

    @staticmethod
    def _set_created_at(
        mapper: Any, connection: Any, target: Any
    ) -> None:
        if hasattr(target, "created_at") and target.created_at is None:
            target.created_at = utc_now()

    @staticmethod
    def _set_updated_at(
        mapper: Any, connection: Any, target: Any
    ) -> None:
        if hasattr(target, "updated_at"):
            target.updated_at = utc_now()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: utc_now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: utc_now(), onupdate=lambda: utc_now()
    )


class TenantMixin:
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    business_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    store_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)


def new_uuid() -> str:
    return str(uuid4())


@event.listens_for(Base, "before_insert", propagate=True)
def _before_insert(mapper, connection, target):
    if hasattr(target, "created_at") and target.created_at is None:
        target.created_at = utc_now()
    if hasattr(target, "updated_at") and target.updated_at is None:
        target.updated_at = utc_now()


@event.listens_for(Base, "before_update", propagate=True)
def _before_update(mapper, connection, target):
    if hasattr(target, "updated_at"):
        target.updated_at = utc_now()
