# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Unit tests for Layer-2 end-user identity, TOTP MFA, brute-force lock, and RBAC claims."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
import uuid

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from app.core.security import create_access_token, decode_access_token, hash_password
from app.main import app
from app.modules.identity.dependencies import get_current_user
from app.modules.identity.exceptions import (
    AccountLockedException,
    InvalidCredentialsWithAttemptsException,
    InvalidMfaCodeException,
    UnauthorizedTokenException,
)
from app.modules.identity.mfa_store import IMfaSecretStore, MfaState
from app.modules.identity.schemas import CourseRoleClaim, LoginRequest
from app.modules.identity.service import (
    LOCK_DURATION_SECONDS,
    AuthService,
    IpRateLimiter,
    resolve_landing,
)
from app.modules.identity.totp import (
    generate_secret,
    generate_totp,
    generate_totp_from_bytes,
    verify_totp,
)
from app.modules.system.models import User


class _InMemoryMfaStore(IMfaSecretStore):
    """Minimal in-memory MFA store for unit testing without database columns."""

    def __init__(self, states: dict[uuid.UUID, MfaState] | None = None):
        self._states = states or {}

    async def is_available(self, db) -> bool:
        return True

    async def get_state(self, db, user_id: uuid.UUID) -> MfaState:
        return self._states.get(user_id, MfaState(enabled=False, secret=None))

    async def save_secret(self, db, user_id: uuid.UUID, secret: str, enabled: bool = False) -> None:
        self._states[user_id] = MfaState(enabled=enabled, secret=secret)

    async def set_enabled(self, db, user_id: uuid.UUID, enabled: bool) -> None:
        current = self._states.get(user_id, MfaState(enabled=False, secret=None))
        self._states[user_id] = MfaState(enabled=enabled, secret=current.secret)

    async def clear_mfa(self, db, user_id: uuid.UUID) -> None:
        self._states[user_id] = MfaState(enabled=False, secret=None)


def _make_user(
    *,
    email: str = "gv01@adlas.edu.vn",
    user_code: str = "GV202601",
    system_role: str = "USER",
    password: str = "Teacher@2026!",
    failed_login_count: int = 0,
    locked_until: datetime | None = None,
    is_active: bool = True,
) -> User:
    return User(
        id=uuid.uuid4(),
        email=email,
        user_code=user_code,
        full_name="Nguyen Van Giang Vien",
        password_hash=hash_password(password),
        system_role=system_role,
        is_active=is_active,
        failed_login_count=failed_login_count,
        locked_until=locked_until,
    )


@pytest.mark.parametrize(
    ("timestamp", "digest", "key", "expected"),
    [
        # RFC 6238 Appendix B Test Vectors (8-digit TOTP, 30s time step)
        (59, "sha1", b"12345678901234567890", "94287082"),
        (59, "sha256", b"12345678901234567890123456789012", "46119246"),
        (59, "sha512", b"1234567890123456789012345678901234567890123456789012345678901234", "90693936"),
        (1111111109, "sha1", b"12345678901234567890", "07081804"),
        (1111111109, "sha256", b"12345678901234567890123456789012", "68084774"),
        (1111111109, "sha512", b"1234567890123456789012345678901234567890123456789012345678901234", "25091201"),
        (1111111111, "sha1", b"12345678901234567890", "14050471"),
        (1111111111, "sha256", b"12345678901234567890123456789012", "67062674"),
        (1111111111, "sha512", b"1234567890123456789012345678901234567890123456789012345678901234", "99943326"),
        (1234567890, "sha1", b"12345678901234567890", "89005924"),
        (1234567890, "sha256", b"12345678901234567890123456789012", "91819424"),
        (1234567890, "sha512", b"1234567890123456789012345678901234567890123456789012345678901234", "93441116"),
        (2000000000, "sha1", b"12345678901234567890", "69279037"),
        (2000000000, "sha256", b"12345678901234567890123456789012", "90698825"),
        (2000000000, "sha512", b"1234567890123456789012345678901234567890123456789012345678901234", "38618901"),
        (20000000000, "sha1", b"12345678901234567890", "65353130"),
        (20000000000, "sha256", b"12345678901234567890123456789012", "77737706"),
        (20000000000, "sha512", b"1234567890123456789012345678901234567890123456789012345678901234", "47863826"),
    ],
)
def test_totp_matches_rfc6238_reference_vectors(
    timestamp: int,
    digest: str,
    key: bytes,
    expected: str,
):
    """Verify TOTP output matches all RFC 6238 Appendix B reference vectors."""
    actual = generate_totp_from_bytes(
        key=key,
        timestamp=timestamp,
        time_step=30,
        digits=8,
        digest=digest,
    )
    assert actual == expected


def test_totp_accepts_one_step_clock_drift_and_rejects_two():
    """Verify +/-1 step (30s) clock drift is accepted and +/-2 steps (60s) is rejected."""
    secret = generate_secret()
    base_ts = 1_700_000_010
    code = generate_totp(secret, timestamp=base_ts)

    assert verify_totp(secret, code, timestamp=base_ts, window=1) is True
    assert verify_totp(secret, code, timestamp=base_ts - 30, window=1) is True
    assert verify_totp(secret, code, timestamp=base_ts + 30, window=1) is True
    assert verify_totp(secret, code, timestamp=base_ts - 60, window=1) is False
    assert verify_totp(secret, code, timestamp=base_ts + 60, window=1) is False


def test_login_blank_fields_rejected():
    """E-1: Blank identifier or empty password must fail validation (422)."""
    with pytest.raises(ValidationError):
        LoginRequest(identifier="   ", password="Password@1")

    with pytest.raises(ValidationError):
        LoginRequest(identifier="gv01@adlas.edu.vn", password="")

    with TestClient(app) as client:
        res = client.post(
            "/api/v1/auth/login",
            json={"identifier": "", "password": ""},
        )
        assert res.status_code == 422


@pytest.mark.asyncio
async def test_login_wrong_password_increments_counter_and_returns_e5():
    """E-5: Wrong password atomically increments counter and returns remaining attempts."""
    mock_db = AsyncMock()
    user = _make_user(password="Correct@2026")

    repo = MagicMock()
    repo.get_by_identifier = AsyncMock(return_value=user)
    repo.increment_failed_login = AsyncMock(return_value=(1, None))

    service = AuthService(
        db=mock_db,
        repo=repo,
        mfa_store=_InMemoryMfaStore(),
        ip_limiter=IpRateLimiter(),
        course_roles_provider=AsyncMock(return_value=[]),
    )

    with pytest.raises(InvalidCredentialsWithAttemptsException) as exc_info:
        await service.authenticate("gv01@adlas.edu.vn", "Wrong@2026", client_ip="10.0.0.1")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "E-5"
    assert exc_info.value.detail["remaining_attempts"] == 4
    repo.increment_failed_login.assert_awaited_once()


@pytest.mark.asyncio
async def test_fifth_failure_locks_account_for_900_seconds():
    """BR-02 / E-6: 5th consecutive failed login locks account for 900 seconds."""
    mock_db = AsyncMock()
    user = _make_user(password="Correct@2026", failed_login_count=4)
    lock_until = datetime.now(timezone.utc) + timedelta(seconds=LOCK_DURATION_SECONDS)

    repo = MagicMock()
    repo.get_by_identifier = AsyncMock(return_value=user)
    repo.increment_failed_login = AsyncMock(return_value=(5, lock_until))

    service = AuthService(
        db=mock_db,
        repo=repo,
        mfa_store=_InMemoryMfaStore(),
        ip_limiter=IpRateLimiter(),
        course_roles_provider=AsyncMock(return_value=[]),
    )

    with pytest.raises(AccountLockedException) as exc_info:
        await service.authenticate("gv01@adlas.edu.vn", "Wrong@2026", client_ip="10.0.0.2")

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail["code"] == "E-6"
    assert exc_info.value.detail["retry_after_seconds"] == 900
    assert "locked_until" in exc_info.value.detail


@pytest.mark.asyncio
async def test_locked_account_rejected_even_with_correct_password():
    """BR-02: Locked account must still be rejected with E-6 even if password is valid."""
    mock_db = AsyncMock()
    user = _make_user(
        password="Correct@2026",
        failed_login_count=5,
        locked_until=datetime.now(timezone.utc) + timedelta(seconds=600),
    )

    repo = MagicMock()
    repo.get_by_identifier = AsyncMock(return_value=user)
    repo.reset_failed_login = AsyncMock()

    service = AuthService(
        db=mock_db,
        repo=repo,
        mfa_store=_InMemoryMfaStore(),
        ip_limiter=IpRateLimiter(),
        course_roles_provider=AsyncMock(return_value=[]),
    )

    with pytest.raises(AccountLockedException) as exc_info:
        await service.authenticate("gv01@adlas.edu.vn", "Correct@2026", client_ip="10.0.0.3")

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail["code"] == "E-6"
    assert exc_info.value.detail["retry_after_seconds"] >= 1
    repo.reset_failed_login.assert_not_awaited()


@pytest.mark.asyncio
async def test_successful_login_resets_counter():
    """BR-02: Successful authentication resets failed_login_count and locked_until."""
    mock_db = AsyncMock()
    user = _make_user(password="Correct@2026", failed_login_count=3)

    repo = MagicMock()
    repo.get_by_identifier = AsyncMock(return_value=user)
    repo.reset_failed_login = AsyncMock()

    service = AuthService(
        db=mock_db,
        repo=repo,
        mfa_store=_InMemoryMfaStore(),
        ip_limiter=IpRateLimiter(),
        course_roles_provider=AsyncMock(return_value=[]),
    )

    result = await service.authenticate("gv01@adlas.edu.vn", "Correct@2026", client_ip="10.0.0.4")

    assert result.requires_mfa is False
    assert result.access_token is not None
    assert result.refresh_token is not None
    repo.reset_failed_login.assert_awaited_once_with(user.id)


@pytest.mark.asyncio
async def test_mfa_enabled_returns_pending_token_only():
    """MFA step 1 returns mfa_pending token without issuing access/refresh tokens."""
    mock_db = AsyncMock()
    user = _make_user(password="Correct@2026")
    secret = generate_secret()
    mfa_store = _InMemoryMfaStore({user.id: MfaState(enabled=True, secret=secret)})

    repo = MagicMock()
    repo.get_by_identifier = AsyncMock(return_value=user)
    repo.reset_failed_login = AsyncMock()

    service = AuthService(
        db=mock_db,
        repo=repo,
        mfa_store=mfa_store,
        ip_limiter=IpRateLimiter(),
    )

    login_res = await service.authenticate("gv01@adlas.edu.vn", "Correct@2026")
    assert login_res.requires_mfa is True
    assert login_res.mfa_token is not None
    assert login_res.access_token is None
    assert login_res.refresh_token is None

    payload = decode_access_token(login_res.mfa_token)
    assert payload is not None
    assert payload["type"] == "mfa_pending"


@pytest.mark.asyncio
async def test_wrong_otp_returns_e_auth_03():
    """E-AUTH-03: Wrong 6-digit OTP increments failed counter and returns 401 E-AUTH-03."""
    mock_db = AsyncMock()
    user = _make_user(password="Correct@2026")
    secret = generate_secret()
    mfa_store = _InMemoryMfaStore({user.id: MfaState(enabled=True, secret=secret)})

    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=user)
    repo.increment_failed_login = AsyncMock(return_value=(1, None))

    service = AuthService(
        db=mock_db,
        repo=repo,
        mfa_store=mfa_store,
        ip_limiter=IpRateLimiter(),
    )
    mfa_token = create_access_token(
        subject=str(user.id),
        claims={"type": "mfa_pending", "remember_me": False},
        expires_delta=timedelta(minutes=5),
    )

    wrong_code = "000000" if generate_totp(secret) != "000000" else "999999"
    with pytest.raises(InvalidMfaCodeException) as exc_info:
        await service.verify_mfa(mfa_token=mfa_token, code=wrong_code, client_ip="10.0.0.5")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "E-AUTH-03"
    assert exc_info.value.detail["remaining_attempts"] == 4


@pytest.mark.asyncio
async def test_mfa_pending_token_cannot_access_protected_route():
    """Security: mfa_pending token must be rejected by get_current_user dependency."""
    user_id = uuid.uuid4()
    mfa_token = create_access_token(
        subject=str(user_id),
        claims={"type": "mfa_pending"},
        expires_delta=timedelta(minutes=5),
    )
    mock_db = AsyncMock()

    with pytest.raises(UnauthorizedTokenException) as exc_info:
        await get_current_user(token=mfa_token, db=mock_db)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_access_token_contains_course_roles_claim():
    """BR-01: Access token includes system_role and contextual course_roles map."""
    mock_db = AsyncMock()
    user = _make_user(password="Correct@2026")
    course_id = uuid.uuid4()

    async def fake_provider(db, uid):
        return [
            CourseRoleClaim(
                course_id=course_id,
                role="INSTRUCTOR",
                course_code="CS101",
                course_name="Nhap mon Lap trinh",
            )
        ]

    repo = MagicMock()
    repo.get_by_identifier = AsyncMock(return_value=user)
    repo.reset_failed_login = AsyncMock()

    service = AuthService(
        db=mock_db,
        repo=repo,
        mfa_store=_InMemoryMfaStore(),
        ip_limiter=IpRateLimiter(),
        course_roles_provider=fake_provider,
    )

    res = await service.authenticate("gv01@adlas.edu.vn", "Correct@2026")
    assert res.access_token is not None
    claims = decode_access_token(res.access_token)
    assert claims is not None
    assert claims["type"] == "access"
    assert claims["system_role"] == "USER"
    assert claims["course_roles"] == {str(course_id): "INSTRUCTOR"}


def test_landing_resolution_admin_teacher_student():
    """BR-01: Landing portal resolves to ADMIN_CONSOLE, TEACHING, or LEARNING."""
    cid = uuid.uuid4()
    assert resolve_landing("ADMIN", []) == "ADMIN_CONSOLE"
    assert (
        resolve_landing(
            "USER",
            [CourseRoleClaim(course_id=cid, role="INSTRUCTOR")],
        )
        == "TEACHING"
    )
    assert (
        resolve_landing(
            "USER",
            [CourseRoleClaim(course_id=cid, role="STUDENT")],
        )
        == "LEARNING"
    )
    assert resolve_landing("USER", []) == "LEARNING"


@pytest.mark.asyncio
async def test_forgot_password_response_is_identical_for_unknown_email():
    """Security: Forgot password returns identical neutral response for known and unknown emails."""
    mock_db = AsyncMock()
    existing = _make_user(email="known@adlas.edu.vn")

    repo = MagicMock()
    repo.enqueue_outbox_event = AsyncMock()

    service = AuthService(db=mock_db, repo=repo, mfa_store=_InMemoryMfaStore())

    repo.get_by_email = AsyncMock(return_value=existing)
    known_res = await service.forgot_password("known@adlas.edu.vn")

    repo.get_by_email = AsyncMock(return_value=None)
    unknown_res = await service.forgot_password("nobody@adlas.edu.vn")

    assert known_res.message == unknown_res.message
    repo.enqueue_outbox_event.assert_awaited_once()
