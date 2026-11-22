# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Abstraction for storing and retrieving TOTP MFA secrets (Plan Q1 - Option A)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import uuid
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.identity.exceptions import MfaStoreUnavailableException


@dataclass(frozen=True)
class MfaState:
    """Immutable MFA status snapshot for a user."""

    enabled: bool
    secret: Optional[str] = None


class IMfaSecretStore(ABC):
    """Abstract store for reading and persisting user TOTP MFA state."""

    @abstractmethod
    async def is_available(self, db: AsyncSession) -> bool:
        """Return True if persistent MFA storage is ready."""

    @abstractmethod
    async def get_state(self, db: AsyncSession, user_id: uuid.UUID) -> MfaState:
        """Read the user's current MFA state."""

    @abstractmethod
    async def save_secret(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        secret: str,
        enabled: bool = False,
    ) -> None:
        """Persist a new TOTP secret for the user."""

    @abstractmethod
    async def set_enabled(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        enabled: bool,
    ) -> None:
        """Toggle MFA enabled flag for the user."""

    @abstractmethod
    async def clear_mfa(self, db: AsyncSession, user_id: uuid.UUID) -> None:
        """Disable MFA and clear the stored secret."""


class DisabledMfaStore(IMfaSecretStore):
    """Fallback store used when MFA columns have not been added to identity.users."""

    async def is_available(self, db: AsyncSession) -> bool:
        return False

    async def get_state(self, db: AsyncSession, user_id: uuid.UUID) -> MfaState:
        return MfaState(enabled=False, secret=None)

    async def save_secret(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        secret: str,
        enabled: bool = False,
    ) -> None:
        raise MfaStoreUnavailableException()

    async def set_enabled(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        enabled: bool,
    ) -> None:
        raise MfaStoreUnavailableException()

    async def clear_mfa(self, db: AsyncSession, user_id: uuid.UUID) -> None:
        raise MfaStoreUnavailableException()


def _check_mfa_columns_sync(sync_conn) -> bool:
    """Inspect identity.users synchronously to verify mfa_enabled and mfa_secret columns."""
    inspector = inspect(sync_conn)
    columns = {col["name"] for col in inspector.get_columns("users", schema="identity")}
    return "mfa_enabled" in columns and "mfa_secret" in columns


class ColumnMfaStore(IMfaSecretStore):
    """
    Column-backed MFA store on identity.users.
    Automatically detects column availability and falls back to DisabledMfaStore
    if `mfa_enabled` and `mfa_secret` are not yet present in the database.
    """

    def __init__(self, fallback: Optional[IMfaSecretStore] = None):
        self._fallback: IMfaSecretStore = fallback or DisabledMfaStore()
        self._columns_available: Optional[bool] = None

    def reset_cache(self) -> None:
        """Clear cached column detection result (useful for tests)."""
        self._columns_available = None

    async def is_available(self, db: AsyncSession) -> bool:
        if self._columns_available is not None:
            return self._columns_available

        try:
            conn = await db.connection()
            self._columns_available = await conn.run_sync(_check_mfa_columns_sync)
        except Exception:
            self._columns_available = False
        return self._columns_available

    async def get_state(self, db: AsyncSession, user_id: uuid.UUID) -> MfaState:
        if not await self.is_available(db):
            return await self._fallback.get_state(db, user_id)

        result = await db.execute(
            text(
                "SELECT mfa_enabled, mfa_secret FROM identity.users WHERE id = :user_id"
            ),
            {"user_id": user_id},
        )
        row = result.first()
        if row is None:
            return MfaState(enabled=False, secret=None)
        return MfaState(enabled=bool(row[0]), secret=row[1])

    async def save_secret(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        secret: str,
        enabled: bool = False,
    ) -> None:
        if not await self.is_available(db):
            await self._fallback.save_secret(db, user_id, secret, enabled=enabled)
            return

        await db.execute(
            text(
                "UPDATE identity.users "
                "SET mfa_secret = :secret, mfa_enabled = :enabled, updated_at = NOW() "
                "WHERE id = :user_id"
            ),
            {"secret": secret, "enabled": enabled, "user_id": user_id},
        )
        await db.flush()

    async def set_enabled(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        enabled: bool,
    ) -> None:
        if not await self.is_available(db):
            await self._fallback.set_enabled(db, user_id, enabled)
            return

        await db.execute(
            text(
                "UPDATE identity.users "
                "SET mfa_enabled = :enabled, updated_at = NOW() "
                "WHERE id = :user_id"
            ),
            {"enabled": enabled, "user_id": user_id},
        )
        await db.flush()

    async def clear_mfa(self, db: AsyncSession, user_id: uuid.UUID) -> None:
        if not await self.is_available(db):
            await self._fallback.clear_mfa(db, user_id)
            return

        await db.execute(
            text(
                "UPDATE identity.users "
                "SET mfa_enabled = FALSE, mfa_secret = NULL, updated_at = NOW() "
                "WHERE id = :user_id"
            ),
            {"user_id": user_id},
        )
        await db.flush()


default_mfa_store = ColumnMfaStore()
