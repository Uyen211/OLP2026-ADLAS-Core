# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

import re
import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreateRequest(BaseModel):
    """Payload for creating a new user account by technical administrator."""
    full_name: str = Field(..., min_length=2, max_length=50, description="User full name")
    email: EmailStr = Field(..., max_length=150, description="Standard email address")
    user_code: Optional[str] = Field(None, min_length=6, max_length=20, description="Uppercase alphanumeric ID code")
    system_role: str = Field(default="USER", description="Global role: USER or ADMIN")
    password: Optional[str] = Field(None, min_length=8, description="Optional initial password")
    force_password_change: bool = Field(default=True, description="Force user to change password on first login")

    @field_validator("user_code")
    @classmethod
    def validate_user_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().upper()
            if not re.match(r"^[A-Z0-9]+$", v):
                raise ValueError("User code must only contain uppercase letters and digits")
        return v

    @field_validator("system_role")
    @classmethod
    def validate_system_role(cls, v: str) -> str:
        allowed = {"USER", "ADMIN"}
        v = v.strip().upper()
        if v not in allowed:
            raise ValueError(f"System role must be one of: {', '.join(allowed)}")
        return v


class UserResponse(BaseModel):
    """User account details returned to the administrator."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    user_code: Optional[str] = None
    full_name: str
    system_role: str
    is_active: bool
    failed_login_count: int
    created_at: datetime
    updated_at: datetime


class UserStatusUpdateRequest(BaseModel):
    """Payload for locking or unlocking an account."""
    is_active: bool = Field(..., description="Target active status")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for status change")


class CourseRoleAssignRequest(BaseModel):
    """Payload for assigning a contextual role in a course."""
    user_id: uuid.UUID = Field(..., description="Target user identifier")
    course_id: uuid.UUID = Field(..., description="Target course identifier")
    contextual_role: str = Field(..., description="Contextual role: INSTRUCTOR or STUDENT")

    @field_validator("contextual_role")
    @classmethod
    def validate_contextual_role(cls, v: str) -> str:
        allowed = {"INSTRUCTOR", "STUDENT"}
        v = v.strip().upper()
        if v not in allowed:
            raise ValueError(f"Contextual role must be one of: {', '.join(allowed)}")
        return v


class SessionInfo(BaseModel):
    """Active user session details."""
    session_id: str
    user_id: uuid.UUID
    email: str
    full_name: str
    system_role: str
    ip_address: Optional[str] = None
    created_at: datetime


class RevokeSessionRequest(BaseModel):
    """Payload for revoking a user session."""
    session_id: str = Field(..., description="Session identifier or token signature to revoke")
    reason: Optional[str] = Field(None, max_length=255, description="Revocation justification")


class PaginatedUsersResponse(BaseModel):
    """Paginated list of users."""
    items: List[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
