# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

import uuid
import pytest
from unittest.mock import AsyncMock
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    is_token_blacklisted,
    revoke_token,
    verify_password,
)
from app.modules.system.models import User
from app.modules.system.schemas import (
    UserCreateRequest,
    UserStatusUpdateRequest,
)
from app.modules.system.service import SystemAuthService, generate_secure_password


def test_password_generator_meets_br02():
    """BR-02: Auto-generated password must have >= 8 chars, 1 upper, 1 lower, 1 digit, 1 symbol."""
    pwd = generate_secure_password(10)
    assert len(pwd) == 10
    assert any(c.isupper() for c in pwd), "Must contain at least one uppercase letter"
    assert any(c.islower() for c in pwd), "Must contain at least one lowercase letter"
    assert any(c.isdigit() for c in pwd), "Must contain at least one digit"
    assert any(c in "!@#$%^&*" for c in pwd), "Must contain at least one symbol"


def test_password_hashing_and_verification():
    """Verify that bcrypt hashing and verification work as expected."""
    plain = "SecureP@ssw0rd2026"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword123", hashed) is False


def test_token_creation_and_revocation():
    """Verify that JWT can be created, decoded, and immediately revoked via blacklist."""
    user_id = str(uuid.uuid4())
    token = create_access_token(subject=user_id, claims={"role": "ADMIN"})
    assert token is not None

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["role"] == "ADMIN"

    # Revoke token
    revoke_token(token)
    assert is_token_blacklisted(token) is True
    assert decode_access_token(token) is None


def test_user_create_schema_validation():
    """AC-01 / E-2: Validate inputs on UserCreateRequest schema."""
    # Valid payload
    valid_payload = UserCreateRequest(
        full_name="Le Van Giảng Viên",
        email="giangvien@truong.edu.vn",
        user_code="GV202601",
        system_role="USER"
    )
    assert valid_payload.email == "giangvien@truong.edu.vn"
    assert valid_payload.user_code == "GV202601"

    # Invalid email format (E-2)
    with pytest.raises(ValidationError):
        UserCreateRequest(
            full_name="Test User",
            email="invalid-email-format",
            user_code="GV202602"
        )

    # Invalid user_code with special characters (E-2)
    with pytest.raises(ValidationError):
        UserCreateRequest(
            full_name="Test User",
            email="valid@truong.edu.vn",
            user_code="gv-2026#abc"
        )

    # Invalid system role
    with pytest.raises(ValidationError):
        UserCreateRequest(
            full_name="Test User",
            email="valid@truong.edu.vn",
            system_role="SUPER_GOD_MODE"
        )


@pytest.mark.asyncio
async def test_create_user_duplicate_email_rejection():
    """AC-03 / E-4: System must reject user creation if email already exists."""
    mock_db = AsyncMock()
    service = SystemAuthService(mock_db)

    # Mock repository returning existing user
    existing_user = User(
        id=uuid.uuid4(),
        email="existing@truong.edu.vn",
        full_name="Existing User",
        password_hash="hash"
    )
    service.repo.get_user_by_email = AsyncMock(return_value=existing_user)

    payload = UserCreateRequest(
        full_name="New User",
        email="existing@truong.edu.vn",
        user_code="SV202601"
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.create_user(payload)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error_code"] == "E-4"
    assert "email" in exc_info.value.detail["field"]


@pytest.mark.asyncio
async def test_prevent_admin_self_deactivation():
    """AC-04 / E-SYS-01: Admin cannot deactivate their own account."""
    mock_db = AsyncMock()
    service = SystemAuthService(mock_db)

    admin_id = uuid.uuid4()
    admin_user = User(
        id=admin_id,
        email="admin@adlas.edu.vn",
        full_name="System Admin",
        system_role="ADMIN",
        password_hash="hash",
        is_active=True
    )
    service.repo.get_user_by_id = AsyncMock(return_value=admin_user)

    payload = UserStatusUpdateRequest(is_active=False, reason="Self deactivation test")

    with pytest.raises(HTTPException) as exc_info:
        await service.update_user_status(
            target_user_id=admin_id,
            payload=payload,
            actor=admin_user
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error_code"] == "E-SYS-01"


@pytest.mark.asyncio
async def test_prevent_last_admin_deactivation_br03():
    """BR-03: System must maintain at least one active system administrator."""
    mock_db = AsyncMock()
    service = SystemAuthService(mock_db)

    current_admin_id = uuid.uuid4()
    current_admin = User(
        id=current_admin_id,
        email="admin1@adlas.edu.vn",
        full_name="Current Admin",
        system_role="ADMIN",
        password_hash="hash",
        is_active=True
    )

    target_admin_id = uuid.uuid4()
    target_admin = User(
        id=target_admin_id,
        email="admin2@adlas.edu.vn",
        full_name="Target Admin",
        system_role="ADMIN",
        password_hash="hash",
        is_active=True
    )

    service.repo.get_user_by_id = AsyncMock(return_value=target_admin)
    # Only 1 active admin remains
    service.repo.count_active_admins = AsyncMock(return_value=1)

    payload = UserStatusUpdateRequest(is_active=False, reason="Deactivating last admin")

    with pytest.raises(HTTPException) as exc_info:
        await service.update_user_status(
            target_user_id=target_admin_id,
            payload=payload,
            actor=current_admin
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error_code"] == "BR-03"
