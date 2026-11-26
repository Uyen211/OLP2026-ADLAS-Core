# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Async SQLAlchemy repository encapsulating all queries against gradebook.* schema."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence
import uuid
from sqlalchemy import desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.modules.gradebook.models import (
    CourseGradebookLock,
    GradeAuditLog,
    GradebookColumn,
    GradebookGroup,
    GradeEntry,
)
from app.modules.system.models import OutboxEvent, User


class GradebookRepository:
    """Data access layer isolated strictly to gradebook.* and system.outbox_events."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # --- Groups & Columns ---
    async def list_groups_with_columns(self, course_id: uuid.UUID) -> List[GradebookGroup]:
        stmt = (
            select(GradebookGroup)
            .where(GradebookGroup.course_id == course_id)
            .options(selectinload(GradebookGroup.columns))
            .order_by(GradebookGroup.weight_percent.asc(), GradebookGroup.group_name.asc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_group_by_id(self, group_id: uuid.UUID) -> Optional[GradebookGroup]:
        stmt = (
            select(GradebookGroup)
            .where(GradebookGroup.id == group_id)
            .options(selectinload(GradebookGroup.columns))
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def count_grades_in_group(self, group_id: uuid.UUID) -> int:
        stmt = (
            select(func.count(GradeEntry.id))
            .join(GradebookColumn, GradeEntry.column_id == GradebookColumn.id)
            .where(GradebookColumn.group_id == group_id)
        )
        return int((await self.db.execute(stmt)).scalar() or 0)

    async def list_columns_by_course(self, course_id: uuid.UUID) -> List[GradebookColumn]:
        stmt = (
            select(GradebookColumn)
            .where(GradebookColumn.course_id == course_id)
            .order_by(GradebookColumn.title.asc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_column_by_id(self, column_id: uuid.UUID) -> Optional[GradebookColumn]:
        stmt = select(GradebookColumn).where(GradebookColumn.id == column_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_column_by_item(
        self,
        course_id: uuid.UUID,
        item_type: str,
        item_id: uuid.UUID,
    ) -> Optional[GradebookColumn]:
        stmt = select(GradebookColumn).where(
            GradebookColumn.course_id == course_id,
            GradebookColumn.item_type == item_type,
            GradebookColumn.item_id == item_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def add_group(self, group: GradebookGroup) -> GradebookGroup:
        self.db.add(group)
        await self.db.flush()
        return group

    async def delete_group(self, group: GradebookGroup) -> None:
        await self.db.delete(group)
        await self.db.flush()

    async def add_column(self, column: GradebookColumn) -> GradebookColumn:
        self.db.add(column)
        await self.db.flush()
        return column

    # --- Grades ---
    async def list_grades_for_columns(self, column_ids: Sequence[uuid.UUID]) -> List[GradeEntry]:
        if not column_ids:
            return []
        stmt = select(GradeEntry).where(GradeEntry.column_id.in_(list(column_ids)))
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_grades_for_student(
        self,
        column_ids: Sequence[uuid.UUID],
        user_id: uuid.UUID,
    ) -> List[GradeEntry]:
        if not column_ids:
            return []
        stmt = select(GradeEntry).where(
            GradeEntry.column_id.in_(list(column_ids)),
            GradeEntry.user_id == user_id,
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_grade_entry(
        self,
        column_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[GradeEntry]:
        stmt = select(GradeEntry).where(
            GradeEntry.column_id == column_id,
            GradeEntry.user_id == user_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def count_graded_entries_in_column(self, column_id: uuid.UUID) -> int:
        stmt = select(func.count(GradeEntry.id)).where(
            GradeEntry.column_id == column_id,
            GradeEntry.official_score.isnot(None),
        )
        return int((await self.db.execute(stmt)).scalar() or 0)

    async def save_grade_entry(self, entry: GradeEntry) -> GradeEntry:
        self.db.add(entry)
        await self.db.flush()
        return entry

    # --- Locks ---
    async def get_course_lock(self, course_id: uuid.UUID) -> Optional[CourseGradebookLock]:
        stmt = select(CourseGradebookLock).where(CourseGradebookLock.course_id == course_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def is_course_locked(self, course_id: uuid.UUID) -> bool:
        lock = await self.get_course_lock(course_id)
        return bool(lock is not None and lock.is_locked)

    async def save_course_lock(self, lock: CourseGradebookLock) -> CourseGradebookLock:
        self.db.add(lock)
        await self.db.flush()
        return lock

    async def enable_emergency_unlock_guc(self) -> None:
        """Authorize database trigger bypass within the current transaction for formal appeal unlock."""
        try:
            await self.db.execute(text("SET LOCAL adlas.emergency_unlock_active = 'true'"))
        except Exception:
            pass

    async def get_user_display_name(self, user_id: Optional[uuid.UUID]) -> Optional[str]:
        if user_id is None:
            return None
        stmt = select(User.full_name).where(User.id == user_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    # --- Audit Logs & Outbox ---
    async def add_audit_log(
        self,
        user_id: Optional[uuid.UUID],
        action_type: str,
        entity_name: str,
        entity_id: uuid.UUID,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
    ) -> GradeAuditLog:
        log = GradeAuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action_type=action_type,
            entity_name=entity_name,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            reason=reason,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def list_audit_logs_for_entities(
        self,
        entity_ids: Sequence[uuid.UUID],
        limit: int = 100,
    ) -> List[GradeAuditLog]:
        if not entity_ids:
            return []
        stmt = (
            select(GradeAuditLog)
            .where(GradeAuditLog.entity_id.in_(list(entity_ids)))
            .order_by(desc(GradeAuditLog.created_at))
            .limit(limit)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def emit_outbox_event(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: uuid.UUID,
        payload: Dict[str, Any],
    ) -> OutboxEvent:
        event = OutboxEvent(
            id=uuid.uuid4(),
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            status="PENDING",
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(event)
        await self.db.flush()
        return event
