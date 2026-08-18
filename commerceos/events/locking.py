"""Distributed locking layer.

SQLite implementation using a dedicated lock table. PostgreSQL-compatible design.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from commerceos.events.models import DistributedLock
from commerceos.events.sqlalchemy_repositories import SQLAlchemyEventsUnitOfWork


class LockManager:
    """Acquire and release named locks with automatic expiration."""

    def __init__(
        self,
        session: Session,
        default_ttl_seconds: int = 300,
        uow: Optional[SQLAlchemyEventsUnitOfWork] = None,
    ):
        self.session = session
        self.default_ttl_seconds = default_ttl_seconds
        self.uow = uow or SQLAlchemyEventsUnitOfWork(session)

    def acquire(self, lock_name: str, owner_id: str, job_id: Optional[str] = None, ttl_seconds: Optional[int] = None) -> bool:
        ttl_seconds = ttl_seconds or self.default_ttl_seconds
        lock = DistributedLock(
            lock_name=lock_name,
            owner_id=owner_id,
            job_id=job_id,
            expires_at=utc_now() + timedelta(seconds=ttl_seconds),
        )
        with self.uow:
            return self.uow.locks().acquire(lock)

    def release(self, lock_name: str, owner_id: str) -> bool:
        with self.uow:
            return self.uow.locks().release(lock_name, owner_id)

    def extend(self, lock_name: str, owner_id: str, ttl_seconds: int) -> bool:
        with self.uow:
            lock = self.uow.locks().get(lock_name)
            if lock is None or lock.owner_id != owner_id:
                return False
            lock.expires_at = utc_now() + timedelta(seconds=ttl_seconds)
            self.uow.locks().acquire(lock)
            return True

    def is_locked(self, lock_name: str) -> bool:
        with self.uow:
            lock = self.uow.locks().get(lock_name)
            if lock is None:
                return False
            expires = lock.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            return expires >= utc_now()
