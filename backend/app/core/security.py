# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

import bcrypt
from datetime import datetime, timedelta, timezone
import hashlib
import logging
from typing import Any, Dict, Optional, Set
import uuid
from jose import JWTError, jwt
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings

logger = logging.getLogger(__name__)

# In-Memory L1 Token Blacklist Cache (backed by identity.revoked_tokens in PostgreSQL)
_token_blacklist: Set[str] = set()


def hash_password(password: str) -> str:
    """Hash plain text password directly with bcrypt (enforcing 72-byte max)."""
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against bcrypt hash."""
    pwd_bytes = plain_password.encode("utf-8")[:72]
    hash_bytes = hashed_password.encode("utf-8")
    try:
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False


def create_access_token(
    subject: str,
    claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Generate signed JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: Dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp())
    }
    if claims:
        to_encode.update(claims)

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate JWT access token. Returns None if invalid or revoked."""
    if is_token_blacklisted(token):
        return None

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def hash_token(token: str) -> str:
    """Compute SHA-256 hex digest of a JWT token for safe database persistence."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def revoke_token(token: str) -> None:
    """Add a token to the in-memory L1 blacklist to immediately revoke its session."""
    _token_blacklist.add(token)


def is_token_blacklisted(token: str) -> bool:
    """Check if token has been revoked in the L1 in-memory cache."""
    return token in _token_blacklist


async def revoke_token_persistent(
    db: AsyncSession,
    token: str,
    user_id: Optional[uuid.UUID] = None,
) -> None:
    """Persistently revoke a JWT token in PostgreSQL identity.revoked_tokens and L1 cache."""
    revoke_token(token)
    from app.modules.system.models import RevokedToken

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=7)
    try:
        claims = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False},
        )
        if claims.get("exp"):
            expires_at = datetime.fromtimestamp(int(claims["exp"]), tz=timezone.utc)
    except Exception:
        pass

    token_digest = hash_token(token)
    try:
        existing_res = await db.execute(
            select(RevokedToken).where(RevokedToken.token_hash == token_digest)
        )
        existing = existing_res.scalar_one_or_none()
        if not isinstance(existing, RevokedToken):
            db.add(
                RevokedToken(
                    token_hash=token_digest,
                    user_id=user_id,
                    revoked_at=now,
                    expires_at=expires_at,
                )
            )
            await db.flush()
    except Exception as exc:
        logger.debug("Persistent token revoke skipped (non-DB session or missing table): %s", exc)


async def is_token_revoked_persistent(db: AsyncSession, token: str) -> bool:
    """Check L1 cache first, then PostgreSQL identity.revoked_tokens."""
    if is_token_blacklisted(token):
        return True
    from app.modules.system.models import RevokedToken

    token_digest = hash_token(token)
    try:
        res = await db.execute(
            select(RevokedToken).where(RevokedToken.token_hash == token_digest)
        )
        row = res.scalar_one_or_none()
        if isinstance(row, RevokedToken):
            _token_blacklist.add(token)
            return True
    except Exception as exc:
        logger.debug("Persistent token check fallback (non-DB session or missing table): %s", exc)
    return False


async def purge_expired_revoked_tokens(db: AsyncSession) -> int:
    """Delete expired rows from identity.revoked_tokens to keep table compact."""
    from app.modules.system.models import RevokedToken

    now = datetime.now(timezone.utc)
    res = await db.execute(delete(RevokedToken).where(RevokedToken.expires_at < now))
    return int(res.rowcount or 0)
