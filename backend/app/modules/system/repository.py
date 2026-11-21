# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

import math
import uuid
from typing import List, Optional, Tuple
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.system.models import SystemAuditLog, User


class SystemRepository:
    """Repository handling database access for system administration."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_users(
        self,
        search_query: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[User], int, int]:
        """Fetch paginated users with optional search and filters."""
        stmt = select(User)

        if search_query:
            q = f"%{search_query.strip()}%"
            stmt = stmt.where(
                or_(
                    User.full_name.ilike(q),
                    User.email.ilike(q),
                    User.user_code.ilike(q)
                )
            )

        if role:
            stmt = stmt.where(User.system_role == role.strip().upper())

        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)

        # Count total matching rows
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar() or 0

        # Apply ordering and pagination
        offset = (page - 1) * page_size
        stmt = stmt.order_by(User.created_at.desc()).offset(offset).limit(page_size)

        result = await self.db.execute(stmt)
        users = list(result.scalars().all())
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return users, total, total_pages

    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Retrieve a user by primary key UUID."""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Retrieve a user by unique email address."""
        stmt = select(User).where(User.email == email.strip().lower())
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_code(self, user_code: str) -> Optional[User]:
        """Retrieve a user by unique identifier code."""
        stmt = select(User).where(User.user_code == user_code.strip().upper())
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def count_active_admins(self) -> int:
        """Count active system administrators for BR-03 enforcement."""
        stmt = select(func.count(User.id)).where(
            User.system_role == "ADMIN",
            User.is_active.is_(True)
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def create_user(self, user: User) -> User:
        """Persist a new user entity to the identity schema."""
        self.db.add(user)
        await self.db.flush()
        return user

    async def update_user(self, user: User) -> User:
        """Update existing user entity."""
        await self.db.flush()
        return user

    async def log_audit(
        self,
        actor_id: Optional[uuid.UUID],
        actor_email: Optional[str],
        action: str,
        module: str,
        details: dict,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        severity: str = "INFO"
    ) -> SystemAuditLog:
        """Write an append-only audit log entry."""
        audit = SystemAuditLog(
            actor_id=actor_id,
            actor_email=actor_email,
            action=action,
            module=module,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            severity=severity
        )
        self.db.add(audit)
        await self.db.flush()
        return audit
