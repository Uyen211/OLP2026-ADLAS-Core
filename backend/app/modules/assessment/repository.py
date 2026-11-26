# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Async repository restricted to assessment.* tables and system.outbox_events (TV3 authoring)."""

from typing import Any, Dict, List, Optional, Sequence
import uuid
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.modules.assessment.models import (
    Assignment,
    AssignmentSubmission,
    IntegrityPledge,
    Rubric,
    RubricCriteria,
)
from app.modules.system.models import OutboxEvent


class AssessmentRepository:
    """Data access layer for assignment authoring, rubrics and integrity pledges.

    Methods only flush; the calling service owns the transaction (commit/rollback).
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Assignments
    # ------------------------------------------------------------------
    async def create_assignment(self, assignment: Assignment) -> Assignment:
        self.db.add(assignment)
        await self.db.flush()
        return assignment

    async def get_assignment(self, assignment_id: uuid.UUID) -> Optional[Assignment]:
        stmt = select(Assignment).where(Assignment.id == assignment_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def update_assignment(self, assignment: Assignment, **fields: Any) -> Assignment:
        for key, value in fields.items():
            setattr(assignment, key, value)
        await self.db.flush()
        return assignment

    async def set_published(self, assignment: Assignment, is_published: bool) -> Assignment:
        assignment.is_published = is_published
        await self.db.flush()
        return assignment

    async def list_course_assignments(
        self,
        course_id: uuid.UUID,
        published_only: bool = False,
    ) -> Sequence[Assignment]:
        stmt = select(Assignment).where(Assignment.course_id == course_id)
        if published_only:
            stmt = stmt.where(Assignment.is_published.is_(True))
        stmt = stmt.order_by(Assignment.due_date.asc())
        return (await self.db.execute(stmt)).scalars().all()

    async def count_submissions(self, assignment_id: uuid.UUID) -> int:
        stmt = select(func.count(AssignmentSubmission.id)).where(
            AssignmentSubmission.assignment_id == assignment_id
        )
        return int((await self.db.execute(stmt)).scalar_one())

    async def delete_assignment_if_no_submissions(self, assignment_id: uuid.UUID) -> bool:
        """Delete the assignment only when it has no submissions. Returns True if deleted."""
        if await self.count_submissions(assignment_id) > 0:
            return False
        assignment = await self.get_assignment(assignment_id)
        if assignment is None:
            return False
        await self.db.delete(assignment)
        await self.db.flush()
        return True

    # ------------------------------------------------------------------
    # Rubrics
    # ------------------------------------------------------------------
    async def get_rubric_with_criteria(self, assignment_id: uuid.UUID) -> Optional[Rubric]:
        stmt = (
            select(Rubric)
            .options(selectinload(Rubric.criteria))
            .where(Rubric.assignment_id == assignment_id)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def replace_rubric(
        self,
        assignment_id: uuid.UUID,
        title: str,
        total_points: Any,
        criteria: List[Dict[str, Any]],
    ) -> Rubric:
        """Create the rubric or fully replace its criteria (bumps version on update)."""
        rubric = await self.get_rubric_with_criteria(assignment_id)
        if rubric is None:
            rubric = Rubric(
                assignment_id=assignment_id,
                title=title,
                total_points=total_points,
                version=1,
            )
            self.db.add(rubric)
            await self.db.flush()
        else:
            await self.db.execute(
                delete(RubricCriteria).where(RubricCriteria.rubric_id == rubric.id)
            )
            rubric.title = title
            rubric.total_points = total_points
            rubric.version = (rubric.version or 1) + 1
            await self.db.flush()
            await self.db.refresh(rubric, attribute_names=["criteria"])

        for index, item in enumerate(criteria, start=1):
            self.db.add(
                RubricCriteria(
                    rubric_id=rubric.id,
                    lo_id=item.get("lo_id"),
                    competency_code=item.get("competency_code"),
                    title=item["title"],
                    description=item.get("description"),
                    max_points=item["max_points"],
                    rating_levels=item["rating_levels"],
                    order_index=item.get("order_index", index),
                )
            )
        await self.db.flush()
        await self.db.refresh(rubric, attribute_names=["criteria"])
        return rubric

    async def freeze_rubric(self, assignment_id: uuid.UUID) -> bool:
        rubric = await self.get_rubric_with_criteria(assignment_id)
        if rubric is None or rubric.is_frozen:
            return False
        rubric.is_frozen = True
        await self.db.flush()
        return True

    async def is_lo_referenced(self, lo_id: uuid.UUID) -> bool:
        """BR-LO-01: True if any rubric criterion references the Learning Objective."""
        stmt = select(func.count(RubricCriteria.id)).where(RubricCriteria.lo_id == lo_id)
        return int((await self.db.execute(stmt)).scalar_one()) > 0

    # ------------------------------------------------------------------
    # Integrity pledges (append-only: INSERT and SELECT only)
    # ------------------------------------------------------------------
    async def add_pledge(self, pledge: IntegrityPledge) -> IntegrityPledge:
        self.db.add(pledge)
        await self.db.flush()
        return pledge

    async def get_latest_pledge(
        self,
        assignment_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[IntegrityPledge]:
        stmt = (
            select(IntegrityPledge)
            .where(
                IntegrityPledge.assignment_id == assignment_id,
                IntegrityPledge.user_id == user_id,
            )
            .order_by(IntegrityPledge.signed_at.desc())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def has_pledge(self, assignment_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        return await self.get_latest_pledge(assignment_id, user_id) is not None

    # ------------------------------------------------------------------
    # Transactional Outbox
    # ------------------------------------------------------------------
    async def add_outbox_event(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: uuid.UUID,
        payload: Dict[str, Any],
    ) -> OutboxEvent:
        event = OutboxEvent(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
        )
        self.db.add(event)
        await self.db.flush()
        return event
