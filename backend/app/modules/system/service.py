# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

import secrets
import string
import uuid
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import hash_password, revoke_token_persistent
from app.modules.system.models import User
from app.modules.system.repository import SystemRepository
from app.modules.system.schemas import (
    CourseRoleAssignRequest,
    PaginatedUsersResponse,
    RevokeSessionRequest,
    UserCreateRequest,
    UserResponse,
    UserStatusUpdateRequest,
)


def generate_secure_password(length: int = 10) -> str:
    """Generate a cryptographically secure random password meeting BR-02 requirements."""
    chars_lower = string.ascii_lowercase
    chars_upper = string.ascii_uppercase
    chars_digits = string.digits
    chars_symbols = "!@#$%^&*"

    # Ensure at least one character from each required character set
    password = [
        secrets.choice(chars_lower),
        secrets.choice(chars_upper),
        secrets.choice(chars_digits),
        secrets.choice(chars_symbols)
    ]
    all_chars = chars_lower + chars_upper + chars_digits + chars_symbols
    password += [secrets.choice(all_chars) for _ in range(length - 4)]
    secrets.SystemRandom().shuffle(password)
    return "".join(password)


class SystemAuthService:
    """Business logic service for technical admin user and session management."""

    def __init__(self, db: AsyncSession):
        self.repo = SystemRepository(db)

    async def list_users(
        self,
        search_query: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20
    ) -> PaginatedUsersResponse:
        """Fetch paginated user list."""
        users, total, total_pages = await self.repo.get_users(
            search_query=search_query,
            role=role,
            is_active=is_active,
            page=page,
            page_size=page_size
        )
        return PaginatedUsersResponse(
            items=[UserResponse.model_validate(u) for u in users],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    async def get_user_detail(self, user_id: uuid.UUID) -> UserResponse:
        """Get detail of a single user."""
        user = await self.repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "E-404", "message": "User not found in system."}
            )
        return UserResponse.model_validate(user)

    async def create_user(
        self,
        payload: UserCreateRequest,
        actor: Optional[User] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UserResponse:
        """Create a new user account with duplicate prevention and audit logging."""
        # Check duplicate email (E-4)
        existing_email = await self.repo.get_user_by_email(payload.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "E-4",
                    "field": "email",
                    "message": f"Email address '{payload.email}' is already registered in the system."
                }
            )

        # Check duplicate user_code (E-4)
        if payload.user_code:
            existing_code = await self.repo.get_user_by_code(payload.user_code)
            if existing_code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error_code": "E-4",
                        "field": "user_code",
                        "message": f"User code '{payload.user_code}' is already registered in the system."
                    }
                )

        # Determine password: auto-generate if omitted
        raw_password = payload.password if payload.password else generate_secure_password(10)
        hashed = hash_password(raw_password)

        new_user = User(
            email=payload.email.lower().strip(),
            user_code=payload.user_code.upper().strip() if payload.user_code else None,
            full_name=payload.full_name.strip(),
            password_hash=hashed,
            system_role=payload.system_role.upper().strip(),
            is_active=True
        )

        user = await self.repo.create_user(new_user)

        # Audit log entry
        await self.repo.log_audit(
            actor_id=actor.id if actor else None,
            actor_email=actor.email if actor else "system",
            action="USER_CREATED",
            module="identity",
            details={
                "target_user_id": str(user.id),
                "target_email": user.email,
                "system_role": user.system_role,
                "auto_generated_password": payload.password is None
            },
            ip_address=ip_address,
            user_agent=user_agent,
            severity="INFO"
        )

        return UserResponse.model_validate(user)

    async def update_user_status(
        self,
        target_user_id: uuid.UUID,
        payload: UserStatusUpdateRequest,
        actor: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UserResponse:
        """Lock or unlock a user account, enforcing BR-03 and preventing self-deactivation."""
        target_user = await self.repo.get_user_by_id(target_user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "E-404", "message": "Target user not found."}
            )

        # E-SYS-01 / E-ADMIN-01: Admin cannot deactivate own account
        if target_user.id == actor.id and not payload.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "E-SYS-01",
                    "message": "System does not allow administrators to deactivate their own account."
                }
            )

        # BR-03: Cannot deactivate the last remaining active system administrator
        if target_user.system_role == "ADMIN" and not payload.is_active:
            active_admin_count = await self.repo.count_active_admins()
            if active_admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error_code": "BR-03",
                        "message": "Cannot deactivate the last active system administrator."
                    }
                )

        target_user.is_active = payload.is_active
        updated = await self.repo.update_user(target_user)

        # Log audit entry
        severity = "WARNING" if not payload.is_active else "INFO"
        action = "USER_DEACTIVATED" if not payload.is_active else "USER_ACTIVATED"

        await self.repo.log_audit(
            actor_id=actor.id,
            actor_email=actor.email,
            action=action,
            module="identity",
            details={
                "target_user_id": str(target_user.id),
                "target_email": target_user.email,
                "is_active": payload.is_active,
                "reason": payload.reason
            },
            ip_address=ip_address,
            user_agent=user_agent,
            severity=severity
        )

        return UserResponse.model_validate(updated)

    async def assign_course_role(
        self,
        payload: CourseRoleAssignRequest,
        actor: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> dict:
        """Assign or update a contextual role for a user in a specific course."""
        target_user = await self.repo.get_user_by_id(payload.user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "E-404", "message": "Target user not found."}
            )

        await self.repo.log_audit(
            actor_id=actor.id,
            actor_email=actor.email,
            action="COURSE_ROLE_ASSIGNED",
            module="course",
            details={
                "target_user_id": str(payload.user_id),
                "course_id": str(payload.course_id),
                "contextual_role": payload.contextual_role
            },
            ip_address=ip_address,
            user_agent=user_agent,
            severity="INFO"
        )

        return {
            "status": "success",
            "message": f"Assigned role {payload.contextual_role} to user {target_user.email} successfully."
        }

    async def revoke_session(
        self,
        payload: RevokeSessionRequest,
        actor: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> dict:
        """Revoke a user session persistently in identity.revoked_tokens and audit log."""
        await revoke_token_persistent(self.repo.db, payload.session_id, user_id=actor.id)

        await self.repo.log_audit(
            actor_id=actor.id,
            actor_email=actor.email,
            action="SESSION_REVOKED",
            module="identity",
            details={
                "revoked_session_id": payload.session_id,
                "reason": payload.reason
            },
            ip_address=ip_address,
            user_agent=user_agent,
            severity="WARNING"
        )

        return {
            "status": "success",
            "message": "Session has been revoked immediately."
        }
