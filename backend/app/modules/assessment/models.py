# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""SQLAlchemy ORM models mapped directly to assessment.* tables."""

from datetime import datetime, timezone
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
import app.modules.system.models  # noqa: F401 - ensure identity.users is in metadata
import app.modules.course.models  # noqa: F401 - ensure course.courses is in metadata


class Assignment(Base):
    """Assignment or Project task in assessment.assignments."""

    __tablename__ = "assignments"
    __table_args__ = {"schema": "assessment"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("course.courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    instructions = Column(Text, nullable=False)
    attachment_url = Column(String(500), nullable=True)
    submission_type = Column(String(50), nullable=False, default="FILE_UPLOAD")  # FILE_UPLOAD, GIT_REPOSITORY, HYBRID
    allowed_extensions = Column(String(100), nullable=False, default=".zip,.pdf,.docx")
    max_file_size_mb = Column(Integer, nullable=False, default=50)
    is_group_assignment = Column(Boolean, nullable=False, default=False)
    is_transfer_task = Column(Boolean, nullable=False, default=False)
    assignment_type = Column(String(20), nullable=False, default="standard")  # standard, milestone, group_project
    group_min_size = Column(Integer, nullable=False, default=1)
    group_max_size = Column(Integer, nullable=False, default=1)
    group_formation_deadline = Column(DateTime(timezone=True), nullable=True)
    grade_group_id = Column(UUID(as_uuid=True), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=False)
    until_date = Column(DateTime(timezone=True), nullable=True)
    late_penalty_percent = Column(Numeric(4, 2), nullable=False, default=5.0)
    is_viva_required = Column(Boolean, nullable=False, default=True)
    viva_question_count = Column(Integer, nullable=False, default=3)
    ai_policy_level = Column(String(20), nullable=False, default="YELLOW")
    is_published = Column(Boolean, nullable=False, default=False)
    available_from = Column(DateTime(timezone=True), nullable=True)
    max_points = Column(Numeric(4, 1), nullable=False, default=10.0)
    max_attempts = Column(Integer, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    submissions = relationship("AssignmentSubmission", back_populates="assignment", cascade="all, delete-orphan")
    rubric = relationship("Rubric", back_populates="assignment", uselist=False, cascade="all, delete-orphan")
    milestones = relationship("AssignmentMilestone", back_populates="assignment", cascade="all, delete-orphan", order_by="AssignmentMilestone.order_index")
    topics = relationship("ProjectTopic", back_populates="assignment", cascade="all, delete-orphan")
    groups = relationship("StudentGroup", back_populates="assignment", cascade="all, delete-orphan")
    course = relationship("Course")


class Rubric(Base):
    """Rubric scoring table in assessment.rubrics."""

    __tablename__ = "rubrics"
    __table_args__ = {"schema": "assessment"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("assessment.assignments.id", ondelete="CASCADE"), nullable=False, unique=True)
    title = Column(String(200), nullable=False)
    total_points = Column(Numeric(4, 1), nullable=False, default=10.0)
    is_frozen = Column(Boolean, nullable=False, default=False)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    assignment = relationship("Assignment", back_populates="rubric")
    criteria = relationship("RubricCriteria", back_populates="rubric", cascade="all, delete-orphan", order_by="RubricCriteria.order_index")


class RubricCriteria(Base):
    """Multi-dimensional scoring criteria in assessment.rubric_criteria."""

    __tablename__ = "rubric_criteria"
    __table_args__ = {"schema": "assessment"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rubric_id = Column(UUID(as_uuid=True), ForeignKey("assessment.rubrics.id", ondelete="CASCADE"), nullable=False)
    lo_id = Column(UUID(as_uuid=True), ForeignKey("course.learning_objectives.id", ondelete="SET NULL"), nullable=True)
    competency_code = Column(String(20), nullable=True)  # C1-C7
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    max_points = Column(Numeric(4, 1), nullable=False)
    rating_levels = Column(JSONB, nullable=False)
    order_index = Column(Integer, nullable=False, default=1)

    rubric = relationship("Rubric", back_populates="criteria")


class AssignmentSubmission(Base):
    """Student submission entity in assessment.assignment_submissions."""

    __tablename__ = "assignment_submissions"
    __table_args__ = (
        CheckConstraint("self_contribution_pct >= 0 AND self_contribution_pct <= 100", name="chk_self_contribution"),
        UniqueConstraint("assignment_id", "user_id", "version", name="uq_assignment_user_version"),
        {"schema": "assessment"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("assessment.assignments.id", ondelete="RESTRICT"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="RESTRICT"), nullable=False)
    milestone_id = Column(UUID(as_uuid=True), ForeignKey("assessment.assignment_milestones.id", ondelete="SET NULL"), nullable=True)
    group_id = Column(UUID(as_uuid=True), ForeignKey("assessment.student_groups.id", ondelete="SET NULL"), nullable=True)
    github_commit_sha = Column(String(40), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    project_title = Column(String(255), nullable=True)
    file_url = Column(String(500), nullable=True)
    git_repo_url = Column(String(500), nullable=True)
    comments = Column(Text, nullable=True)
    ai_disclosure_data = Column(JSONB, nullable=False, default=dict)
    self_contribution_pct = Column(Integer, nullable=False)
    is_pledge_signed = Column(Boolean, nullable=False, default=True)
    submitted_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    is_late = Column(Boolean, nullable=False, default=False)
    late_penalty_applied = Column(Numeric(4, 2), nullable=False, default=0.0)
    status = Column(String(30), nullable=False, default="PENDING_VIVA")  # PENDING_VIVA, IN_VIVA, VIVA_COMPLETED, GRADED

    assignment = relationship("Assignment", back_populates="submissions")
    user = relationship("User")
    milestone = relationship("AssignmentMilestone", back_populates="submissions")
    group = relationship("StudentGroup")
    viva_transcript = relationship("VivaTranscript", back_populates="submission", uselist=False, cascade="all, delete-orphan")


class VivaTranscript(Base):
    """Viva defense session and integrity audit trail in assessment.viva_transcripts."""

    __tablename__ = "viva_transcripts"
    __table_args__ = {"schema": "assessment"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("assessment.assignment_submissions.id", ondelete="CASCADE"), nullable=False, unique=True)
    questions_answers = Column(JSONB, nullable=False)
    violation_logs = Column(JSONB, nullable=False, default=list)
    started_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(30), nullable=False, default="COMPLETED")  # READY, IN_PROGRESS, COMPLETED, TIMEOUT

    submission = relationship("AssignmentSubmission", back_populates="viva_transcript")


class IntegrityPledge(Base):
    """Append-only electronic academic integrity pledge in assessment.integrity_pledges."""

    __tablename__ = "integrity_pledges"
    __table_args__ = (
        CheckConstraint("self_contribution_pct >= 0 AND self_contribution_pct <= 100", name="integrity_pledges_self_contribution_pct_check"),
        {"schema": "assessment"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("assessment.assignments.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False)
    pledge_version = Column(String(30), nullable=False, default="v1.0")
    ai_policy_level = Column(String(20), nullable=False)
    self_contribution_pct = Column(Integer, nullable=False)
    ai_disclosure_snapshot = Column(JSONB, nullable=False, default=dict)
    client_ip = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    signed_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class AssignmentMilestone(Base):
    """Phased milestone tracking in assessment.assignment_milestones."""

    __tablename__ = "assignment_milestones"
    __table_args__ = {"schema": "assessment"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("assessment.assignments.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    weight_percent = Column(Numeric(5, 2), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    until_date = Column(DateTime(timezone=True), nullable=True)
    order_index = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    assignment = relationship("Assignment", back_populates="milestones")
    submissions = relationship("AssignmentSubmission", back_populates="milestone")
    peer_reviews = relationship("PeerReview", back_populates="milestone")


class ProjectTopic(Base):
    """Project topic list with capped registration in assessment.project_topics."""

    __tablename__ = "project_topics"
    __table_args__ = {"schema": "assessment"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("assessment.assignments.id", ondelete="CASCADE"), nullable=False)
    topic_code = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    max_groups = Column(Integer, nullable=False, default=1)
    current_groups_count = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    assignment = relationship("Assignment", back_populates="topics")
    groups = relationship("StudentGroup", back_populates="topic")


class StudentGroup(Base):
    """Student group for collaborative project in assessment.student_groups."""

    __tablename__ = "student_groups"
    __table_args__ = {"schema": "assessment"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("assessment.assignments.id", ondelete="CASCADE"), nullable=False)
    group_name = Column(String(100), nullable=False)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("assessment.project_topics.id", ondelete="SET NULL"), nullable=True)
    leader_student_id = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="RESTRICT"), nullable=False)
    is_finalized = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    assignment = relationship("Assignment", back_populates="groups")
    topic = relationship("ProjectTopic", back_populates="groups")
    leader = relationship("User", foreign_keys=[leader_student_id])
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")


class GroupMember(Base):
    """Group membership entity in assessment.group_members."""

    __tablename__ = "group_members"
    __table_args__ = (
        UniqueConstraint("group_id", "student_id", name="uq_group_student"),
        {"schema": "assessment"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("assessment.student_groups.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False)
    joined_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    role = Column(String(20), nullable=False, default="MEMBER")  # LEADER, MEMBER

    group = relationship("StudentGroup", back_populates="members")
    student = relationship("User", foreign_keys=[student_id])


class PeerReview(Base):
    """Blind peer evaluation entry in assessment.peer_reviews."""

    __tablename__ = "peer_reviews"
    __table_args__ = (
        UniqueConstraint("assignment_id", "milestone_id", "reviewer_id", "reviewee_id", name="uq_peer_review_entry"),
        {"schema": "assessment"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("assessment.assignments.id", ondelete="CASCADE"), nullable=False)
    milestone_id = Column(UUID(as_uuid=True), ForeignKey("assessment.assignment_milestones.id", ondelete="SET NULL"), nullable=True)
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False)
    reviewee_id = Column(UUID(as_uuid=True), ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False)
    criteria_scores_json = Column(JSONB, nullable=False, default=dict)
    total_score = Column(Numeric(5, 2), nullable=False)
    comment = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    assignment = relationship("Assignment")
    milestone = relationship("AssignmentMilestone", back_populates="peer_reviews")
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    reviewee = relationship("User", foreign_keys=[reviewee_id])
