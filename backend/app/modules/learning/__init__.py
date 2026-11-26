# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Learning Materials & Socratic AI bounded context (T2-P-M2-01..04)."""

import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.course.public_api import CoursePublicService
from app.modules.learning.repository import LearningRepository


async def is_lo_referenced_by_learning(
    db: AsyncSession,
    lo_id: uuid.UUID,
) -> bool:
    """BR-LO-01 callback preventing deletion of LOs referenced by learning materials."""
    return await LearningRepository(db).is_lo_referenced(lo_id)


def register_learning_hooks() -> None:
    """Register cross-module hooks with CoursePublicService without direct foreign-schema queries."""
    CoursePublicService.register_lo_reference_checker(
        "learning_materials",
        is_lo_referenced_by_learning,
    )


register_learning_hooks()
