# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Assignment authoring service (T2-P-M3-01): schedule rules, Draft/Publish, Outbox events."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.assessment.authoring_schemas import (
    AssignmentAuthoringResponse,
    AssignmentCreateRequest,
    AssignmentDeleteResponse,
    AssignmentUpdateRequest,
    MilestoneResponse,
    MilestonesBatchCreateRequest,
)
from app.modules.assessment.exceptions import (
    AssessmentNotFoundException,
    AssignmentHasSubmissionsException,
    InvalidAssignmentScheduleException,
    InvalidMilestoneDatesException,
    InvalidMilestoneWeightsException,
)
from app.modules.assessment.models import Assignment, AssignmentMilestone
from app.modules.assessment.repository import AssessmentRepository
from app.modules.course.enums import ContextualRole
from app.modules.course.public_api import CoursePublicService

ADMIN_ROLES = {"ADMIN", "SUPER_ADMIN"}
EVENT_ASSIGNMENT_PUBLISHED = "assessment.assignment_published"


def is_system_admin(user: Any) -> bool:
    return str(getattr(user, "system_role", "") or "").upper() in ADMIN_ROLES


def _aware(value: Optional[datetime]) -> Optional[datetime]:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def validate_schedule(
    available_from: Optional[datetime],
    due_date: datetime,
    until_date: Optional[datetime],
) -> None:
    """E-ASN-01: require available_from <= due_date <= until_date."""
    due = _aware(due_date)
    until = _aware(until_date)
    avail = _aware(available_from)
    if until is not None and until < due:
        raise InvalidAssignmentScheduleException(
            "Until Date must be greater than or equal to Due Date."
        )
    if avail is not None and due < avail:
        raise InvalidAssignmentScheduleException(
            "Due Date must be greater than or equal to Available From."
        )


class AssignmentAuthoringService:
    """Business logic for creating, editing, publishing and deleting assignments."""

    def __init__(
        self,
        db: AsyncSession,
        repo: Optional[AssessmentRepository] = None,
        course_service: Optional[CoursePublicService] = None,
    ):
        self.db = db
        self.repo = repo or AssessmentRepository(db)
        self.course_service = course_service or CoursePublicService(db)

    async def _assert_instructor(self, course_id: uuid.UUID, user: Any) -> None:
        await self.course_service.assert_course_role(
            course_id=course_id,
            user_id=user.id,
            allowed_roles=[ContextualRole.INSTRUCTOR],
            is_admin=is_system_admin(user),
        )

    async def _load_assignment(self, assignment_id: uuid.UUID) -> Assignment:
        assignment = await self.repo.get_assignment(assignment_id)
        if assignment is None:
            raise AssessmentNotFoundException(str(assignment_id))
        return assignment

    async def _emit_published(self, assignment: Assignment, actor_id: uuid.UUID) -> None:
        payload: Dict[str, Any] = {
            "assignment_id": str(assignment.id),
            "course_id": str(assignment.course_id),
            "title": assignment.title,
            "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
            "ai_policy_level": assignment.ai_policy_level,
            "published_by": str(actor_id),
        }
        await self.repo.add_outbox_event(
            EVENT_ASSIGNMENT_PUBLISHED, "assignment", assignment.id, payload
        )

    async def create_assignment(
        self,
        course_id: uuid.UUID,
        user: Any,
        payload: AssignmentCreateRequest,
    ) -> AssignmentAuthoringResponse:
        await self._assert_instructor(course_id, user)
        validate_schedule(payload.available_from, payload.due_date, payload.until_date)
        data = payload.model_dump(exclude={"publish"})
        assignment = Assignment(
            id=uuid.uuid4(),
            course_id=course_id,
            created_by=user.id,
            is_published=bool(payload.publish),
            max_points=10.0,
            **data,
        )
        await self.repo.create_assignment(assignment)
        if payload.publish:
            await self._emit_published(assignment, user.id)
        await self.db.commit()
        return AssignmentAuthoringResponse.model_validate(assignment)

    async def update_assignment(
        self,
        assignment_id: uuid.UUID,
        user: Any,
        payload: AssignmentUpdateRequest,
    ) -> AssignmentAuthoringResponse:
        assignment = await self._load_assignment(assignment_id)
        await self._assert_instructor(assignment.course_id, user)
        changes = payload.model_dump(exclude_unset=True)
        # Non-nullable columns must not be reset to None.
        for key in list(changes):
            if changes[key] is None and key not in {
                "available_from",
                "until_date",
                "attachment_url",
                "max_attempts",
            }:
                changes.pop(key)
        validate_schedule(
            changes.get("available_from", assignment.available_from),
            changes.get("due_date", assignment.due_date),
            changes.get("until_date", assignment.until_date),
        )
        await self.repo.update_assignment(assignment, **changes)
        await self.db.commit()
        return AssignmentAuthoringResponse.model_validate(assignment)

    async def publish_assignment(
        self, assignment_id: uuid.UUID, user: Any
    ) -> AssignmentAuthoringResponse:
        assignment = await self._load_assignment(assignment_id)
        await self._assert_instructor(assignment.course_id, user)
        if not assignment.is_published:
            validate_schedule(
                assignment.available_from, assignment.due_date, assignment.until_date
            )
            await self.repo.set_published(assignment, True)
            await self._emit_published(assignment, user.id)
            await self.db.commit()
        return AssignmentAuthoringResponse.model_validate(assignment)

    async def delete_assignment(
        self, assignment_id: uuid.UUID, user: Any
    ) -> AssignmentDeleteResponse:
        assignment = await self._load_assignment(assignment_id)
        await self._assert_instructor(assignment.course_id, user)
        count = await self.repo.count_submissions(assignment_id)
        if count > 0:
            raise AssignmentHasSubmissionsException(count)
        await self.repo.delete_assignment_if_no_submissions(assignment_id)
        await self.db.commit()
        return AssignmentDeleteResponse(id=assignment_id)

    async def create_milestones(
        self,
        assignment_id: uuid.UUID,
        user: Any,
        payload: MilestonesBatchCreateRequest,
    ) -> list[MilestoneResponse]:
        """Configure milestones for an assignment with sum(weights)==100%."""
        assignment = await self._load_assignment(assignment_id)
        await self._assert_instructor(assignment.course_id, user)

        total_weight = sum(m.weight_percent for m in payload.milestones)
        if total_weight != 100:
            raise InvalidMilestoneWeightsException(float(total_weight))

        for m in payload.milestones:
            due = _aware(m.due_date)
            until = _aware(m.until_date)
            if until and due and until < due:
                raise InvalidMilestoneDatesException("Milestone until_date cannot be earlier than due_date.")

        # Remove existing milestones for fresh set
        from sqlalchemy import delete
        await self.db.execute(delete(AssignmentMilestone).where(AssignmentMilestone.assignment_id == assignment_id))

        created: list[AssignmentMilestone] = []
        for item in payload.milestones:
            ms = AssignmentMilestone(
                assignment_id=assignment.id,
                title=item.title,
                description=item.description,
                weight_percent=item.weight_percent,
                due_date=item.due_date,
                until_date=item.until_date,
                order_index=item.order_index,
            )
            self.db.add(ms)
            created.append(ms)

        await self.db.commit()
        for ms in created:
            await self.db.refresh(ms)

        return [MilestoneResponse.model_validate(m) for m in created]

    async def list_milestones(self, assignment_id: uuid.UUID) -> list[MilestoneResponse]:
        """List all milestones for an assignment in order."""
        from sqlalchemy import select
        await self._load_assignment(assignment_id)
        stmt = (
            select(AssignmentMilestone)
            .where(AssignmentMilestone.assignment_id == assignment_id)
            .order_by(AssignmentMilestone.order_index.asc())
        )
        res = await self.db.execute(stmt)
        milestones = list(res.scalars().all())
        return [MilestoneResponse.model_validate(m) for m in milestones]
