# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Core authentication, MFA, brute-force protection, and password recovery services."""

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable, Deque, Dict, List, Literal, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    revoke_token,
    verify_password,
)
from app.modules.identity.exceptions import (
    AccountLockedException,
    InvalidCredentialsWithAttemptsException,
    InvalidMfaCodeException,
    MfaStoreUnavailableException,
    PasswordMismatchException,
    ResetTokenInvalidException,
    UnauthorizedTokenException,
    WeakPasswordException,
)
from app.modules.identity.mfa_store import IMfaSecretStore, default_mfa_store
from app.modules.identity.repository import IdentityRepository
from app.modules.identity.schemas import (
    CourseRoleClaim,
    ForgotPasswordResponse,
    LoginResponse,
    MeResponse,
    MfaSetupResponse,
    TokenResponse,
)
from app.modules.identity.totp import (
    build_otpauth_uri,
    generate_secret,
    verify_totp,
)
from app.modules.system.models import User

MAX_FAILED_ATTEMPTS = 5
LOCK_DURATION_SECONDS = 900  # 15 minutes (BR-02)
MFA_TOKEN_EXPIRE_MINUTES = 5
RESET_TOKEN_EXPIRE_MINUTES = 15
REFRESH_SHORT_HOURS = 12
REFRESH_REMEMBER_DAYS = 7

# Pre-computed dummy bcrypt hash to equalize timing when user does not exist
_DUMMY_PASSWORD_HASH = hash_password("DummyTimingDefense#2026")

CourseRolesProvider = Callable[[AsyncSession, uuid.UUID], Awaitable[List[CourseRoleClaim]]]
_course_roles_provider: Optional[CourseRolesProvider] = None


def register_course_roles_provider(provider: Optional[CourseRolesProvider]) -> None:
    """Register callback (e.g. from course.public_api) to resolve contextual course roles."""
    global _course_roles_provider
    _course_roles_provider = provider


class IpRateLimiter:
    """In-process sliding window rate limiter for failed auth attempts per client IP."""

    def __init__(self, max_attempts: int = 15, window_seconds: int = LOCK_DURATION_SECONDS):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: Dict[str, Deque[float]] = defaultdict(deque)

    def _prune(self, ip: str, now_ts: float) -> Deque[float]:
        bucket = self._attempts[ip]
        cutoff = now_ts - self.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        return bucket

    def check_blocked(self, ip: Optional[str]) -> Optional[int]:
        """Return remaining retry_after seconds if IP is currently blocked, else None."""
        if not ip:
            return None
        now_ts = datetime.now(timezone.utc).timestamp()
        bucket = self._prune(ip, now_ts)
        if len(bucket) >= self.max_attempts:
            retry_after = int(self.window_seconds - (now_ts - bucket[0]))
            return max(1, retry_after)
        return None

    def record_failure(self, ip: Optional[str]) -> None:
        if not ip:
            return
        now_ts = datetime.now(timezone.utc).timestamp()
        bucket = self._prune(ip, now_ts)
        bucket.append(now_ts)

    def clear(self, ip: Optional[str]) -> None:
        if ip and ip in self._attempts:
            del self._attempts[ip]

    def reset_all(self) -> None:
        self._attempts.clear()


default_ip_rate_limiter = IpRateLimiter()


def validate_password_strength(password: str) -> bool:
    """Enforce >= 8 chars with upper, lower, digit, and special symbol."""
    if len(password) < 8:
        return False
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(not c.isalnum() for c in password)
    return has_upper and has_lower and has_digit and has_symbol


def resolve_landing(
    system_role: str,
    course_roles: List[CourseRoleClaim],
) -> Literal["ADMIN_CONSOLE", "TEACHING", "LEARNING"]:
    """Determine default landing portal based on system and contextual roles (BR-01)."""
    if system_role.upper() == "ADMIN":
        return "ADMIN_CONSOLE"
    if any(item.role.upper() == "INSTRUCTOR" for item in course_roles):
        return "TEACHING"
    return "LEARNING"


class AuthService:
    """End-user authentication and account security service (T2-P-M1-01)."""

    def __init__(
        self,
        db: AsyncSession,
        repo: Optional[IdentityRepository] = None,
        mfa_store: Optional[IMfaSecretStore] = None,
        ip_limiter: Optional[IpRateLimiter] = None,
        course_roles_provider: Optional[CourseRolesProvider] = None,
    ):
        self.db = db
        self.repo = repo or IdentityRepository(db)
        self.mfa_store = mfa_store or default_mfa_store
        self.ip_limiter = ip_limiter or default_ip_rate_limiter
        self._course_roles_provider = course_roles_provider

    async def _resolve_course_roles(self, user_id: uuid.UUID) -> List[CourseRoleClaim]:
        provider = self._course_roles_provider or _course_roles_provider
        if provider is None:
            return []
        return await provider(self.db, user_id)

    def _assert_not_locked(self, user: User) -> None:
        if user.locked_until is None:
            return
        now = datetime.now(timezone.utc)
        locked_until = user.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if locked_until > now:
            retry_after = int((locked_until - now).total_seconds())
            raise AccountLockedException(
                retry_after_seconds=max(1, retry_after),
                locked_until=locked_until,
            )

    async def _build_me_response(self, user: User) -> MeResponse:
        course_roles = await self._resolve_course_roles(user.id)
        mfa_state = await self.mfa_store.get_state(self.db, user.id)
        return MeResponse(
            id=user.id,
            email=user.email,
            user_code=user.user_code,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            system_role=user.system_role,
            mfa_enabled=mfa_state.enabled,
            course_roles=course_roles,
            landing=resolve_landing(user.system_role, course_roles),
        )

    async def _issue_token_pair(self, user: User, remember_me: bool = False) -> TokenResponse:
        me = await self._build_me_response(user)
        course_roles_map = {str(item.course_id): item.role for item in me.course_roles}

        access_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_expires = (
            timedelta(days=REFRESH_REMEMBER_DAYS)
            if remember_me
            else timedelta(hours=REFRESH_SHORT_HOURS)
        )

        access_token = create_access_token(
            subject=str(user.id),
            claims={
                "type": "access",
                "system_role": user.system_role,
                "course_roles": course_roles_map,
            },
            expires_delta=access_expires,
        )
        refresh_token = create_access_token(
            subject=str(user.id),
            claims={
                "type": "refresh",
                "remember_me": remember_me,
            },
            expires_delta=refresh_expires,
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(access_expires.total_seconds()),
            user=me,
        )

    async def authenticate(
        self,
        identifier: str,
        password: str,
        remember_me: bool = False,
        client_ip: Optional[str] = None,
    ) -> LoginResponse:
        """Validate credentials, enforce BR-02 brute-force lock, and handle MFA step."""
        ip_retry = self.ip_limiter.check_blocked(client_ip)
        if ip_retry is not None:
            raise AccountLockedException(retry_after_seconds=ip_retry)

        user = await self.repo.get_by_identifier(identifier)
        if user is None:
            # Constant-time defense against email/code enumeration
            verify_password(password, _DUMMY_PASSWORD_HASH)
            self.ip_limiter.record_failure(client_ip)
            raise InvalidCredentialsWithAttemptsException()

        self._assert_not_locked(user)

        if not user.is_active or not verify_password(password, user.password_hash):
            self.ip_limiter.record_failure(client_ip)
            new_count, locked_until = await self.repo.increment_failed_login(
                user_id=user.id,
                lock_threshold=MAX_FAILED_ATTEMPTS,
                lock_duration_seconds=LOCK_DURATION_SECONDS,
            )
            if locked_until is not None:
                raise AccountLockedException(
                    retry_after_seconds=LOCK_DURATION_SECONDS,
                    locked_until=locked_until,
                )
            remaining = max(0, MAX_FAILED_ATTEMPTS - new_count)
            raise InvalidCredentialsWithAttemptsException(remaining_attempts=remaining)

        await self.repo.reset_failed_login(user.id)

        mfa_state = await self.mfa_store.get_state(self.db, user.id)
        if mfa_state.enabled and mfa_state.secret:
            mfa_delta = timedelta(minutes=MFA_TOKEN_EXPIRE_MINUTES)
            mfa_token = create_access_token(
                subject=str(user.id),
                claims={"type": "mfa_pending", "remember_me": remember_me},
                expires_delta=mfa_delta,
            )
            return LoginResponse(
                requires_mfa=True,
                mfa_token=mfa_token,
                expires_in=int(mfa_delta.total_seconds()),
            )

        tokens = await self._issue_token_pair(user, remember_me=remember_me)
        return LoginResponse(
            requires_mfa=False,
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
            expires_in=tokens.expires_in,
            user=tokens.user,
        )

    async def verify_mfa(
        self,
        mfa_token: str,
        code: str,
        client_ip: Optional[str] = None,
    ) -> TokenResponse:
        """Complete step-2 TOTP verification using a pending MFA token."""
        payload = decode_access_token(mfa_token)
        if payload is None or payload.get("type") != "mfa_pending" or "sub" not in payload:
            raise InvalidMfaCodeException()

        try:
            user_id = uuid.UUID(str(payload["sub"]))
        except (ValueError, TypeError) as exc:
            raise InvalidMfaCodeException() from exc

        user = await self.repo.get_by_id(user_id)
        if user is None or not user.is_active:
            raise InvalidMfaCodeException()

        self._assert_not_locked(user)

        mfa_state = await self.mfa_store.get_state(self.db, user.id)
        if not mfa_state.enabled or not mfa_state.secret or not verify_totp(mfa_state.secret, code):
            self.ip_limiter.record_failure(client_ip)
            new_count, locked_until = await self.repo.increment_failed_login(
                user_id=user.id,
                lock_threshold=MAX_FAILED_ATTEMPTS,
                lock_duration_seconds=LOCK_DURATION_SECONDS,
            )
            if locked_until is not None:
                raise AccountLockedException(
                    retry_after_seconds=LOCK_DURATION_SECONDS,
                    locked_until=locked_until,
                )
            remaining = max(0, MAX_FAILED_ATTEMPTS - new_count)
            raise InvalidMfaCodeException(remaining_attempts=remaining)

        await self.repo.reset_failed_login(user.id)
        revoke_token(mfa_token)
        remember_me = bool(payload.get("remember_me", False))
        return await self._issue_token_pair(user, remember_me=remember_me)

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        """Rotate refresh token and issue a fresh access token with updated roles."""
        payload = decode_access_token(refresh_token)
        if payload is None or payload.get("type") != "refresh" or "sub" not in payload:
            raise UnauthorizedTokenException("Refresh token khong hop le hoac da het han.")

        try:
            user_id = uuid.UUID(str(payload["sub"]))
        except (ValueError, TypeError) as exc:
            raise UnauthorizedTokenException() from exc

        user = await self.repo.get_by_id(user_id)
        if user is None or not user.is_active:
            raise UnauthorizedTokenException()

        self._assert_not_locked(user)
        revoke_token(refresh_token)
        remember_me = bool(payload.get("remember_me", False))
        return await self._issue_token_pair(user, remember_me=remember_me)

    async def get_me(self, user: User) -> MeResponse:
        """Return profile and contextual roles for the authenticated user."""
        return await self._build_me_response(user)

    async def logout(self, access_token: str) -> None:
        """Revoke the current access token via core.security token blacklist."""
        revoke_token(access_token)

    async def setup_mfa(self, user: User) -> MfaSetupResponse:
        """Generate and store a pending TOTP secret for enrollment."""
        if not await self.mfa_store.is_available(self.db):
            raise MfaStoreUnavailableException()
        secret = generate_secret()
        await self.mfa_store.save_secret(self.db, user.id, secret=secret, enabled=False)
        uri = build_otpauth_uri(secret=secret, account_name=user.email, issuer="ADLAS")
        return MfaSetupResponse(secret=secret, otpauth_uri=uri)

    async def enable_mfa(self, user: User, code: str) -> None:
        """Verify initial TOTP code and activate MFA for the user."""
        if not await self.mfa_store.is_available(self.db):
            raise MfaStoreUnavailableException()
        state = await self.mfa_store.get_state(self.db, user.id)
        if not state.secret or not verify_totp(state.secret, code):
            raise InvalidMfaCodeException()
        await self.mfa_store.set_enabled(self.db, user.id, enabled=True)

    async def disable_mfa(self, user: User, code: str) -> None:
        """Verify current TOTP code and disable MFA for the user."""
        if not await self.mfa_store.is_available(self.db):
            raise MfaStoreUnavailableException()
        state = await self.mfa_store.get_state(self.db, user.id)
        if not state.enabled or not state.secret or not verify_totp(state.secret, code):
            raise InvalidMfaCodeException()
        await self.mfa_store.clear_mfa(self.db, user.id)

    async def forgot_password(self, email: str) -> ForgotPasswordResponse:
        """
        Issue a 15-minute password reset token and enqueue an outbox event.
        Always returns a neutral response to prevent account enumeration.
        """
        user = await self.repo.get_by_email(email)
        if user is not None and user.is_active:
            reset_token = create_access_token(
                subject=str(user.id),
                claims={"type": "pwd_reset", "email": user.email},
                expires_delta=timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES),
            )
            await self.repo.enqueue_outbox_event(
                event_type="identity.password_reset_requested",
                aggregate_type="USER",
                aggregate_id=user.id,
                payload={
                    "user_id": str(user.id),
                    "email": user.email,
                    "full_name": user.full_name,
                    "reset_token": reset_token,
                    "expires_in_minutes": RESET_TOKEN_EXPIRE_MINUTES,
                },
            )
        return ForgotPasswordResponse(
            message="Neu email ton tai trong he thong, lien ket dat lai mat khau co hieu luc 15 phut da duoc gui."
        )

    async def reset_password(
        self,
        token: str,
        new_password: str,
        confirm_password: str,
    ) -> None:
        """Complete password reset using a valid 15-minute reset token."""
        if new_password != confirm_password:
            raise PasswordMismatchException()

        if not validate_password_strength(new_password):
            raise WeakPasswordException()

        payload = decode_access_token(token)
        if payload is None or payload.get("type") != "pwd_reset" or "sub" not in payload:
            raise ResetTokenInvalidException()

        try:
            user_id = uuid.UUID(str(payload["sub"]))
        except (ValueError, TypeError) as exc:
            raise ResetTokenInvalidException() from exc

        user = await self.repo.get_by_id(user_id)
        if user is None or not user.is_active:
            raise ResetTokenInvalidException()

        await self.repo.update_password_hash(user.id, hash_password(new_password))
        revoke_token(token)
