# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

from datetime import datetime
import uuid
from typing import List, Literal, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """User self-registration payload (T2-P-M1-01)."""

    email: EmailStr = Field(..., max_length=150)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=150)
    role: Literal["STUDENT", "INSTRUCTOR"] = "STUDENT"

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Mat khau phai co it nhat 8 ky tu.")
        has_upper = any(c.isupper() for c in value)
        has_lower = any(c.islower() for c in value)
        has_digit = any(c.isdigit() for c in value)
        if not (has_upper and has_lower and has_digit):
            raise ValueError("Mat khau phai chua ca chu hoa, chu thuong va chu so.")
        return value


class RegisterResponse(BaseModel):
    """User self-registration response (T2-P-M1-01)."""

    id: uuid.UUID
    email: str
    full_name: str
    role: str
    status: str
    created_at: datetime


class CourseRoleClaim(BaseModel):
    """Contextual role assigned to a user in a specific course (BR-01)."""

    course_id: uuid.UUID
    role: str
    course_code: Optional[str] = None
    course_name: Optional[str] = None


class MeResponse(BaseModel):
    """Authenticated user profile with contextual roles and landing target."""

    id: uuid.UUID
    email: str
    user_code: Optional[str] = None
    full_name: str
    avatar_url: Optional[str] = None
    system_role: str
    mfa_enabled: bool = False
    course_roles: List[CourseRoleClaim] = Field(default_factory=list)
    landing: Literal["ADMIN_CONSOLE", "TEACHING", "LEARNING"]


class LoginRequest(BaseModel):
    """Credentials payload accepting either email or user_code (MSSV / Ma GV)."""

    identifier: str = Field(..., min_length=1, max_length=150)
    password: str = Field(..., min_length=1, max_length=128)
    remember_me: bool = False

    @field_validator("identifier")
    @classmethod
    def strip_identifier(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Ten dang nhap khong duoc de trong.")
        return cleaned


class LoginResponse(BaseModel):
    """Response from POST /api/v1/auth/login (direct session or MFA step)."""

    requires_mfa: bool
    mfa_token: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = 0
    user: Optional[MeResponse] = None


class MfaVerifyRequest(BaseModel):
    """Step-2 MFA verification payload."""

    mfa_token: str = Field(..., min_length=1)
    code: str = Field(..., pattern=r"^\d{6}$")


class TokenResponse(BaseModel):
    """Issued access and refresh token pair with user profile."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: MeResponse


class RefreshRequest(BaseModel):
    """Token refresh payload."""

    refresh_token: str = Field(..., min_length=1)


class MfaSetupResponse(BaseModel):
    """TOTP enrollment payload containing Base32 secret and otpauth URI."""

    secret: str
    otpauth_uri: str


class MfaCodeRequest(BaseModel):
    """6-digit TOTP confirmation payload for enabling or disabling MFA."""

    code: str = Field(..., pattern=r"^\d{6}$")


class ForgotPasswordRequest(BaseModel):
    """Password recovery request by registered email."""

    email: str = Field(..., min_length=3, max_length=150)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if "@" not in cleaned or "." not in cleaned.split("@")[-1]:
            raise ValueError("Dia chi email khong hop le.")
        return cleaned


class ForgotPasswordResponse(BaseModel):
    """Neutral acknowledgment for password reset requests."""

    message: str


class ResetPasswordRequest(BaseModel):
    """Password reset completion payload."""

    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=1, max_length=128)
    confirm_password: str = Field(..., min_length=1, max_length=128)
