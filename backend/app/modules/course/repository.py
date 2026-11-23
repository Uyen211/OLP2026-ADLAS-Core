# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Async SQLAlchemy repository restricted strictly to course.* tables."""

from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
import uuid
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.course.enums import ContextualRole, EnrollmentStatus
from app.modules.course.models import (
    Course,
    CourseEnrollment,
    CourseGroup,
    CourseGroupMember,
    LearningObjective,
)
from app.modules.system.models import OutboxEvent, User


class CourseRepository:
    """Data access layer for course.*, plus read-only User joins and transactional Outbox."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Courses & Templates
    # ------------------------------------------------------------------
    async def create_course(self, course: Course) -> Course:
        self.db.add(course)
        await self.db.flush()
        return course

    async def get_course_by_id(self, course_id: uuid.UUID) -> Optional[Course]:
        stmt = select(Course).where(Course.id == course_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_course_by_join_code(self, join_code: str) -> Optional[Course]:
        stmt = select(Course).where(Course.join_code == join_code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def join_code_exists(self, join_code: str) -> bool:
        stmt = select(func.count(Course.id)).where(Course.join_code == join_code)
        result = await self.db.execute(stmt)
        return (result.scalar() or 0) > 0

    async def list_courses_for_user(
        self,
        user_id: uuid.UUID,
        is_admin: bool = False,
        role_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> List[Tuple[Course, Optional[str]]]:
        """List courses visible to user along with their contextual_role."""
        if is_admin:
            stmt = (
                select(Course, CourseEnrollment.contextual_role)
                .outerjoin(
                    CourseEnrollment,
                    (CourseEnrollment.course_id == Course.id)
                    & (CourseEnrollment.user_id == user_id)
                    & (CourseEnrollment.enrollment_status == EnrollmentStatus.ACTIVE.value),
                )
            )
        else:
            stmt = (
                select(Course, CourseEnrollment.contextual_role)
                .join(CourseEnrollment, CourseEnrollment.course_id == Course.id)
                .where(
                    CourseEnrollment.user_id == user_id,
                    CourseEnrollment.enrollment_status == EnrollmentStatus.ACTIVE.value,
                )
            )

        if role_filter:
            stmt = stmt.where(CourseEnrollment.contextual_role == role_filter.upper())
        if status_filter:
            stmt = stmt.where(Course.status == status_filter.upper())
        if search_query:
            q = f"%{search_query.strip()}%"
            stmt = stmt.where(
                or_(
                    Course.name.ilike(q),
                    Course.course_code.ilike(q),
                    Course.section_code.ilike(q),
                )
            )

        stmt = stmt.order_by(Course.created_at.desc())
        result = await self.db.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def list_templates(self) -> List[Course]:
        stmt = (
            select(Course)
            .where(Course.is_template.is_(True))
            .order_by(Course.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_course_metrics(
        self,
        course_ids: Sequence[uuid.UUID],
    ) -> Tuple[Dict[uuid.UUID, int], Dict[uuid.UUID, int]]:
        """Batch count active students and learning objectives per course."""
        if not course_ids:
            return {}, {}

        student_stmt = (
            select(CourseEnrollment.course_id, func.count(CourseEnrollment.id))
            .where(
                CourseEnrollment.course_id.in_(course_ids),
                CourseEnrollment.contextual_role == ContextualRole.STUDENT.value,
                CourseEnrollment.enrollment_status == EnrollmentStatus.ACTIVE.value,
            )
            .group_by(CourseEnrollment.course_id)
        )
        lo_stmt = (
            select(LearningObjective.course_id, func.count(LearningObjective.id))
            .where(LearningObjective.course_id.in_(course_ids))
            .group_by(LearningObjective.course_id)
        )
        student_res = await self.db.execute(student_stmt)
        lo_res = await self.db.execute(lo_stmt)

        return (
            {row[0]: int(row[1]) for row in student_res.all()},
            {row[0]: int(row[1]) for row in lo_res.all()},
        )

    # ------------------------------------------------------------------
    # Learning Objectives
    # ------------------------------------------------------------------
    async def list_los(self, course_id: uuid.UUID) -> List[LearningObjective]:
        stmt = (
            select(LearningObjective)
            .where(LearningObjective.course_id == course_id)
            .order_by(LearningObjective.order_index.asc(), LearningObjective.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_lo_by_id(
        self,
        course_id: uuid.UUID,
        lo_id: uuid.UUID,
    ) -> Optional[LearningObjective]:
        stmt = select(LearningObjective).where(
            LearningObjective.course_id == course_id,
            LearningObjective.id == lo_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_lo(self, lo: LearningObjective) -> LearningObjective:
        self.db.add(lo)
        await self.db.flush()
        return lo

    async def delete_lo(self, lo: LearningObjective) -> None:
        await self.db.delete(lo)
        await self.db.flush()

    async def count_los(self, course_id: uuid.UUID) -> int:
        stmt = select(func.count(LearningObjective.id)).where(
            LearningObjective.course_id == course_id
        )
        result = await self.db.execute(stmt)
        return int(result.scalar() or 0)

    # ------------------------------------------------------------------
    # Enrollments & Roster
    # ------------------------------------------------------------------
    async def get_enrollment(
        self,
        course_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[CourseEnrollment]:
        stmt = select(CourseEnrollment).where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def is_user_instructor_anywhere(self, user_id: uuid.UUID) -> bool:
        """Check whether user holds an active INSTRUCTOR role in at least one course (Q3)."""
        stmt = select(func.count(CourseEnrollment.id)).where(
            CourseEnrollment.user_id == user_id,
            CourseEnrollment.contextual_role == ContextualRole.INSTRUCTOR.value,
            CourseEnrollment.enrollment_status == EnrollmentStatus.ACTIVE.value,
        )
        result = await self.db.execute(stmt)
        return (result.scalar() or 0) > 0

    async def list_user_active_roles(
        self,
        user_id: uuid.UUID,
    ) -> List[Tuple[uuid.UUID, str, str, str]]:
        """Return (course_id, contextual_role, course_code, course_name) for active enrollments."""
        stmt = (
            select(
                CourseEnrollment.course_id,
                CourseEnrollment.contextual_role,
                Course.course_code,
                Course.name,
            )
            .join(Course, Course.id == CourseEnrollment.course_id)
            .where(
                CourseEnrollment.user_id == user_id,
                CourseEnrollment.enrollment_status == EnrollmentStatus.ACTIVE.value,
            )
        )
        result = await self.db.execute(stmt)
        return [(row[0], row[1], row[2], row[3]) for row in result.all()]

    async def create_enrollment(self, enrollment: CourseEnrollment) -> CourseEnrollment:
        self.db.add(enrollment)
        await self.db.flush()
        return enrollment

    async def bulk_insert_student_enrollments(
        self,
        course_id: uuid.UUID,
        user_ids: Sequence[uuid.UUID],
    ) -> int:
        """
        Insert active student enrollments using PostgreSQL ON CONFLICT DO NOTHING (BR-ROSTER-01).
        Returns the number of newly inserted rows.
        """
        if not user_ids:
            return 0

        now = datetime.now(timezone.utc)
        rows = [
            {
                "id": uuid.uuid4(),
                "course_id": course_id,
                "user_id": uid,
                "contextual_role": ContextualRole.STUDENT.value,
                "enrollment_status": EnrollmentStatus.ACTIVE.value,
                "enrolled_at": now,
            }
            for uid in user_ids
        ]
        stmt = (
            pg_insert(CourseEnrollment)
            .values(rows)
            .on_conflict_do_nothing(constraint="uq_course_user_enrollment")
            .returning(CourseEnrollment.id)
        )
        result = await self.db.execute(stmt)
        inserted = len(result.all())
        await self.db.flush()
        return inserted

    async def list_active_students_with_users(
        self,
        course_id: uuid.UUID,
        search_query: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Tuple[CourseEnrollment, User]], int]:
        """List active student enrollments joined with identity.users."""
        stmt = (
            select(CourseEnrollment, User)
            .join(User, User.id == CourseEnrollment.user_id)
            .where(
                CourseEnrollment.course_id == course_id,
                CourseEnrollment.contextual_role == ContextualRole.STUDENT.value,
                CourseEnrollment.enrollment_status == EnrollmentStatus.ACTIVE.value,
            )
        )
        if search_query:
            q = f"%{search_query.strip()}%"
            stmt = stmt.where(
                or_(
                    User.full_name.ilike(q),
                    User.user_code.ilike(q),
                    User.email.ilike(q),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await self.db.execute(count_stmt)).scalar() or 0)

        offset = (page - 1) * page_size
        stmt = stmt.order_by(User.user_code.asc(), User.full_name.asc()).offset(offset).limit(page_size)
        rows = (await self.db.execute(stmt)).all()
        return [(row[0], row[1]) for row in rows], total

    async def list_all_active_students(self, course_id: uuid.UUID) -> List[User]:
        """Fetch all active student User objects enrolled in a course."""
        stmt = (
            select(User)
            .join(CourseEnrollment, CourseEnrollment.user_id == User.id)
            .where(
                CourseEnrollment.course_id == course_id,
                CourseEnrollment.contextual_role == ContextualRole.STUDENT.value,
                CourseEnrollment.enrollment_status == EnrollmentStatus.ACTIVE.value,
            )
            .order_by(User.user_code.asc(), User.full_name.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_users_by_emails(self, emails: Iterable[str]) -> List[User]:
        norm = [e.strip().lower() for e in emails if e and e.strip()]
        if not norm:
            return []
        stmt = select(User).where(func.lower(User.email).in_(norm))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_enrollment_status(
        self,
        course_id: uuid.UUID,
        user_id: uuid.UUID,
        new_status: EnrollmentStatus,
    ) -> None:
        stmt = (
            update(CourseEnrollment)
            .where(
                CourseEnrollment.course_id == course_id,
                CourseEnrollment.user_id == user_id,
            )
            .values(enrollment_status=new_status.value)
        )
        await self.db.execute(stmt)
        await self.db.flush()

    # ------------------------------------------------------------------
    # Groups & Group Members
    # ------------------------------------------------------------------
    async def list_groups_with_members(
        self,
        course_id: uuid.UUID,
    ) -> List[Tuple[CourseGroup, List[User]]]:
        group_stmt = (
            select(CourseGroup)
            .where(CourseGroup.course_id == course_id)
            .order_by(CourseGroup.group_set_name.asc(), CourseGroup.name.asc())
        )
        groups = list((await self.db.execute(group_stmt)).scalars().all())
        if not groups:
            return []

        group_ids = [g.id for g in groups]
        member_stmt = (
            select(CourseGroupMember.group_id, User)
            .join(User, User.id == CourseGroupMember.user_id)
            .where(CourseGroupMember.group_id.in_(group_ids))
            .order_by(User.user_code.asc(), User.full_name.asc())
        )
        members_by_group: Dict[uuid.UUID, List[User]] = {gid: [] for gid in group_ids}
        for gid, user in (await self.db.execute(member_stmt)).all():
            members_by_group[gid].append(user)

        return [(g, members_by_group[g.id]) for g in groups]

    async def get_student_group_names(
        self,
        course_id: uuid.UUID,
        user_ids: Sequence[uuid.UUID],
    ) -> Dict[uuid.UUID, str]:
        """Return first group name per student in a course for roster table display."""
        if not user_ids:
            return {}
        stmt = (
            select(CourseGroupMember.user_id, CourseGroup.name)
            .join(CourseGroup, CourseGroup.id == CourseGroupMember.group_id)
            .where(
                CourseGroup.course_id == course_id,
                CourseGroupMember.user_id.in_(user_ids),
            )
            .order_by(CourseGroup.created_at.asc())
        )
        mapping: Dict[uuid.UUID, str] = {}
        for uid, gname in (await self.db.execute(stmt)).all():
            mapping.setdefault(uid, gname)
        return mapping

    async def get_group_by_id(
        self,
        course_id: uuid.UUID,
        group_id: uuid.UUID,
    ) -> Optional[CourseGroup]:
        stmt = select(CourseGroup).where(
            CourseGroup.course_id == course_id,
            CourseGroup.id == group_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def user_in_group_set(
        self,
        course_id: uuid.UUID,
        group_set_name: str,
        user_id: uuid.UUID,
    ) -> bool:
        stmt = (
            select(func.count(CourseGroupMember.id))
            .join(CourseGroup, CourseGroup.id == CourseGroupMember.group_id)
            .where(
                CourseGroup.course_id == course_id,
                CourseGroup.group_set_name == group_set_name,
                CourseGroupMember.user_id == user_id,
            )
        )
        return int((await self.db.execute(stmt)).scalar() or 0) > 0

    async def replace_group_set(
        self,
        course_id: uuid.UUID,
        group_set_name: str,
        groups: Sequence[Tuple[str, Sequence[uuid.UUID]]],
    ) -> None:
        """Atomically replace all groups and members belonging to `group_set_name`."""
        await self.db.execute(
            delete(CourseGroup).where(
                CourseGroup.course_id == course_id,
                CourseGroup.group_set_name == group_set_name,
            )
        )
        await self.db.flush()

        for group_name, member_ids in groups:
            grp = CourseGroup(
                course_id=course_id,
                group_set_name=group_set_name,
                name=group_name.strip(),
            )
            self.db.add(grp)
            await self.db.flush()
            for uid in member_ids:
                self.db.add(CourseGroupMember(group_id=grp.id, user_id=uid))
        await self.db.flush()

    async def add_group_member(self, group_id: uuid.UUID, user_id: uuid.UUID) -> None:
        self.db.add(CourseGroupMember(group_id=group_id, user_id=user_id))
        await self.db.flush()

    async def enqueue_outbox_event(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: uuid.UUID,
        payload: Dict[str, object],
    ) -> OutboxEvent:
        event = OutboxEvent(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            status="PENDING",
        )
        self.db.add(event)
        await self.db.flush()
        return event
