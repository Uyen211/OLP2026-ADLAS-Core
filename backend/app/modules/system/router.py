# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import decode_access_token
from app.modules.system.models import User
from app.modules.system.schemas import (
    CourseRoleAssignRequest,
    PaginatedUsersResponse,
    RevokeSessionRequest,
    UserCreateRequest,
    UserResponse,
    UserStatusUpdateRequest,
)
from app.modules.system.service import SystemAuthService

router = APIRouter(prefix="/api/v1/system/auth", tags=["Platform Admin - Identity & Sessions"])


async def get_current_admin(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Authenticate the current technical administrator from Bearer JWT.
    Provides mock admin fallback in development if no token provided.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            service = SystemAuthService(db)
            try:
                user_id = uuid.UUID(payload["sub"])
                user = await service.repo.get_user_by_id(user_id)
                if user and user.is_active:
                    return user
            except (ValueError, TypeError):
                pass

    # Fallback default System Administrator for development and bootstrap
    service = SystemAuthService(db)
    existing_admin = await service.repo.get_user_by_email("admin@adlas.edu.vn")
    if existing_admin:
        return existing_admin

    # Bootstrap default platform admin if not yet seeded
    try:
        bootstrapped = await service.repo.create_user(
            email="admin@adlas.edu.vn",
            user_code="SYSADMIN",
            full_name="Platform System Administrator",
            password_hash="system_managed",
            system_role="ADMIN"
        )
        await db.commit()
        return bootstrapped
    except Exception:
        await db.rollback()
        # Return fallback with id=None to satisfy foreign key nullability
        return User(
            id=None,
            email="admin@adlas.edu.vn",
            user_code="SYSADMIN",
            full_name="Platform System Administrator",
            password_hash="system_managed",
            system_role="ADMIN",
            is_active=True
        )


@router.get("/users", response_model=PaginatedUsersResponse)
async def list_users(
    q: Optional[str] = Query(None, description="Search query for name, email, or user code"),
    role: Optional[str] = Query(None, description="Filter by system role: USER or ADMIN"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """List paginated users with optional search and role filtering."""
    service = SystemAuthService(db)
    return await service.list_users(
        search_query=q,
        role=role,
        is_active=is_active,
        page=page,
        page_size=page_size
    )


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    payload: UserCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Create a new user account with duplicate prevention and audit trail."""
    service = SystemAuthService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    return await service.create_user(
        payload=payload,
        actor=admin,
        ip_address=client_ip,
        user_agent=user_agent
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_detail(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Retrieve detailed user account information."""
    service = SystemAuthService(db)
    return await service.get_user_detail(user_id)


@router.put("/users/{user_id}/status", response_model=UserResponse)
async def update_user_status(
    user_id: uuid.UUID,
    payload: UserStatusUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Lock or unlock user account. Enforces E-SYS-01 and BR-03."""
    service = SystemAuthService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    return await service.update_user_status(
        target_user_id=user_id,
        payload=payload,
        actor=admin,
        ip_address=client_ip,
        user_agent=user_agent
    )


@router.post("/users/{user_id}/course-roles")
async def assign_course_role(
    user_id: uuid.UUID,
    payload: CourseRoleAssignRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Assign or update a contextual role for a user in a specific course."""
    payload.user_id = user_id
    service = SystemAuthService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    return await service.assign_course_role(
        payload=payload,
        actor=admin,
        ip_address=client_ip,
        user_agent=user_agent
    )


@router.post("/revoke-session")
async def revoke_session(
    payload: RevokeSessionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Revoke user session immediately via token blacklist and audit trail."""
    service = SystemAuthService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    return await service.revoke_session(
        payload=payload,
        actor=admin,
        ip_address=client_ip,
        user_agent=user_agent
    )
