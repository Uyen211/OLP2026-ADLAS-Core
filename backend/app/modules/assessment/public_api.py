# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Public read-only contract exposed by Assessment Context for TV1 (SpeedGrader/Gradebook) and TV2."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional, Tuple
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.assessment.exceptions import AssessmentNotFoundException
from app.modules.assessment.repository import AssessmentRepository
from app.modules.course.public_api import CoursePublicService


@dataclass(frozen=True)
class RubricCriterionDTO:
    id: uuid.UUID
    lo_id: Optional[uuid.UUID]
    competency_code: Optional[str]
    title: str
    description: Optional[str]
    max_points: Decimal
    rating_levels: Any
    order_index: int


@dataclass(frozen=True)
class RubricDTO:
    id: uuid.UUID
    assignment_id: uuid.UUID
    title: str
    total_points: Decimal
    is_frozen: bool
    version: int
    criteria: Tuple[RubricCriterionDTO, ...]


@dataclass(frozen=True)
class AssignmentPolicyDTO:
    assignment_id: uuid.UUID
    course_id: uuid.UUID
    is_published: bool
    available_from: Optional[datetime]
    due_date: datetime
    until_date: Optional[datetime]
    late_penalty_percent: Decimal
    ai_policy_level: str
    max_points: Decimal
    max_attempts: Optional[int]
    is_viva_required: bool


class AssessmentPublicService:
    """Cross-module read-only interface that never exposes assessment.* ORM objects."""

    def __init__(self, db: AsyncSession, repo: Optional[AssessmentRepository] = None):
        self.db = db
        self.repo = repo or AssessmentRepository(db)

    async def get_assignment_rubric(self, assignment_id: uuid.UUID) -> Optional[RubricDTO]:
        rubric = await self.repo.get_rubric_with_criteria(assignment_id)
        if rubric is None:
            return None
        criteria: List[RubricCriterionDTO] = [
            RubricCriterionDTO(
                id=c.id,
                lo_id=c.lo_id,
                competency_code=c.competency_code,
                title=c.title,
                description=c.description,
                max_points=Decimal(str(c.max_points)),
                rating_levels=c.rating_levels,
                order_index=c.order_index,
            )
            for c in sorted(rubric.criteria, key=lambda item: item.order_index)
        ]
        return RubricDTO(
            id=rubric.id,
            assignment_id=rubric.assignment_id,
            title=rubric.title,
            total_points=Decimal(str(rubric.total_points)),
            is_frozen=bool(rubric.is_frozen),
            version=rubric.version,
            criteria=tuple(criteria),
        )

    async def get_assignment_policy(self, assignment_id: uuid.UUID) -> AssignmentPolicyDTO:
        a = await self.repo.get_assignment(assignment_id)
        if a is None:
            raise AssessmentNotFoundException(str(assignment_id))
        return AssignmentPolicyDTO(
            assignment_id=a.id,
            course_id=a.course_id,
            is_published=bool(a.is_published),
            available_from=a.available_from,
            due_date=a.due_date,
            until_date=a.until_date,
            late_penalty_percent=Decimal(str(a.late_penalty_percent)),
            ai_policy_level=a.ai_policy_level,
            max_points=Decimal(str(a.max_points if a.max_points is not None else 10)),
            max_attempts=a.max_attempts,
            is_viva_required=bool(a.is_viva_required),
        )

    async def has_signed_pledge(self, assignment_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        return await self.repo.has_pledge(assignment_id, user_id)


async def is_lo_referenced_by_assessment(db: AsyncSession, lo_id: uuid.UUID) -> bool:
    """BR-LO-01 callback: block deletion of LOs referenced by rubric criteria."""
    return await AssessmentRepository(db).is_lo_referenced(lo_id)


def register_assessment_hooks() -> None:
    """Register cross-module hooks with CoursePublicService (no foreign-schema queries)."""
    CoursePublicService.register_lo_reference_checker(
        "assessment",
        is_lo_referenced_by_assessment,
    )


register_assessment_hooks()
