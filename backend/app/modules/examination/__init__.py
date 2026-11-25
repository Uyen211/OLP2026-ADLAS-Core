# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Examination & CBT Engine bounded context (T2-P-M4-01..04)."""

import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.course.public_api import CoursePublicService
from app.modules.examination.repository import ExaminationRepository


async def is_lo_referenced_by_examination(
    db: AsyncSession,
    lo_id: uuid.UUID,
) -> bool:
    """BR-LO-01 callback preventing deletion of LOs referenced by active questions or snapshots."""
    return await ExaminationRepository(db).is_lo_referenced(lo_id)


def register_examination_hooks() -> None:
    """Register cross-module hooks with CoursePublicService without direct foreign-schema queries."""
    CoursePublicService.register_lo_reference_checker(
        "examination",
        is_lo_referenced_by_examination,
    )


register_examination_hooks()
