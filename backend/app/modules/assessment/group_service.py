# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Group formation, topic selection, and orphan student assignment service (TV3)."""

from datetime import datetime, timezone
from typing import List, Optional
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.modules.assessment.exceptions import (
    AssessmentAccessDeniedException,
    AssessmentNotFoundException,
    GroupFormationDeadlinePassedException,
    GroupTopicFullException,
    ProjectTopicNotFoundException,
    StudentGroupNotFoundException,
)
from app.modules.assessment.models import (
    Assignment,
    GroupMember,
    ProjectTopic,
    StudentGroup,
)
from app.modules.course.models import CourseEnrollment
from app.modules.system.models import User


class GroupService:
    """Service handling collaborative groups, topics, and auto-assignment."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_topic(
        self,
        assignment_id: uuid.UUID,
        user: User,
        topic_code: str,
        title: str,
        description: Optional[str] = None,
        max_groups: int = 1,
    ) -> ProjectTopic:
        """Instructor registers a project topic."""
        assignment = await self._get_assignment(assignment_id)
        topic = ProjectTopic(
            assignment_id=assignment.id,
            topic_code=topic_code,
            title=title,
            description=description,
            max_groups=max_groups,
            current_groups_count=0,
            is_active=True,
        )
        self.db.add(topic)
        await self.db.commit()
        await self.db.refresh(topic)
        return topic

    async def list_topics(self, assignment_id: uuid.UUID) -> List[ProjectTopic]:
        """List all active project topics for an assignment."""
        await self._get_assignment(assignment_id)
        stmt = (
            select(ProjectTopic)
            .where(ProjectTopic.assignment_id == assignment_id, ProjectTopic.is_active.is_(True))
            .order_by(ProjectTopic.topic_code.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_group(
        self,
        assignment_id: uuid.UUID,
        leader: User,
        group_name: str,
        member_ids: Optional[List[uuid.UUID]] = None,
        topic_id: Optional[uuid.UUID] = None,
    ) -> StudentGroup:
        """Create a student group with leader and initial members."""
        assignment = await self._get_assignment(assignment_id)
        now = datetime.now(timezone.utc)

        if assignment.group_formation_deadline and now > assignment.group_formation_deadline:
            raise GroupFormationDeadlinePassedException()

        members_to_add = [leader.id]
        if member_ids:
            for mid in member_ids:
                if mid not in members_to_add:
                    members_to_add.append(mid)

        group = StudentGroup(
            assignment_id=assignment.id,
            group_name=group_name,
            topic_id=None,
            leader_student_id=leader.id,
            is_finalized=False,
        )
        self.db.add(group)
        await self.db.flush()

        for mid in members_to_add:
            role = "LEADER" if mid == leader.id else "MEMBER"
            member = GroupMember(
                group_id=group.id,
                student_id=mid,
                role=role,
            )
            self.db.add(member)

        if topic_id:
            await self._reserve_topic(group, topic_id)

        await self.db.commit()
        return await self.get_group(group.id)

    async def select_topic(
        self,
        group_id: uuid.UUID,
        user: User,
        topic_id: uuid.UUID,
    ) -> StudentGroup:
        """Pessimistic lock topic selection (SELECT ... FOR UPDATE)."""
        group = await self.get_group(group_id)
        assignment = await self._get_assignment(group.assignment_id)
        now = datetime.now(timezone.utc)

        if assignment.group_formation_deadline and now > assignment.group_formation_deadline:
            raise GroupFormationDeadlinePassedException()

        if group.leader_student_id != user.id:
            raise AssessmentAccessDeniedException("Only the group leader may select a project topic.")

        await self._reserve_topic(group, topic_id)
        await self.db.commit()
        return await self.get_group(group.id)

    async def _reserve_topic(self, group: StudentGroup, topic_id: uuid.UUID) -> None:
        """Reserve topic with pessimistic lock to avoid race conditions."""
        stmt = (
            select(ProjectTopic)
            .where(ProjectTopic.id == topic_id, ProjectTopic.assignment_id == group.assignment_id)
            .with_for_update()
        )
        res = await self.db.execute(stmt)
        topic = res.scalar_one_or_none()
        if not topic:
            raise ProjectTopicNotFoundException(str(topic_id))

        if topic.current_groups_count >= topic.max_groups:
            raise GroupTopicFullException(topic.topic_code)

        if group.topic_id and group.topic_id != topic_id:
            prev_stmt = (
                select(ProjectTopic)
                .where(ProjectTopic.id == group.topic_id)
                .with_for_update()
            )
            prev_res = await self.db.execute(prev_stmt)
            prev_topic = prev_res.scalar_one_or_none()
            if prev_topic and prev_topic.current_groups_count > 0:
                prev_topic.current_groups_count -= 1

        topic.current_groups_count += 1
        group.topic_id = topic.id

    async def get_group(self, group_id: uuid.UUID) -> StudentGroup:
        """Fetch group with topic and members eagerly loaded."""
        stmt = (
            select(StudentGroup)
            .options(
                selectinload(StudentGroup.members).selectinload(GroupMember.student),
                selectinload(StudentGroup.topic),
            )
            .where(StudentGroup.id == group_id)
        )
        res = await self.db.execute(stmt)
        group = res.scalar_one_or_none()
        if not group:
            raise StudentGroupNotFoundException(str(group_id))
        return group

    async def list_groups(self, assignment_id: uuid.UUID) -> List[StudentGroup]:
        """List all groups for an assignment."""
        await self._get_assignment(assignment_id)
        stmt = (
            select(StudentGroup)
            .options(
                selectinload(StudentGroup.members).selectinload(GroupMember.student),
                selectinload(StudentGroup.topic),
            )
            .where(StudentGroup.assignment_id == assignment_id)
            .order_by(StudentGroup.created_at.asc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def auto_assign_orphan_students(
        self,
        assignment_id: uuid.UUID,
        instructor: User,
    ) -> List[StudentGroup]:
        """Auto-group remaining students and assign available topics after deadline."""
        assignment = await self._get_assignment(assignment_id)

        enrollments_stmt = (
            select(CourseEnrollment.user_id)
            .where(
                CourseEnrollment.course_id == assignment.course_id,
                CourseEnrollment.role == "STUDENT",
                CourseEnrollment.status == "ACTIVE",
            )
        )
        all_enrolled_res = await self.db.execute(enrollments_stmt)
        all_student_ids = set(all_enrolled_res.scalars().all())

        grouped_stmt = (
            select(GroupMember.student_id)
            .join(StudentGroup, StudentGroup.id == GroupMember.group_id)
            .where(StudentGroup.assignment_id == assignment_id)
        )
        grouped_res = await self.db.execute(grouped_stmt)
        grouped_student_ids = set(grouped_res.scalars().all())

        orphan_ids = list(all_student_ids - grouped_student_ids)
        if not orphan_ids:
            return []

        target_size = assignment.group_max_size if assignment.group_max_size > 1 else 3
        chunks = [orphan_ids[i:i + target_size] for i in range(0, len(orphan_ids), target_size)]

        topics_stmt = (
            select(ProjectTopic)
            .where(
                ProjectTopic.assignment_id == assignment_id,
                ProjectTopic.is_active.is_(True),
                ProjectTopic.current_groups_count < ProjectTopic.max_groups,
            )
            .order_by(ProjectTopic.topic_code.asc())
            .with_for_update()
        )
        topics_res = await self.db.execute(topics_stmt)
        available_topics = list(topics_res.scalars().all())

        new_groups: List[StudentGroup] = []
        topic_idx = 0

        existing_count_stmt = select(func.count(StudentGroup.id)).where(StudentGroup.assignment_id == assignment_id)
        cnt_res = await self.db.execute(existing_count_stmt)
        base_count = cnt_res.scalar() or 0

        for idx, chunk in enumerate(chunks, start=1):
            leader_id = chunk[0]
            group_name = f"Auto-Group {base_count + idx}"
            assigned_topic = None
            if topic_idx < len(available_topics):
                candidate_topic = available_topics[topic_idx]
                if candidate_topic.current_groups_count < candidate_topic.max_groups:
                    candidate_topic.current_groups_count += 1
                    assigned_topic = candidate_topic.id
                    if candidate_topic.current_groups_count >= candidate_topic.max_groups:
                        topic_idx += 1

            new_group = StudentGroup(
                assignment_id=assignment.id,
                group_name=group_name,
                topic_id=assigned_topic,
                leader_student_id=leader_id,
                is_finalized=True,
            )
            self.db.add(new_group)
            await self.db.flush()

            for student_id in chunk:
                role = "LEADER" if student_id == leader_id else "MEMBER"
                gm = GroupMember(
                    group_id=new_group.id,
                    student_id=student_id,
                    role=role,
                )
                self.db.add(gm)

            new_groups.append(new_group)

        await self.db.commit()
        return [await self.get_group(g.id) for g in new_groups]

    async def _get_assignment(self, assignment_id: uuid.UUID) -> Assignment:
        stmt = select(Assignment).where(Assignment.id == assignment_id)
        res = await self.db.execute(stmt)
        assignment = res.scalar_one_or_none()
        if not assignment:
            raise AssessmentNotFoundException(str(assignment_id))
        return assignment
