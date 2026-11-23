# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Public service interface exposed by Identity Context for other bounded contexts."""

from dataclasses import dataclass
import secrets
import string
from typing import Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import hash_password
from app.modules.identity.repository import IdentityRepository
from app.modules.system.models import User


@dataclass(frozen=True)
class StudentAccountInput:
    """Input DTO for provisioning or resolving a student account during roster import."""

    user_code: str
    full_name: str
    email: str


@dataclass(frozen=True)
class StudentAccountResult:
    """Result DTO returned to Course Context without exposing credentials."""

    user_id: uuid.UUID
    user_code: Optional[str]
    full_name: str
    email: str
    created: bool


def _generate_random_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    chars = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*"),
    ]
    chars.extend(secrets.choice(alphabet) for _ in range(max(0, length - 4)))
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


class IdentityPublicService:
    """Public interface for cross-context user lookup and student account provisioning."""

    def __init__(self, db: AsyncSession, repo: Optional[IdentityRepository] = None):
        self.db = db
        self.repo = repo or IdentityRepository(db)

    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        return await self.repo.get_by_id(user_id)

    async def get_or_create_students(
        self,
        items: List[StudentAccountInput],
    ) -> List[StudentAccountResult]:
        """
        Resolve existing student accounts by email/user_code or create new ones
        with a hashed random password (never returned in plaintext).
        """
        if not items:
            return []

        existing = await self.repo.get_users_by_emails_or_codes(
            emails=[item.email for item in items],
            user_codes=[item.user_code for item in items],
        )
        by_email: Dict[str, User] = {u.email.lower(): u for u in existing}
        by_code: Dict[str, User] = {
            u.user_code.upper(): u for u in existing if u.user_code
        }

        results: List[StudentAccountResult] = []
        for item in items:
            norm_email = item.email.strip().lower()
            norm_code = item.user_code.strip().upper()

            found = by_email.get(norm_email) or by_code.get(norm_code)
            if found is not None:
                results.append(
                    StudentAccountResult(
                        user_id=found.id,
                        user_code=found.user_code,
                        full_name=found.full_name,
                        email=found.email,
                        created=False,
                    )
                )
                continue

            created_user = await self.repo.create_user(
                email=norm_email,
                user_code=norm_code,
                full_name=item.full_name.strip(),
                password_hash=hash_password(_generate_random_password()),
                system_role="USER",
            )
            by_email[created_user.email.lower()] = created_user
            if created_user.user_code:
                by_code[created_user.user_code.upper()] = created_user

            results.append(
                StudentAccountResult(
                    user_id=created_user.id,
                    user_code=created_user.user_code,
                    full_name=created_user.full_name,
                    email=created_user.email,
                    created=True,
                )
            )

        return results
