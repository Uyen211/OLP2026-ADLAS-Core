# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""SQLAlchemy 2.0 ORM models mapped strictly to examination.* tables."""

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
from app.core.database import Base
import app.modules.course.models  # noqa: F401 - register course.* tables in Base.metadata
import app.modules.system.models  # noqa: F401 - register identity.users in Base.metadata


class QuestionFolder(Base):
    """Hierarchical folder organization in examination.question_folders."""

    __tablename__ = "question_folders"
    __table_args__ = ({"schema": "examination"},)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(
        UUID(as_uuid=True),
        ForeignKey("course.courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    folder_name = Column(String(100), nullable=False)
    parent_folder_id = Column(
        UUID(as_uuid=True),
        ForeignKey("examination.question_folders.id", ondelete="CASCADE"),
        nullable=True,
    )
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class QuestionBank(Base):
    """Categorized question bank container in examination.question_banks."""

    __tablename__ = "question_banks"
    __table_args__ = ({"schema": "examination"},)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(
        UUID(as_uuid=True),
        ForeignKey("course.courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_name = Column(String(150), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class Question(Base):
    """Question item in examination.questions supporting KaTeX/Code and Soft Delete."""

    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint("default_points > 0", name="chk_exam_question_points_positive"),
        {"schema": "examination"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_id = Column(
        UUID(as_uuid=True),
        ForeignKey("examination.question_banks.id", ondelete="CASCADE"),
        nullable=False,
    )
    folder_id = Column(
        UUID(as_uuid=True),
        ForeignKey("examination.question_folders.id", ondelete="SET NULL"),
        nullable=True,
    )
    lo_id = Column(
        UUID(as_uuid=True),
        ForeignKey("course.learning_objectives.id", ondelete="SET NULL"),
        nullable=True,
    )
    bloom_level = Column(String(30), nullable=False, default="UNDERSTAND")
    difficulty = Column(String(20), nullable=False, default="medium")  # easy, medium, hard
    source_ref = Column(String(100), nullable=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(30), nullable=False, default="MULTIPLE_CHOICE")
    default_points = Column(Numeric(4, 2), nullable=False, default=Decimal("1.00"))
    options = Column(JSONB, nullable=False)
    explanation = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class Quiz(Base):
    """Quiz and proctoring room configuration in examination.quizzes."""

    __tablename__ = "quizzes"
    __table_args__ = (
        CheckConstraint("available_until > available_from", name="chk_quiz_availability"),
        CheckConstraint("time_limit_mins > 0", name="chk_exam_quiz_time_limit_positive"),
        CheckConstraint("max_attempts >= 1", name="chk_exam_quiz_max_attempts_positive"),
        {"schema": "examination"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(
        UUID(as_uuid=True),
        ForeignKey("course.courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    title = Column(String(200), nullable=False)
    time_limit_mins = Column(Integer, nullable=False, default=45)
    available_from = Column(DateTime(timezone=True), nullable=False)
    available_until = Column(DateTime(timezone=True), nullable=False)
    passcode = Column(String(50), nullable=True)
    ip_filter_range = Column(String(100), nullable=True)
    grade_release_policy = Column(String(30), nullable=False, default="AFTER_CLOSE")
    is_ai_locked = Column(Boolean, nullable=False, default=True)
    status = Column(String(30), nullable=False, default="DRAFT")
    security_mode = Column(String(30), nullable=False, default="CONTROLLED")
    max_attempts = Column(Integer, nullable=False, default=1)
    grade_group_id = Column(UUID(as_uuid=True), nullable=True)
    grade_multiplier = Column(Numeric(3, 2), nullable=False, default=Decimal("1.00"))
    selection_mode = Column(String(20), nullable=False, default="manual")  # manual, random_draw
    draw_rules_json = Column(JSONB, nullable=False, default=list)
    strict_mode_enabled = Column(Boolean, nullable=False, default=False)
    max_strikes = Column(Integer, nullable=False, default=3)
    shuffle_questions = Column(Boolean, nullable=False, default=True)
    shuffle_options = Column(Boolean, nullable=False, default=True)
    snapshot_mode = Column(Boolean, nullable=False, default=True)
    matrix_config = Column(JSONB, nullable=False, default=list)
    grades_published_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class QuizQuestion(Base):
    """Tier-1 immutable quiz-level snapshot in examination.quiz_questions (BR-EXAM-01)."""

    __tablename__ = "quiz_questions"
    __table_args__ = (
        UniqueConstraint("quiz_id", "question_order", name="uq_quiz_question_order"),
        CheckConstraint("default_points > 0", name="chk_quiz_question_points_positive"),
        {"schema": "examination"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quiz_id = Column(
        UUID(as_uuid=True),
        ForeignKey("examination.quizzes.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("examination.questions.id", ondelete="SET NULL"),
        nullable=True,
    )
    lo_id = Column(
        UUID(as_uuid=True),
        ForeignKey("course.learning_objectives.id", ondelete="SET NULL"),
        nullable=True,
    )
    question_order = Column(Integer, nullable=False)
    question_type = Column(String(30), nullable=False, default="MULTIPLE_CHOICE")
    question_text_snapshot = Column(Text, nullable=False)
    options_snapshot = Column(JSONB, nullable=False)
    explanation_snapshot = Column(Text, nullable=True)
    default_points = Column(Numeric(4, 2), nullable=False, default=Decimal("1.00"))
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class QuizSubmission(Base):
    """Student exam attempt with server-locked timer, autosave seq_num, and violations."""

    __tablename__ = "quiz_submissions"
    __table_args__ = (
        UniqueConstraint("quiz_id", "user_id", "attempt_number", name="uq_quiz_user_attempt"),
        CheckConstraint("attempt_number >= 1", name="chk_exam_submission_attempt_positive"),
        CheckConstraint("seq_num >= 0", name="chk_exam_submission_seq_non_negative"),
        {"schema": "examination"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quiz_id = Column(
        UUID(as_uuid=True),
        ForeignKey("examination.quizzes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    attempt_number = Column(Integer, nullable=False, default=1)
    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    seq_num = Column(Integer, nullable=False, default=0)
    student_answers = Column(JSONB, nullable=False, default=dict)
    flagged_questions = Column(JSONB, nullable=False, default=list)
    auto_score = Column(Numeric(4, 2), nullable=True)
    final_score = Column(Numeric(4, 2), nullable=True)
    client_ip = Column(String(45), nullable=True)
    tab_blur_count = Column(Integer, nullable=False, default=0)
    fullscreen_exit_count = Column(Integer, nullable=False, default=0)
    strike_count = Column(Integer, nullable=False, default=0)
    is_flagged = Column(Boolean, nullable=False, default=False)
    violation_logs = Column(JSONB, nullable=False, default=list)
    violation_logs_json = Column(JSONB, nullable=False, default=list)
    status = Column(String(30), nullable=False, default="IN_PROGRESS")


class QuizAttemptQuestion(Base):
    """Tier-2 per-student shuffled question snapshot in examination.quiz_attempt_questions."""

    __tablename__ = "quiz_attempt_questions"
    __table_args__ = ({"schema": "examination"},)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(
        UUID(as_uuid=True),
        ForeignKey("examination.quiz_submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    quiz_question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("examination.quiz_questions.id", ondelete="SET NULL"),
        nullable=True,
    )
    question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("examination.questions.id", ondelete="SET NULL"),
        nullable=True,
    )
    lo_id = Column(
        UUID(as_uuid=True),
        ForeignKey("course.learning_objectives.id", ondelete="SET NULL"),
        nullable=True,
    )
    question_order = Column(Integer, nullable=False)
    question_type = Column(String(30), nullable=False, default="MULTIPLE_CHOICE")
    question_text = Column(Text, nullable=False)
    options_snapshot = Column(JSONB, nullable=False)
    explanation_snapshot = Column(Text, nullable=True)
    default_points = Column(Numeric(4, 2), nullable=False, default=Decimal("1.00"))


class QuizRegrade(Base):
    """48-hour regrade request supporting per-question and entire-class scope."""

    __tablename__ = "quiz_regrades"
    __table_args__ = (
        UniqueConstraint(
            "submission_id",
            "attempt_question_id",
            name="uq_quiz_regrade_submission_question",
        ),
        {"schema": "examination"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(
        UUID(as_uuid=True),
        ForeignKey("examination.quiz_submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("examination.quiz_attempt_questions.id", ondelete="SET NULL"),
        nullable=True,
    )
    student_reason = Column(Text, nullable=False)
    evidence_url = Column(String(500), nullable=True)
    regrade_scope = Column(String(30), nullable=False, default="SINGLE_STUDENT")
    status = Column(String(30), nullable=False, default="PENDING")
    old_score = Column(Numeric(4, 2), nullable=False)
    new_score = Column(Numeric(4, 2), nullable=True)
    reviewer_feedback = Column(Text, nullable=True)
    reviewed_by = Column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
