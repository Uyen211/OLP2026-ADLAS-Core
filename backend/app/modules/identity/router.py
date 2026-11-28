# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""REST API router for end-user authentication, MFA, and password recovery."""

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.identity.dependencies import CurrentUser, get_current_user
from app.modules.identity.schemas import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LoginResponse,
    MeResponse,
    MfaCodeRequest,
    MfaSetupResponse,
    MfaVerifyRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    TokenResponse,
)
from app.modules.identity.service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication & Identity"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """Self-register a new user account (T2-P-M1-01)."""
    service = AuthService(db)
    return await service.register_user(payload)


def _extract_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Authenticate by email or user_code with brute-force lock and optional MFA step."""
    service = AuthService(db)
    return await service.authenticate(
        identifier=payload.identifier,
        password=payload.password,
        remember_me=payload.remember_me,
        client_ip=_extract_client_ip(request),
    )


@router.post("/mfa/verify", response_model=TokenResponse)
async def verify_mfa(
    payload: MfaVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Verify 6-digit TOTP code against a pending MFA login token."""
    service = AuthService(db)
    return await service.verify_mfa(
        mfa_token=payload.mfa_token,
        code=payload.code,
        client_ip=_extract_client_ip(request),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Exchange a valid refresh token for a new access and refresh token pair."""
    service = AuthService(db)
    return await service.refresh_tokens(payload.refresh_token)


@router.get("/me", response_model=MeResponse)
async def get_me(
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    """Return authenticated user profile, contextual course roles, and landing route."""
    service = AuthService(db)
    return await service.get_me(current.user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Revoke the current access token immediately."""
    service = AuthService(db)
    await service.logout(current.token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/mfa/setup", response_model=MfaSetupResponse)
async def setup_mfa(
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MfaSetupResponse:
    """Generate a new TOTP secret and otpauth URI for the authenticated user."""
    service = AuthService(db)
    return await service.setup_mfa(current.user)


@router.post("/mfa/enable", status_code=status.HTTP_204_NO_CONTENT)
async def enable_mfa(
    payload: MfaCodeRequest,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Confirm initial TOTP code and enable MFA on the account."""
    service = AuthService(db)
    await service.enable_mfa(current.user, payload.code)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/mfa/disable", status_code=status.HTTP_204_NO_CONTENT)
async def disable_mfa(
    payload: MfaCodeRequest,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Confirm current TOTP code and disable MFA on the account."""
    service = AuthService(db)
    await service.disable_mfa(current.user, payload.code)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/password/forgot",
    response_model=ForgotPasswordResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> ForgotPasswordResponse:
    """Request a password reset link (always returns neutral 202 response)."""
    service = AuthService(db)
    return await service.forgot_password(payload.email)


@router.post("/password/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Reset account password using a valid 15-minute reset token."""
    service = AuthService(db)
    await service.reset_password(
        token=payload.token,
        new_password=payload.new_password,
        confirm_password=payload.confirm_password,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
