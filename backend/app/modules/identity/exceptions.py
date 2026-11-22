# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

from datetime import datetime
from typing import Any, Dict, Optional
from fastapi import status
from app.core.exceptions import ADLASException


class InvalidCredentialsWithAttemptsException(ADLASException):
    """E-5: Invalid credentials with remaining attempts metadata."""

    def __init__(self, remaining_attempts: Optional[int] = None):
        super().__init__(
            code="E-5",
            detail="Thong tin dang nhap hoac mat khau khong chinh xac.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
        if remaining_attempts is not None and isinstance(self.detail, dict):
            self.detail["remaining_attempts"] = remaining_attempts


class AccountLockedException(ADLASException):
    """E-6: Account or client IP temporarily locked due to brute-force attempts (BR-02)."""

    def __init__(
        self,
        retry_after_seconds: int,
        locked_until: Optional[datetime] = None,
    ):
        super().__init__(
            code="E-6",
            detail="Tai khoan tam thoi bi khoa do nhap sai qua 5 lan lien tiep. Vui long thu lai sau 15 phut.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
        if isinstance(self.detail, dict):
            self.detail["retry_after_seconds"] = max(1, int(retry_after_seconds))
            if locked_until is not None:
                self.detail["locked_until"] = locked_until.isoformat()


class InvalidMfaCodeException(ADLASException):
    """E-AUTH-03: Invalid or expired 6-digit TOTP code."""

    def __init__(self, remaining_attempts: Optional[int] = None):
        super().__init__(
            code="E-AUTH-03",
            detail="Ma xac thuc 2 lop khong hop le hoac da het han.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
        if remaining_attempts is not None and isinstance(self.detail, dict):
            self.detail["remaining_attempts"] = remaining_attempts


class MfaStoreUnavailableException(ADLASException):
    """409: MFA storage columns are not yet provisioned in identity.users."""

    def __init__(self):
        super().__init__(
            code="E-MFA-UNAVAILABLE",
            detail="Kho luu tru MFA chua duoc khoi tao trong co so du lieu.",
            status_code=status.HTTP_409_CONFLICT,
        )


class PasswordMismatchException(ADLASException):
    """E-3: Confirmation password does not match new password."""

    def __init__(self):
        super().__init__(
            code="E-3",
            detail="Mat khau xac nhan khong trung khop.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class WeakPasswordException(ADLASException):
    """E-2: Password does not satisfy complexity requirements."""

    def __init__(self):
        super().__init__(
            code="E-2",
            detail="Mat khau phai co it nhat 8 ky tu, gom chu hoa, chu thuong, chu so va ky tu dac biet.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class ResetTokenInvalidException(ADLASException):
    """400: Password reset token is invalid, revoked, or expired."""

    def __init__(self):
        super().__init__(
            code="E-RESET-INVALID",
            detail="Lien ket dat lai mat khau khong hop le hoac da het han.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class UnauthorizedTokenException(ADLASException):
    """401: Missing, malformed, wrong-type, or revoked bearer token."""

    def __init__(self, detail: str = "Phien dang nhap khong hop le hoac da het han."):
        super().__init__(
            code="E-5",
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


def build_error_payload(code: str, message: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Helper for constructing structured error payloads."""
    payload: Dict[str, Any] = {"code": code, "message": message}
    if extra:
        payload.update(extra)
    return payload
