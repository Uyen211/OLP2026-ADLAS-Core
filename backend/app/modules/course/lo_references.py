# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Pluggable Learning Objective reference checker registry (BR-LO-01)."""

from typing import Awaitable, Callable, Dict
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

LoReferenceChecker = Callable[[AsyncSession, uuid.UUID], Awaitable[bool]]


class LoReferenceRegistry:
    """
    Allows external bounded contexts (learning, assessment, examination) to register
    reference checks without causing Course Context to query foreign schemas directly.
    """

    def __init__(self):
        self._checkers: Dict[str, LoReferenceChecker] = {}

    def register(self, name: str, checker: LoReferenceChecker) -> None:
        self._checkers[name] = checker

    def unregister(self, name: str) -> None:
        self._checkers.pop(name, None)

    def clear(self) -> None:
        self._checkers.clear()

    async def is_lo_referenced(self, db: AsyncSession, lo_id: uuid.UUID) -> bool:
        """Return True if any registered bounded context references the given LO."""
        for checker in self._checkers.values():
            if await checker(db, lo_id):
                return True
        return False


lo_reference_registry = LoReferenceRegistry()


def register_lo_reference_checker(name: str, checker: LoReferenceChecker) -> None:
    """Register a cross-context LO reference checker for BR-LO-01 enforcement."""
    lo_reference_registry.register(name, checker)
