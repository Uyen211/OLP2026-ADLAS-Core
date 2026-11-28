# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Pydantic v2 request and response schemas for Examination Context (T2-P-M4-01..02)."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field, field_validator, model_validator
from app.modules.course.enums import BloomLevel
from app.modules.examination.enums import (
    GradeReleasePolicy,
    QuestionType,
    QuizStatus,
    RegradeScope,
    RegradeStatus,
    SecurityMode,
    SubmissionStatus,
)


# ------------------------------------------------------------------
# Question Banks
# ------------------------------------------------------------------
class QuestionBankCreate(BaseModel):
    """Payload for POST /api/v1/examinations/courses/{course_id}/question-banks."""

    category_name: str = Field(..., min_length=2, max_length=150)

    @field_validator("category_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("Ten danh muc ngan hang cau hoi phai co it nhat 2 ky tu.")
        return cleaned


class QuestionBankResponse(BaseModel):
    """Question bank summary returned to instructors."""

    id: uuid.UUID
    course_id: uuid.UUID
    category_name: str
    question_count: int = 0
    created_at: datetime


class QuestionFolderCreate(BaseModel):
    """Payload to create a question folder."""

    folder_name: str = Field(..., min_length=1, max_length=100)
    parent_folder_id: Optional[uuid.UUID] = None


class QuestionFolderResponse(BaseModel):
    """Question folder details."""

    id: uuid.UUID
    course_id: uuid.UUID
    folder_name: str
    parent_folder_id: Optional[uuid.UUID] = None
    created_by: Optional[uuid.UUID] = None
    created_at: datetime


# ------------------------------------------------------------------
# Questions
# ------------------------------------------------------------------
class QuestionOptionSchema(BaseModel):
    """Single answer option supporting KaTeX/Code text."""

    id: Optional[str] = Field(None, max_length=64)
    key: str = Field(..., min_length=1, max_length=10)
    text: str = Field(..., min_length=1)
    is_correct: bool = False

    @field_validator("key")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("Ma phuong an khong duoc de trong.")
        return cleaned

    @field_validator("text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Noi dung phuong an khong duoc de trong.")
        return cleaned


def _validate_question_options(
    question_type: QuestionType,
    options: List[QuestionOptionSchema],
) -> None:
    if len(options) < 2:
        raise ValueError("Cau hoi phai co it nhat 2 phuong an tra loi.")

    keys = [o.key for o in options]
    if len(keys) != len(set(keys)):
        raise ValueError("Ma cac phuong an (A, B, C, D) khong duoc trung lap.")

    correct_count = sum(1 for o in options if o.is_correct)
    if question_type == QuestionType.MULTIPLE_CHOICE and correct_count != 1:
        raise ValueError("Cau hoi trac nghiem 1 dap an phai co dung 1 phuong an dung.")
    if question_type == QuestionType.MULTI_SELECT and correct_count < 1:
        raise ValueError("Cau hoi chon nhieu dap an phai co it nhat 1 phuong an dung.")


class QuestionCreate(BaseModel):
    """Payload for POST /api/v1/examinations/courses/{course_id}/questions."""

    bank_id: uuid.UUID
    folder_id: Optional[uuid.UUID] = None
    lo_id: Optional[uuid.UUID] = None
    bloom_level: BloomLevel = BloomLevel.UNDERSTAND
    difficulty: str = "medium"  # easy, medium, hard
    source_ref: Optional[str] = None
    question_text: str = Field(..., min_length=3)
    question_type: QuestionType = QuestionType.MULTIPLE_CHOICE
    default_points: Decimal = Field(Decimal("1.00"), gt=0, le=Decimal("99.99"))
    options: List[QuestionOptionSchema] = Field(..., min_length=2)
    explanation: Optional[str] = None

    @field_validator("question_text")
    @classmethod
    def strip_question_text(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise ValueError("Noi dung cau hoi phai co it nhat 3 ky tu.")
        return cleaned

    @model_validator(mode="after")
    def validate_options(self) -> "QuestionCreate":
        _validate_question_options(self.question_type, self.options)
        return self


class QuestionUpdate(BaseModel):
    """Payload for PUT /api/v1/examinations/questions/{question_id}."""

    bank_id: Optional[uuid.UUID] = None
    folder_id: Optional[uuid.UUID] = None
    lo_id: Optional[uuid.UUID] = None
    bloom_level: Optional[BloomLevel] = None
    difficulty: Optional[str] = None
    source_ref: Optional[str] = None
    question_text: Optional[str] = Field(None, min_length=3)
    question_type: Optional[QuestionType] = None
    default_points: Optional[Decimal] = Field(None, gt=0, le=Decimal("99.99"))
    options: Optional[List[QuestionOptionSchema]] = Field(None, min_length=2)
    explanation: Optional[str] = None

    @field_validator("question_text")
    @classmethod
    def strip_optional_question_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise ValueError("Noi dung cau hoi phai co it nhat 3 ky tu.")
        return cleaned


class QuestionResponse(BaseModel):
    """Question item returned from the question bank."""

    id: uuid.UUID
    bank_id: uuid.UUID
    folder_id: Optional[uuid.UUID] = None
    lo_id: Optional[uuid.UUID] = None
    bloom_level: BloomLevel
    difficulty: str = "medium"
    source_ref: Optional[str] = None
    question_text: str
    question_type: QuestionType
    default_points: Decimal
    options: List[Dict[str, Any]]
    explanation: Optional[str] = None
    is_active: bool = True
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# ------------------------------------------------------------------
# 1-Click Extraction & Draw Rules (TV3 Feature)
# ------------------------------------------------------------------
class ExtractedQuestionDraft(BaseModel):
    """Draft question extracted from DOCX/PDF awaiting instructor confirmation."""

    prompt: str = Field(..., min_length=3)
    options: List[QuestionOptionSchema] = Field(..., min_length=2)
    correct_key: str
    explanation: Optional[str] = None
    difficulty: str = "medium"
    confidence_score: float = 1.0


class ExtractionPreviewResponse(BaseModel):
    """Preview of extracted questions for instructor review."""

    filename: str
    total_extracted: int
    questions: List[ExtractedQuestionDraft]


class ExtractionBatchSaveRequest(BaseModel):
    """Instructor confirms extracted questions to insert into a bank/folder."""

    bank_id: uuid.UUID
    folder_id: Optional[uuid.UUID] = None
    questions: List[ExtractedQuestionDraft]


class DrawRuleSchema(BaseModel):
    """Rule for dynamic random question draw."""

    folder_id: Optional[uuid.UUID] = None
    bank_id: Optional[uuid.UUID] = None
    difficulty: Optional[str] = None  # easy, medium, hard, or None for all
    count: int = Field(..., ge=1, le=500)
    points_per_question: Decimal = Field(Decimal("1.00"), gt=0)


class QuestionDeleteResponse(BaseModel):
    """Outcome of DELETE /api/v1/examinations/questions/{question_id}."""

    question_id: uuid.UUID
    soft_deleted: bool
    message: str


# ------------------------------------------------------------------
# Quizzes, Snapshots & Security Room Settings
# ------------------------------------------------------------------
class QuizMatrixRuleSchema(BaseModel):
    """Single matrix cell specifying how many questions to draw from a bank."""

    bank_id: uuid.UUID
    bloom_level: Optional[BloomLevel] = None
    lo_id: Optional[uuid.UUID] = None
    count: int = Field(..., ge=1, le=500)


class QuizCreate(BaseModel):
    """Payload for POST /api/v1/examinations/courses/{course_id}/quizzes."""

    title: str = Field(..., min_length=3, max_length=200)
    time_limit_mins: int = Field(45, ge=1, le=600)
    available_from: datetime
    available_until: datetime
    passcode: Optional[str] = Field(None, max_length=50)
    ip_filter_range: Optional[str] = Field(None, max_length=100)
    grade_release_policy: GradeReleasePolicy = GradeReleasePolicy.AFTER_CLOSE
    is_ai_locked: bool = True
    security_mode: SecurityMode = SecurityMode.CONTROLLED
    max_attempts: int = Field(1, ge=1, le=100)
    shuffle_questions: bool = True
    shuffle_options: bool = True
    snapshot_mode: bool = True
    matrix_config: List[QuizMatrixRuleSchema] = Field(default_factory=list)
    question_ids: List[uuid.UUID] = Field(default_factory=list)
    grade_group_id: Optional[uuid.UUID] = None
    grade_multiplier: Decimal = Decimal("1.00")
    selection_mode: str = "manual"  # manual, random_draw
    draw_rules: List[DrawRuleSchema] = Field(default_factory=list)
    strict_mode_enabled: bool = False
    max_strikes: int = 3

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise ValueError("Ten ky thi phai co it nhat 3 ky tu.")
        return cleaned


class QuizSettingsUpdate(BaseModel):
    """Payload for PUT /api/v1/examinations/quizzes/{quiz_id}/settings."""

    title: Optional[str] = Field(None, min_length=3, max_length=200)
    time_limit_mins: int = Field(..., ge=1, le=600)
    available_from: datetime
    available_until: datetime
    passcode: Optional[str] = Field(None, max_length=50)
    ip_filter_range: Optional[str] = Field(None, max_length=100)
    security_mode: SecurityMode = SecurityMode.CONTROLLED
    max_attempts: int = Field(1, ge=1, le=100)
    grade_release_policy: GradeReleasePolicy = GradeReleasePolicy.AFTER_CLOSE
    is_ai_locked: bool = True
    shuffle_questions: bool = True
    shuffle_options: bool = True
    grade_group_id: Optional[uuid.UUID] = None
    grade_multiplier: Optional[Decimal] = None
    selection_mode: Optional[str] = None
    draw_rules: Optional[List[DrawRuleSchema]] = None
    strict_mode_enabled: Optional[bool] = None
    max_strikes: Optional[int] = None


class QuizQuestionSnapshotResponse(BaseModel):
    """Frozen Tier-1 quiz question snapshot (sanitized when viewed by students)."""

    id: uuid.UUID
    question_id: Optional[uuid.UUID] = None
    lo_id: Optional[uuid.UUID] = None
    question_order: int
    question_type: QuestionType
    question_text_snapshot: str
    options_snapshot: List[Dict[str, Any]]
    explanation_snapshot: Optional[str] = None
    default_points: Decimal


class QuizSummaryResponse(BaseModel):
    """Quiz summary card for course exam listings."""

    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    status: QuizStatus
    time_limit_mins: int
    available_from: datetime
    available_until: datetime
    security_mode: SecurityMode
    max_attempts: int
    grade_release_policy: GradeReleasePolicy
    grades_published_at: Optional[datetime] = None
    is_ai_locked: bool
    has_passcode: bool
    passcode: Optional[str] = None
    ip_filter_range: Optional[str] = None
    shuffle_questions: bool
    shuffle_options: bool
    snapshot_mode: bool
    question_count: int = 0
    created_at: datetime
    updated_at: datetime


class QuizDetailResponse(QuizSummaryResponse):
    """Detailed quiz view including matrix_config and frozen questions (for instructors)."""

    matrix_config: List[Dict[str, Any]] = Field(default_factory=list)
    questions: List[QuizQuestionSnapshotResponse] = Field(default_factory=list)


class PasscodeRegenerateResponse(BaseModel):
    """Response for POST /api/v1/examinations/quizzes/{quiz_id}/passcode/regenerate."""

    quiz_id: uuid.UUID
    passcode: str


class PublishGradesResponse(BaseModel):
    """Response for POST /api/v1/examinations/quizzes/{quiz_id}/publish-grades."""

    quiz_id: uuid.UUID
    grades_published_at: datetime


# ------------------------------------------------------------------
# Exam Attempts, Resume Exam & 2-Tier Autosave (T2-P-M4-03)
# ------------------------------------------------------------------
class AttemptStartRequest(BaseModel):
    """Payload for POST /api/v1/examinations/quizzes/{quiz_id}/attempts/start."""

    passcode: Optional[str] = Field(None, max_length=50)


class AttemptQuestionResponse(BaseModel):
    """Tier-2 per-student shuffled question (never includes `is_correct` or explanation)."""

    id: uuid.UUID
    question_order: int
    question_type: QuestionType
    question_text: str
    options_snapshot: List[Dict[str, Any]]
    default_points: Decimal


class AttemptStartResponse(BaseModel):
    """Response for starting a new attempt or resuming an active IN_PROGRESS session."""

    submission_id: uuid.UUID
    quiz_id: uuid.UUID
    attempt_number: int
    resumed: bool
    status: SubmissionStatus
    started_at: datetime
    expires_at: datetime
    remaining_seconds: int
    seq_num: int
    student_answers: Dict[str, Any] = Field(default_factory=dict)
    flagged_questions: List[str] = Field(default_factory=list)
    security_mode: SecurityMode
    is_ai_locked: bool
    questions: List[AttemptQuestionResponse]


class AutosaveRequest(BaseModel):
    """Payload for POST /api/v1/examinations/attempts/{submission_id}/autosave."""

    seq_num: int = Field(..., ge=1)
    answers: Dict[str, Any] = Field(default_factory=dict)
    flagged_questions: Optional[List[str]] = None
    tab_blur_delta: int = Field(0, ge=0, le=100)
    fullscreen_exit_delta: int = Field(0, ge=0, le=100)
    violation_event: Optional[Dict[str, Any]] = None


class AutosaveResponse(BaseModel):
    """Acknowledgement for monotonic autosave ingestion."""

    submission_id: uuid.UUID
    accepted: bool
    seq_num: int
    remaining_seconds: int
    tab_blur_count: int
    fullscreen_exit_count: int
    strike_count: Optional[int] = 0
    is_flagged: Optional[bool] = False

    @field_validator("strike_count", mode="before")
    @classmethod
    def _default_strikes(cls, v: Any) -> int:
        return 0 if v is None else v

    @field_validator("is_flagged", mode="before")
    @classmethod
    def _default_flagged(cls, v: Any) -> bool:
        return False if v is None else v


class SubmitAttemptRequest(BaseModel):
    """Optional final answers payload for POST /api/v1/examinations/attempts/{submission_id}/submit."""

    answers: Optional[Dict[str, Any]] = None
    flagged_questions: Optional[List[str]] = None


class SubmitAttemptResponse(BaseModel):
    """Response returned immediately after submitting and auto-grading an attempt."""

    submission_id: uuid.UUID
    quiz_id: uuid.UUID
    status: SubmissionStatus
    submitted_at: datetime
    grades_visible: bool
    auto_score: Optional[Decimal] = None
    final_score: Optional[Decimal] = None


class ActiveSessionResponse(BaseModel):
    """Lightweight session status for GET /quizzes/{quiz_id}/active-session (E-13)."""

    has_active_session: bool
    is_ai_locked: bool
    quiz_id: uuid.UUID
    submission_id: Optional[uuid.UUID] = None
    expires_at: Optional[datetime] = None


# ------------------------------------------------------------------
# Results & 48-Hour Regrade Workflow (T2-P-M4-04)
# ------------------------------------------------------------------
class ResultQuestionAnalysis(BaseModel):
    """Per-question grading breakdown shown once grades are released."""

    attempt_question_id: uuid.UUID
    question_order: int
    question_type: QuestionType
    question_text: str
    default_points: Decimal
    earned_points: Decimal
    is_correct: bool
    selected_keys: List[str] = Field(default_factory=list)
    correct_keys: List[str] = Field(default_factory=list)
    options_snapshot: List[Dict[str, Any]] = Field(default_factory=list)
    explanation_snapshot: Optional[str] = None


class RegradeSummaryResponse(BaseModel):
    """Single regrade request record."""

    id: uuid.UUID
    submission_id: uuid.UUID
    attempt_question_id: Optional[uuid.UUID] = None
    student_reason: str
    evidence_url: Optional[str] = None
    regrade_scope: RegradeScope
    status: RegradeStatus
    old_score: Decimal
    new_score: Optional[Decimal] = None
    reviewer_feedback: Optional[str] = None
    reviewed_by: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime


class AttemptResultResponse(BaseModel):
    """Exam result response respecting `grade_release_policy` and 48h regrade deadline."""

    submission_id: uuid.UUID
    quiz_id: uuid.UUID
    quiz_title: str
    status: SubmissionStatus
    submitted_at: Optional[datetime] = None
    grade_release_policy: GradeReleasePolicy
    grades_visible: bool
    release_timestamp: Optional[datetime] = None
    regrade_deadline: Optional[datetime] = None
    can_request_regrade: bool
    auto_score: Optional[Decimal] = None
    final_score: Optional[Decimal] = None
    questions: List[ResultQuestionAnalysis] = Field(default_factory=list)
    regrades: List[RegradeSummaryResponse] = Field(default_factory=list)


class RegradeCreateRequest(BaseModel):
    """Payload for POST /api/v1/examinations/attempts/{submission_id}/regrades."""

    attempt_question_id: uuid.UUID
    student_reason: str = Field(..., min_length=30, max_length=500)
    evidence_url: Optional[str] = Field(None, max_length=500)

    @field_validator("student_reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 30:
            raise ValueError("Ly do phuc khao phai co tu 30 den 500 ky tu.")
        return cleaned


class RegradeReviewRequest(BaseModel):
    """Payload for POST /api/v1/examinations/regrades/{regrade_id}/review."""

    approved: bool
    regrade_scope: RegradeScope = RegradeScope.SINGLE_STUDENT
    new_score: Optional[Decimal] = Field(None, ge=Decimal("0.0"), le=Decimal("10.0"))
    correct_option_ids: Optional[List[str]] = None
    award_full_question_credit: bool = False
    reviewer_feedback: str = Field(..., min_length=3, max_length=1000)

    @field_validator("reviewer_feedback")
    @classmethod
    def strip_feedback(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise ValueError("Phan hoi cua giang vien phai co it nhat 3 ky tu.")
        return cleaned


class RegradeReviewResponse(BaseModel):
    """Result of instructor reviewing a regrade request (SINGLE_STUDENT or ENTIRE_CLASS)."""

    regrade: RegradeSummaryResponse
    affected_submissions_count: int = 0
    closed_pending_regrades_count: int = 0


# ------------------------------------------------------------------
# TV3 Extensions: Folder Stats, Violations & Alert Timeline Review
# ------------------------------------------------------------------
class QuestionFolderStatsItem(BaseModel):
    folder_id: Optional[uuid.UUID] = None
    name: str
    EASY: int = 0
    MEDIUM: int = 0
    HARD: int = 0
    total: int = 0


class QuestionFolderStatsResponse(BaseModel):
    folders: List[QuestionFolderStatsItem]


class ViolationRecordRequest(BaseModel):
    violation_type: str = Field(..., description="TAB_SWITCH, EXIT_FULLSCREEN, WINDOW_BLUR, or COPY_PASTE")
    client_ts: Optional[str] = None


class ViolationRecordResponse(BaseModel):
    strike_count: int
    max_strikes: int
    is_flagged: bool


class AttemptReviewSummaryResponse(BaseModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    user_id: uuid.UUID
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    attempt_number: int
    strike_count: int = 0
    is_flagged: bool = False
    auto_score: Optional[Decimal] = None
    final_score: Optional[Decimal] = None
    status: str
    review_decision: Optional[str] = None
    instructor_note: Optional[str] = None
    violation_logs: List[Dict[str, Any]] = Field(default_factory=list)
    started_at: datetime
    submitted_at: Optional[datetime] = None


class FinalizeReviewRequest(BaseModel):
    review_decision: str = Field(..., description="ACCEPTED or INVALIDATED")
    essay_scores: Dict[str, float] = Field(default_factory=dict)
    instructor_note: Optional[str] = None
