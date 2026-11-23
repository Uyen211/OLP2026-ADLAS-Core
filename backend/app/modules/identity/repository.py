# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Data access repository for end-user identity operations reusing system.models.User."""

from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Tuple
import uuid
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.system.models import OutboxEvent, User


class IdentityRepository:
    """Repository encapsulating permitted identity.users and system.outbox_events queries."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        normalized = email.strip().lower()
        stmt = select(User).where(func.lower(User.email) == normalized)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_identifier(self, identifier: str) -> Optional[User]:
        """Lookup user by email (case-insensitive) or user_code (MSSV/Ma GV)."""
        cleaned = identifier.strip()
        stmt = select(User).where(
            or_(
                func.lower(User.email) == cleaned.lower(),
                func.upper(User.user_code) == cleaned.upper(),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def increment_failed_login(
        self,
        user_id: uuid.UUID,
        lock_threshold: int = 5,
        lock_duration_seconds: int = 900,
    ) -> Tuple[int, Optional[datetime]]:
        """
        Atomically increment failed_login_count to prevent race conditions (BR-02).
        Locks the account for `lock_duration_seconds` once threshold is reached.
        """
        now = datetime.now(timezone.utc)
        inc_stmt = (
            update(User)
            .where(User.id == user_id)
            .values(
                failed_login_count=User.failed_login_count + 1,
                updated_at=now,
            )
            .returning(User.failed_login_count)
        )
        result = await self.db.execute(inc_stmt)
        new_count = int(result.scalar_one())

        locked_until: Optional[datetime] = None
        if new_count >= lock_threshold:
            locked_until = now + timedelta(seconds=lock_duration_seconds)
            lock_stmt = (
                update(User)
                .where(User.id == user_id)
                .values(locked_until=locked_until, updated_at=now)
            )
            await self.db.execute(lock_stmt)

        await self.db.flush()
        return new_count, locked_until

    async def reset_failed_login(self, user_id: uuid.UUID) -> None:
        """Reset failed login counter and clear any temporary lock."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(failed_login_count=0, locked_until=None, updated_at=now)
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def update_password_hash(self, user_id: uuid.UUID, password_hash: str) -> None:
        """Update password hash and clear any brute-force lock."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(
                password_hash=password_hash,
                failed_login_count=0,
                locked_until=None,
                updated_at=now,
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def create_user(
        self,
        email: str,
        full_name: str,
        password_hash: str,
        user_code: Optional[str] = None,
        system_role: str = "USER",
    ) -> User:
        """Persist a new end-user account in identity.users."""
        user = User(
            email=email.strip().lower(),
            user_code=user_code.strip().upper() if user_code else None,
            full_name=full_name.strip(),
            password_hash=password_hash,
            system_role=system_role.strip().upper(),
            is_active=True,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def get_users_by_emails_or_codes(
        self,
        emails: Iterable[str],
        user_codes: Iterable[str],
    ) -> List[User]:
        """Batch fetch users matching any of the provided emails or user codes."""
        norm_emails = [e.strip().lower() for e in emails if e and e.strip()]
        norm_codes = [c.strip().upper() for c in user_codes if c and c.strip()]
        conditions = []
        if norm_emails:
            conditions.append(func.lower(User.email).in_(norm_emails))
        if norm_codes:
            conditions.append(func.upper(User.user_code).in_(norm_codes))
        if not conditions:
            return []

        stmt = select(User).where(or_(*conditions))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def enqueue_outbox_event(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: uuid.UUID,
        payload: Dict[str, object],
    ) -> OutboxEvent:
        """Insert a transactional outbox event into system.outbox_events."""
        event = OutboxEvent(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            status="PENDING",
        )
        self.db.add(event)
        await self.db.flush()
        return event
