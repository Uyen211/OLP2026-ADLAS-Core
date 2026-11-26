# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""SQLAlchemy ORM models mapped directly to gradebook.* tables."""

from datetime import datetime, timezone
from decimal import Decimal
import uuid
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
import app.modules.assessment.models  # noqa: F401 - ensure assessment.* tables are registered
import app.modules.course.models  # noqa: F401 - ensure course.courses is registered
import app.modules.system.models  # noqa: F401 - ensure identity.users is registered


class GradebookGroup(Base):
    """Weighted grade category in gradebook.gradebook_groups (T2-P-M5-01)."""

    __tablename__ = "gradebook_groups"
    __table_args__ = (
        CheckConstraint("weight_percent >= 1 AND weight_percent <= 100", name="chk_gradebook_group_weight"),
        {"schema": "gradebook"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("course.courses.id", ondelete="CASCADE"), nullable=False)
    group_name = Column(String(100), nullable=False)
    weight_percent = Column(Integer, nullable=False)
    drop_lowest_count = Column(Integer, nullable=False, default=0)
    is_hurdle = Column(Boolean, nullable=False, default=False)
    hurdle_min_score = Column(Numeric(4, 2), nullable=True, default=Decimal("4.00"))

    columns = relationship("GradebookColumn", back_populates="group", cascade="all, delete-orphan")


class GradebookColumn(Base):
    """Individual grade column belonging to a grade group in gradebook.gradebook_columns."""

    __tablename__ = "gradebook_columns"
    __table_args__ = {"schema": "gradebook"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("course.courses.id", ondelete="CASCADE"), nullable=False)
    group_id = Column(UUID(as_uuid=True), ForeignKey("gradebook.gradebook_groups.id", ondelete="RESTRICT"), nullable=False)
    item_type = Column(String(30), nullable=False)  # ASSIGNMENT, QUIZ, PROGRESS_ATTENDANCE, MANUAL
    item_id = Column(UUID(as_uuid=True), nullable=True)
    title = Column(String(150), nullable=False)
    max_points = Column(Numeric(4, 2), nullable=False, default=Decimal("10.00"))
    is_muted = Column(Boolean, nullable=False, default=True)

    group = relationship("GradebookGroup", back_populates="columns")
    grades = relationship("GradeEntry", back_populates="column", cascade="all, delete-orphan")


class GradeEntry(Base):
    """Student score, AI Rubric proposal, and instructor review in gradebook.grades."""

    __tablename__ = "grades"
    __table_args__ = (
        CheckConstraint("official_score >= 0.0 AND official_score <= 10.0", name="chk_grade_official_range"),
        UniqueConstraint("column_id", "user_id", name="uq_column_user_grade"),
        {"schema": "gradebook"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    column_id = Column(UUID(as_uuid=True), ForeignKey("gradebook.gradebook_columns.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="RESTRICT"), nullable=False)
    submission_id = Column(
        UUID(as_uuid=True),
        ForeignKey("assessment.assignment_submissions.id", ondelete="SET NULL"),
        nullable=True,
    )
    proposed_ai_score = Column(Numeric(4, 2), nullable=True)
    proposed_ai_citations = Column(JSONB, nullable=True)
    evidence_flag = Column(String(30), nullable=True)
    ai_proposed_details = Column(JSONB, nullable=True)
    official_score = Column(Numeric(4, 2), nullable=True)
    rubric_scores = Column(JSONB, nullable=True)
    instructor_feedback = Column(Text, nullable=True)
    voice_feedback_url = Column(String(500), nullable=True)
    annotations = Column(JSONB, nullable=True)
    is_overridden = Column(Boolean, nullable=False, default=False)
    grading_status = Column(String(30), nullable=False, default="UNGRADED")
    graded_by = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="SET NULL"), nullable=True)
    graded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    column = relationship("GradebookColumn", back_populates="grades")


class CourseGradebookLock(Base):
    """Poka-yoke final lock record per course in gradebook.course_gradebook_locks (T2-P-M5-05)."""

    __tablename__ = "course_gradebook_locks"
    __table_args__ = {"schema": "gradebook"}

    course_id = Column(UUID(as_uuid=True), ForeignKey("course.courses.id", ondelete="CASCADE"), primary_key=True)
    is_locked = Column(Boolean, nullable=False, default=True)
    locked_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    locked_by = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="SET NULL"), nullable=True)
    unlock_decision_code = Column(String(100), nullable=True)
    unlock_reason = Column(Text, nullable=True)
    unlocked_at = Column(DateTime(timezone=True), nullable=True)
    unlocked_by = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="SET NULL"), nullable=True)


class GradeAuditLog(Base):
    """Immutable academic audit trail in gradebook.audit_logs (BR-12)."""

    __tablename__ = "audit_logs"
    __table_args__ = {"schema": "gradebook"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="SET NULL"), nullable=True)
    action_type = Column(String(50), nullable=False)
    entity_name = Column(String(100), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
