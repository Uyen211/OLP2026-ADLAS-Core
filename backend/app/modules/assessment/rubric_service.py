# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Rubric service (T2-P-M3-02): 4 Mastery levels, exact Decimal 10.0 total, freeze guard."""

from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.assessment.authoring_schemas import (
    RUBRIC_TOTAL_POINTS,
    RubricCriterionResponse,
    RubricResponse,
    RubricSaveRequest,
)
from app.modules.assessment.authoring_service import is_system_admin
from app.modules.assessment.exceptions import (
    AssessmentAccessDeniedException,
    AssessmentNotFoundException,
    InvalidRubricLearningObjectiveException,
    InvalidRubricTotalPointsException,
    RubricFrozenException,
)
from app.modules.assessment.repository import AssessmentRepository
from app.modules.course.enums import ContextualRole
from app.modules.course.public_api import CoursePublicService

EVENT_RUBRIC_SAVED = "assessment.rubric_saved"


def assert_rubric_total(total: Decimal) -> None:
    """E-RUB-01: total points must be exactly Decimal('10.0')."""
    if total != RUBRIC_TOTAL_POINTS:
        raise InvalidRubricTotalPointsException(total=str(total), expected=str(RUBRIC_TOTAL_POINTS))


def _levels_to_json(levels: List[Any]) -> List[Dict[str, Any]]:
    return [
        {
            "level": lv.level,
            "label": lv.label,
            "description": lv.description,
            "points": float(lv.points),
        }
        for lv in levels
    ]


class RubricService:
    def __init__(
        self,
        db: AsyncSession,
        repo: Optional[AssessmentRepository] = None,
        course_service: Optional[CoursePublicService] = None,
    ):
        self.db = db
        self.repo = repo or AssessmentRepository(db)
        self.course_service = course_service or CoursePublicService(db)

    async def _load_assignment(self, assignment_id: uuid.UUID):
        assignment = await self.repo.get_assignment(assignment_id)
        if assignment is None:
            raise AssessmentNotFoundException(str(assignment_id))
        return assignment

    async def get_rubric(self, assignment_id: uuid.UUID, user: Any) -> RubricResponse:
        assignment = await self._load_assignment(assignment_id)
        role = await self.course_service.assert_course_role(
            course_id=assignment.course_id,
            user_id=user.id,
            allowed_roles=[ContextualRole.INSTRUCTOR, ContextualRole.TA, ContextualRole.STUDENT],
            is_admin=is_system_admin(user),
        )
        if role == ContextualRole.STUDENT and not assignment.is_published:
            raise AssessmentNotFoundException(str(assignment_id))
        rubric = await self.repo.get_rubric_with_criteria(assignment_id)
        count = await self.repo.count_submissions(assignment_id)
        if rubric is None:
            return RubricResponse(assignment_id=assignment_id, submission_count=count)
        return RubricResponse(
            assignment_id=assignment_id,
            exists=True,
            rubric_id=rubric.id,
            title=rubric.title,
            total_points=float(rubric.total_points),
            is_frozen=bool(rubric.is_frozen),
            version=rubric.version,
            submission_count=count,
            criteria=[
                RubricCriterionResponse(
                    id=c.id,
                    title=c.title,
                    description=c.description,
                    lo_id=c.lo_id,
                    competency_code=c.competency_code,
                    max_points=float(c.max_points),
                    rating_levels=list(c.rating_levels or []),
                    order_index=c.order_index,
                )
                for c in sorted(rubric.criteria, key=lambda item: item.order_index)
            ],
        )

    async def save_rubric(
        self, assignment_id: uuid.UUID, user: Any, payload: RubricSaveRequest
    ) -> RubricResponse:
        assignment = await self._load_assignment(assignment_id)
        role = await self.course_service.assert_course_role(
            course_id=assignment.course_id,
            user_id=user.id,
            allowed_roles=[ContextualRole.INSTRUCTOR],
            is_admin=is_system_admin(user),
        )
        if role != ContextualRole.INSTRUCTOR:
            raise AssessmentAccessDeniedException()

        # E-RUB-02: block edits when frozen or already used for grading.
        existing = await self.repo.get_rubric_with_criteria(assignment_id)
        count = await self.repo.count_submissions(assignment_id)
        if (existing is not None and existing.is_frozen) or count > 0:
            raise RubricFrozenException(count)

        # E-RUB-01: exact Decimal total.
        assert_rubric_total(payload.total_points())

        # Every referenced LO must belong to this course.
        lo_ids = {c.lo_id for c in payload.criteria if c.lo_id is not None}
        if lo_ids:
            valid = {lo.id for lo in await self.course_service.get_learning_objectives(assignment.course_id)}
            for lo_id in lo_ids:
                if lo_id not in valid:
                    raise InvalidRubricLearningObjectiveException(str(lo_id))

        criteria = [
            {
                "lo_id": c.lo_id,
                "competency_code": c.competency_code,
                "title": c.title,
                "description": c.description,
                "max_points": c.max_points,
                "rating_levels": _levels_to_json(c.rating_levels),
                "order_index": index,
            }
            for index, c in enumerate(payload.criteria, start=1)
        ]
        rubric = await self.repo.replace_rubric(
            assignment_id, payload.title, RUBRIC_TOTAL_POINTS, criteria
        )
        await self.repo.add_outbox_event(
            EVENT_RUBRIC_SAVED,
            "rubric",
            rubric.id,
            {
                "assignment_id": str(assignment_id),
                "rubric_id": str(rubric.id),
                "version": rubric.version,
                "total_points": str(RUBRIC_TOTAL_POINTS),
                "criteria_count": len(criteria),
                "saved_by": str(user.id),
            },
        )
        await self.db.commit()
        return await self.get_rubric(assignment_id, user)
