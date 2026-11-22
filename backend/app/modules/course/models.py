# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""SQLAlchemy 2.0 ORM models mapped strictly to pre-existing course.* tables."""

from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
import app.modules.system.models  # noqa: F401 - register identity.users in Base.metadata


class Course(Base):
    """Course section or reusable course template in course.courses."""

    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint("credits >= 1 AND credits <= 6", name="chk_course_credits"),
        UniqueConstraint("course_code", "section_code", "semester", name="uq_course_section_semester"),
        {"schema": "course"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_code = Column(String(30), nullable=False)
    section_code = Column(String(30), nullable=False)
    name = Column(String(200), nullable=False)
    semester = Column(String(50), nullable=False)
    credits = Column(Integer, nullable=False)
    grading_scheme = Column(String(30), nullable=False, default="SCALE_10")
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    syllabus_text = Column(Text, nullable=True)
    join_code = Column(String(10), unique=True, nullable=True)
    is_enrollment_open = Column(Boolean, nullable=False, default=True)
    is_template = Column(Boolean, nullable=False, default=False)
    status = Column(String(30), nullable=False, default="UNPUBLISHED")
    created_by = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class LearningObjective(Base):
    """Course Learning Objective (LO/CLO) catalog entry in course.learning_objectives."""

    __tablename__ = "learning_objectives"
    __table_args__ = (
        UniqueConstraint("course_id", "code", name="uq_course_lo_code"),
        {"schema": "course"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("course.courses.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(30), nullable=False)
    description = Column(Text, nullable=False)
    bloom_level = Column(String(30), nullable=False, default="UNDERSTAND")
    order_index = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class CourseEnrollment(Base):
    """Per-course membership and contextual role (BR-01) in course.course_enrollments."""

    __tablename__ = "course_enrollments"
    __table_args__ = (
        UniqueConstraint("course_id", "user_id", name="uq_course_user_enrollment"),
        {"schema": "course"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("course.courses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False)
    contextual_role = Column(String(30), nullable=False)
    enrollment_status = Column(String(30), nullable=False, default="ACTIVE")
    enrolled_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class CourseGroup(Base):
    """Project group belonging to a group set in course.course_groups."""

    __tablename__ = "course_groups"
    __table_args__ = ({"schema": "course"},)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("course.courses.id", ondelete="CASCADE"), nullable=False)
    group_set_name = Column(String(100), nullable=False)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class CourseGroupMember(Base):
    """Student membership within a course project group in course.course_group_members."""

    __tablename__ = "course_group_members"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_group_member"),
        {"schema": "course"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("course.course_groups.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False)
    joined_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
