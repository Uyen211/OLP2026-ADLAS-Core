# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""
Service implementing T2-P-M5-05:
- Muted Gradebook Policy & Post Grades (BR-09)
- Poka-Yoke Final Lock with exact 'KHOA DIEM' phrase (BR-12 / E-14)
- Emergency Unlock workflow after formal appeal (Subflow A-1)
- Immutable Audit Trail
"""

from datetime import datetime, timezone
from typing import List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.gradebook.exceptions import (
    GradebookHasMutedColumnsException,
    GradebookLockedException,
    GradebookNotFoundException,
    GradebookPokaYokeInvalidException,
)
from app.modules.gradebook.models import CourseGradebookLock
from app.modules.gradebook.repository import GradebookRepository
from app.modules.gradebook.schemas import (
    EmergencyUnlockRequest,
    GradeAuditLogResponse,
    GradebookLockPreviewResponse,
    GradebookLockRequest,
    GradebookLockResponse,
    PostGradesRequest,
    PostGradesResponse,
)
from app.modules.gradebook.structure_service import GradebookStructureService

POKA_YOKE_LOCK_PHRASE = "KHOA DIEM"


class GradebookSealingService:
    """Controls grade publication visibility, final sealing, emergency unlock, and audit history."""

    def __init__(
        self,
        db: AsyncSession,
        repo: Optional[GradebookRepository] = None,
        structure_service: Optional[GradebookStructureService] = None,
    ):
        self.db = db
        self.repo = repo or GradebookRepository(db)
        self.structure_service = structure_service or GradebookStructureService(db, self.repo)

    async def post_column_grades(
        self,
        course_id: uuid.UUID,
        column_id: uuid.UUID,
        payload: PostGradesRequest,
        actor_id: uuid.UUID,
    ) -> PostGradesResponse:
        """Unmute a column so students can view their official grades (BR-09)."""
        if await self.repo.is_course_locked(course_id):
            raise GradebookLockedException()

        col = await self.repo.get_column_by_id(column_id)
        if col is None or col.course_id != course_id:
            raise GradebookNotFoundException("cot diem")

        old_muted = col.is_muted
        col.is_muted = False
        await self.db.flush()

        graded_count = await self.repo.count_graded_entries_in_column(column_id)
        notification_queued = False
        if payload.send_notification:
            await self.repo.emit_outbox_event(
                event_type="gradebook.grades_published",
                aggregate_type="gradebook_column",
                aggregate_id=col.id,
                payload={
                    "course_id": str(course_id),
                    "column_id": str(col.id),
                    "column_title": col.title,
                    "scope": payload.scope.value,
                    "published_grades_count": graded_count,
                },
            )
            notification_queued = True

        await self.repo.add_audit_log(
            user_id=actor_id,
            action_type="POST_GRADES",
            entity_name="gradebook_columns",
            entity_id=col.id,
            old_values={"is_muted": old_muted},
            new_values={"is_muted": False, "scope": payload.scope.value},
        )

        return PostGradesResponse(
            column_id=col.id,
            is_muted=False,
            scope=payload.scope.value,
            published_grades_count=graded_count,
            notification_queued=notification_queued,
        )

    async def mute_column_grades(
        self,
        course_id: uuid.UUID,
        column_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> PostGradesResponse:
        """Re-mute a column while instructor revises grades (allowed only before final lock)."""
        if await self.repo.is_course_locked(course_id):
            raise GradebookLockedException()

        col = await self.repo.get_column_by_id(column_id)
        if col is None or col.course_id != course_id:
            raise GradebookNotFoundException("cot diem")

        col.is_muted = True
        await self.db.flush()
        await self.repo.add_audit_log(
            user_id=actor_id,
            action_type="MUTE_GRADES",
            entity_name="gradebook_columns",
            entity_id=col.id,
            old_values={"is_muted": False},
            new_values={"is_muted": True},
        )
        return PostGradesResponse(
            column_id=col.id,
            is_muted=True,
            scope="ALL",
            published_grades_count=0,
            notification_queued=False,
        )

    async def get_lock_preview(self, course_id: uuid.UUID) -> GradebookLockPreviewResponse:
        """Return pass/fail/hurdle stats and any remaining muted columns before final lock."""
        overview = await self.structure_service.get_class_overview(course_id)
        columns = await self.repo.list_columns_by_course(course_id)
        muted_titles = [c.title for c in columns if c.is_muted]
        return GradebookLockPreviewResponse(
            course_id=course_id,
            is_locked=overview.is_locked,
            total_students=overview.total_students,
            passed_count=overview.passed_count,
            failed_count=overview.failed_count,
            hurdle_failed_count=overview.hurdle_failed_count,
            pass_rate_pct=overview.pass_rate_pct,
            fail_rate_pct=overview.fail_rate_pct,
            class_average_10=overview.class_average_10,
            muted_columns=muted_titles,
            can_lock=(not overview.is_locked and len(muted_titles) == 0),
        )

    async def lock_course_gradebook(
        self,
        course_id: uuid.UUID,
        payload: GradebookLockRequest,
        actor_id: uuid.UUID,
    ) -> GradebookLockResponse:
        """
        Execute Poka-yoke Final Lock (BR-12):
        1. Exact case-sensitive match against 'KHOA DIEM' (E-LOCK-01)
        2. Zero remaining muted columns (E-GB-06)
        3. Seal course_gradebook_locks (activates PostgreSQL physical trigger)
        """
        if payload.confirmation_text != POKA_YOKE_LOCK_PHRASE:
            raise GradebookPokaYokeInvalidException()

        columns = await self.repo.list_columns_by_course(course_id)
        muted_titles = [c.title for c in columns if c.is_muted]
        if muted_titles:
            raise GradebookHasMutedColumnsException(muted_titles)

        now = datetime.now(timezone.utc)
        lock = await self.repo.get_course_lock(course_id)
        if lock is None:
            lock = CourseGradebookLock(
                course_id=course_id,
                is_locked=True,
                locked_at=now,
                locked_by=actor_id,
            )
        else:
            lock.is_locked = True
            lock.locked_at = now
            lock.locked_by = actor_id
        await self.repo.save_course_lock(lock)

        await self.repo.add_audit_log(
            user_id=actor_id,
            action_type="LOCK_GRADEBOOK",
            entity_name="course_gradebook_locks",
            entity_id=course_id,
            new_values={"is_locked": True, "locked_at": now.isoformat()},
            reason="Poka-yoke KHOA DIEM verified",
        )
        await self.repo.emit_outbox_event(
            event_type="gradebook.course_locked",
            aggregate_type="course",
            aggregate_id=course_id,
            payload={"course_id": str(course_id), "locked_by": str(actor_id), "locked_at": now.isoformat()},
        )
        locked_by_name = await self.repo.get_user_display_name(actor_id)
        return GradebookLockResponse(
            course_id=course_id,
            is_locked=True,
            locked_at=now,
            locked_by=actor_id,
            locked_by_name=locked_by_name,
        )

    async def emergency_unlock_gradebook(
        self,
        course_id: uuid.UUID,
        payload: EmergencyUnlockRequest,
        actor_id: uuid.UUID,
    ) -> GradebookLockResponse:
        """Subflow A-1: Formally unlock a sealed gradebook with decision code and >=30 char reason."""
        lock = await self.repo.get_course_lock(course_id)
        if lock is None or not lock.is_locked:
            raise GradebookNotFoundException("trang thai khoa so diem")

        now = datetime.now(timezone.utc)
        lock.is_locked = False
        lock.unlock_decision_code = payload.decision_code.strip()
        lock.unlock_reason = payload.reason.strip()
        lock.unlocked_at = now
        lock.unlocked_by = actor_id
        await self.repo.save_course_lock(lock)

        await self.repo.add_audit_log(
            user_id=actor_id,
            action_type="EMERGENCY_UNLOCK_GRADEBOOK",
            entity_name="course_gradebook_locks",
            entity_id=course_id,
            old_values={"is_locked": True},
            new_values={
                "is_locked": False,
                "unlock_decision_code": lock.unlock_decision_code,
            },
            reason=lock.unlock_reason,
        )
        actor_name = await self.repo.get_user_display_name(actor_id)
        return GradebookLockResponse(
            course_id=course_id,
            is_locked=False,
            locked_at=lock.locked_at or now,
            locked_by=lock.locked_by,
            locked_by_name=actor_name,
        )

    async def list_course_audit_logs(self, course_id: uuid.UUID) -> List[GradeAuditLogResponse]:
        """Return immutable audit history for the course gradebook, its columns, and its grades."""
        groups = await self.repo.list_groups_with_columns(course_id)
        columns = [col for grp in groups for col in grp.columns]
        grades = await self.repo.list_grades_for_columns([c.id for c in columns])
        entity_ids = (
            [course_id]
            + [g.id for g in groups]
            + [c.id for c in columns]
            + [gr.id for gr in grades]
        )
        logs = await self.repo.list_audit_logs_for_entities(entity_ids)
        return [GradeAuditLogResponse.model_validate(item) for item in logs]
