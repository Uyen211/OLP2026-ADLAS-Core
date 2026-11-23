# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""FastAPI authentication dependencies for end-user routes."""

from dataclasses import dataclass
from typing import Optional
import uuid
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import decode_access_token
from app.modules.identity.exceptions import UnauthorizedTokenException
from app.modules.identity.repository import IdentityRepository
from app.modules.system.models import User


@dataclass(frozen=True)
class CurrentUser:
    """Authenticated end-user context attached to protected requests."""

    user: User
    token: str


def get_bearer_token(authorization: Optional[str] = Header(None)) -> str:
    """Extract Bearer JWT token from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedTokenException()
    token = authorization[len("Bearer ") :].strip()
    if not token:
        raise UnauthorizedTokenException()
    return token


async def get_current_user(
    token: str = Depends(get_bearer_token),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """
    Validate Bearer JWT, strictly rejecting non-access tokens (e.g. mfa_pending, refresh, pwd_reset),
    and load the active user record from identity.users.
    """
    payload = decode_access_token(token)
    if payload is None or payload.get("type") != "access" or "sub" not in payload:
        raise UnauthorizedTokenException()

    try:
        user_id = uuid.UUID(str(payload["sub"]))
    except (ValueError, TypeError) as exc:
        raise UnauthorizedTokenException() from exc

    repo = IdentityRepository(db)
    user = await repo.get_by_id(user_id)
    if user is None or not user.is_active:
        raise UnauthorizedTokenException()

    return CurrentUser(user=user, token=token)
