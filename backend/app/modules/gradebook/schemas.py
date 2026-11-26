# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Pydantic v2 DTO schemas for Gradebook, TT08 Calculation, AI Rubric Proposal, and SpeedGrader."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.modules.gradebook.enums import (
    EvidenceFlag,
    GradeItemType,
    GradingStatus,
    PostGradesScope,
)


# ---------------------------------------------------------------------------
# T2-P-M5-01: Gradebook Structure Schemas
# ---------------------------------------------------------------------------
class GradeGroupInput(BaseModel):
    """Single grade category payload when saving full gradebook structure."""

    id: Optional[uuid.UUID] = None
    group_name: str = Field(..., min_length=1, max_length=100)
    weight_percent: int = Field(..., ge=1, le=100)
    drop_lowest_count: int = Field(0, ge=0, le=5)
    is_hurdle: bool = False
    hurdle_min_score: Decimal = Field(Decimal("4.00"), ge=Decimal("0.00"), le=Decimal("10.00"))

    @field_validator("group_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Group name cannot be blank.")
        return trimmed


class GradebookStructureSaveRequest(BaseModel):
    """Batch save request for course gradebook structure (total weight must equal 100%)."""

    groups: List[GradeGroupInput] = Field(..., min_length=1)


class GradeGroupDeleteRequest(BaseModel):
    """Confirmation payload when deleting a grade group that contains student grades."""

    confirmation_text: Optional[str] = None


class GradeColumnCreateRequest(BaseModel):
    """Create a sub-column inside an existing grade group (Subflow A-1 of M5-01)."""

    group_id: uuid.UUID
    title: str = Field(..., min_length=1, max_length=150)
    item_type: GradeItemType = GradeItemType.MANUAL
    item_id: Optional[uuid.UUID] = None
    max_points: Decimal = Field(Decimal("10.00"), gt=Decimal("0.00"), le=Decimal("100.00"))
    is_muted: bool = True

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Column title cannot be blank.")
        return trimmed


class GradeColumnResponse(BaseModel):
    """Read DTO for a single gradebook column."""

    id: uuid.UUID
    course_id: uuid.UUID
    group_id: uuid.UUID
    item_type: str
    item_id: Optional[uuid.UUID] = None
    title: str
    max_points: Decimal
    is_muted: bool

    model_config = ConfigDict(from_attributes=True)


class GradeGroupResponse(BaseModel):
    """Read DTO for a grade category including its child columns."""

    id: uuid.UUID
    course_id: uuid.UUID
    group_name: str
    weight_percent: int
    drop_lowest_count: int
    is_hurdle: bool
    hurdle_min_score: Decimal
    columns: List[GradeColumnResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class GradebookStructureResponse(BaseModel):
    """Complete course gradebook structure with real-time weight sum and lock status."""

    course_id: uuid.UUID
    total_weight_percent: int
    is_weight_valid: bool
    is_locked: bool
    locked_at: Optional[datetime] = None
    groups: List[GradeGroupResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# T2-P-M5-02: Calculation, Overview & Student Grades Schemas
# ---------------------------------------------------------------------------
class CellGradeDTO(BaseModel):
    """Single cell score for a student in a column."""

    column_id: uuid.UUID
    grade_id: Optional[uuid.UUID] = None
    submission_id: Optional[uuid.UUID] = None
    official_score: Optional[Decimal] = None
    proposed_ai_score: Optional[Decimal] = None
    evidence_flag: Optional[str] = None
    grading_status: str = GradingStatus.UNGRADED.value
    is_muted: bool = True
    is_overridden: bool = False
    instructor_feedback: Optional[str] = None
    voice_feedback_url: Optional[str] = None


class StudentCourseSummaryRow(BaseModel):
    """One student row in the class Gradebook overview table."""

    user_id: uuid.UUID
    user_code: Optional[str] = None
    full_name: str
    email: str
    column_grades: Dict[str, CellGradeDTO] = Field(default_factory=dict)
    group_averages: Dict[str, Optional[Decimal]] = Field(default_factory=dict)
    final_score_10: Optional[Decimal] = None
    letter_grade: Optional[str] = None
    score_4: Optional[Decimal] = None
    is_passed: Optional[bool] = None
    hurdle_failed: bool = False
    is_provisional: bool = False
    missing_columns_count: int = 0


class GradeDistributionBucket(BaseModel):
    """One bar in the class grade distribution chart (Subflow A-1 of M5-02)."""

    label: str
    range_hint: str
    count: int
    percentage: float


class ClassGradebookOverviewResponse(BaseModel):
    """Full instructor gradebook overview with TT08 calculations and distribution stats."""

    course_id: uuid.UUID
    is_locked: bool
    locked_at: Optional[datetime] = None
    locked_by_name: Optional[str] = None
    total_students: int
    passed_count: int
    failed_count: int
    hurdle_failed_count: int
    incomplete_students_count: int
    class_average_10: Optional[Decimal] = None
    pass_rate_pct: float
    fail_rate_pct: float
    groups: List[GradeGroupResponse] = Field(default_factory=list)
    students: List[StudentCourseSummaryRow] = Field(default_factory=list)
    distribution: List[GradeDistributionBucket] = Field(default_factory=list)


class StudentMyGradeItem(BaseModel):
    """Single grade column visible to a student (respecting BR-09 Muted Policy)."""

    column_id: uuid.UUID
    group_name: str
    weight_percent: int
    is_hurdle: bool
    title: str
    item_type: str
    max_points: Decimal
    is_muted: bool
    official_score: Optional[Decimal] = None
    instructor_feedback: Optional[str] = None
    voice_feedback_url: Optional[str] = None
    status_label: str


class StudentMyGradesResponse(BaseModel):
    """Student-only gradebook summary with muted scores strictly withheld."""

    course_id: uuid.UUID
    is_locked: bool
    items: List[StudentMyGradeItem] = Field(default_factory=list)
    final_score_10: Optional[Decimal] = None
    letter_grade: Optional[str] = None
    score_4: Optional[Decimal] = None
    is_passed: Optional[bool] = None
    hurdle_failed: bool = False
    is_provisional: bool = False


class ManualGradeUpsertRequest(BaseModel):
    """Direct score entry for manual columns in the gradebook table."""

    user_id: uuid.UUID
    official_score: Decimal = Field(..., ge=Decimal("0.00"), le=Decimal("10.00"))
    instructor_feedback: Optional[str] = None
    reason: Optional[str] = None


# ---------------------------------------------------------------------------
# T2-I-M5-03 & T2-P-M5-04: AI Rubric Proposal & SpeedGrader 3-Column Schemas
# ---------------------------------------------------------------------------
class CitationItemSchema(BaseModel):
    """Single factual evidence citation extracted from submission or Viva transcript."""

    source_type: str = Field(..., pattern="^(SUBMISSION|VIVA)$")
    reference: str
    excerpt: str


class CriterionProposalSchema(BaseModel):
    """AI proposed score and citations for one Rubric criterion."""

    criterion_id: str
    criterion_title: str
    max_points: Decimal
    proposed_points: Decimal
    rating_level_label: str
    explanation: str
    citations: List[CitationItemSchema] = Field(default_factory=list)


class RubricProposalResponse(BaseModel):
    """Structured AI Rubric Proposal response stored in gradebook.grades (T2-I-M5-03)."""

    submission_id: uuid.UUID
    evidence_flag: EvidenceFlag
    proposed_total_score: Optional[Decimal] = None
    summary_comment: str
    generation_source: str = "gemini_live"
    criteria_proposals: List[CriterionProposalSchema] = Field(default_factory=list)


class SpeedGraderSubmissionNavItem(BaseModel):
    """Student navigation item for SpeedGrader top bar dropdown & filters."""

    submission_id: uuid.UUID
    user_id: uuid.UUID
    user_code: Optional[str] = None
    student_name: str
    student_email: str
    version: int
    submitted_at: datetime
    is_late: bool
    late_penalty_applied: float
    viva_status: Optional[str] = None
    grading_status: str = GradingStatus.UNGRADED.value
    official_score: Optional[Decimal] = None
    proposed_ai_score: Optional[Decimal] = None
    evidence_flag: Optional[str] = None


class SpeedGraderSubmissionListResponse(BaseModel):
    """List of submissions for an assignment with grading progress counter."""

    assignment_id: uuid.UUID
    assignment_title: str
    course_id: uuid.UUID
    total_submissions: int
    graded_count: int
    progress_percent: float
    items: List[SpeedGraderSubmissionNavItem] = Field(default_factory=list)


class RubricRatingLevelDTO(BaseModel):
    """One mastery rating level inside a rubric criterion."""

    level: str
    label: str
    points: Decimal
    description: str


class RubricCriterionViewDTO(BaseModel):
    """Rubric criterion rendered in SpeedGrader Column 3."""

    id: uuid.UUID
    lo_id: Optional[uuid.UUID] = None
    competency_code: Optional[str] = None
    title: str
    description: Optional[str] = None
    max_points: Decimal
    order_index: int
    rating_levels: List[Dict[str, Any]] = Field(default_factory=list)


class SpeedGraderVersionItemDTO(BaseModel):
    """Historical submission version entry for v1/v2 switching."""

    submission_id: uuid.UUID
    version: int
    submitted_at: datetime
    is_late: bool
    file_url: Optional[str] = None
    git_repo_url: Optional[str] = None


class SpeedGraderWorkspaceResponse(BaseModel):
    """Complete 3-column aggregated payload for SpeedGrader Cockpit (T2-P-M5-04)."""

    course_id: uuid.UUID
    course_name: str
    assignment_id: uuid.UUID
    assignment_title: str
    column_id: uuid.UUID
    is_gradebook_locked: bool
    is_column_muted: bool
    # Column 1: Submission artifact & AI disclosure
    submission_id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    student_email: str
    student_code: Optional[str] = None
    version: int
    versions: List[SpeedGraderVersionItemDTO] = Field(default_factory=list)
    project_title: Optional[str] = None
    file_url: Optional[str] = None
    git_repo_url: Optional[str] = None
    comments: Optional[str] = None
    self_contribution_pct: int
    ai_disclosure_data: Dict[str, Any] = Field(default_factory=dict)
    submitted_at: datetime
    is_late: bool
    late_penalty_applied: float
    # Column 2: Call 1 AI Digest, Viva Q&A & Integrity Logs
    missing_viva: bool = False
    viva_status: Optional[str] = None
    viva_started_at: Optional[datetime] = None
    viva_completed_at: Optional[datetime] = None
    ai_digest_summary: Optional[str] = None
    digest_type: Optional[str] = None
    summarizer_mode: Optional[str] = None
    generation_source: Optional[str] = None
    questions: List[Dict[str, Any]] = Field(default_factory=list)
    answers: Dict[str, Any] = Field(default_factory=dict)
    violation_logs: List[Dict[str, Any]] = Field(default_factory=list)
    window_blur_count: int = 0
    paste_attempt_count: int = 0
    # Column 3: Rubric, AI Proposal & Instructor Grading Cockpit
    rubric_id: Optional[uuid.UUID] = None
    rubric_title: Optional[str] = None
    rubric_criteria: List[RubricCriterionViewDTO] = Field(default_factory=list)
    ai_proposal: Optional[RubricProposalResponse] = None
    grade_id: Optional[uuid.UUID] = None
    official_score: Optional[Decimal] = None
    rubric_scores: Dict[str, Any] = Field(default_factory=dict)
    instructor_feedback: Optional[str] = None
    voice_feedback_url: Optional[str] = None
    is_overridden: bool = False
    grading_status: str = GradingStatus.UNGRADED.value
    graded_at: Optional[datetime] = None


class SpeedGraderSaveGradeRequest(BaseModel):
    """Payload to save official score, rubric selections, feedback, and override reason."""

    official_score: Decimal = Field(..., ge=Decimal("0.00"), le=Decimal("10.00"))
    rubric_scores: Dict[str, Any] = Field(default_factory=dict)
    instructor_feedback: Optional[str] = None
    voice_feedback_url: Optional[str] = None
    override_reason: Optional[str] = None


class SpeedGraderDraftRequest(BaseModel):
    """30-second autosave draft payload for instructor feedback (BR-SPEED-01)."""

    instructor_feedback: Optional[str] = None
    rubric_scores: Optional[Dict[str, Any]] = None


class VersionDiffLineDTO(BaseModel):
    """One line of a v1 vs v2 submission diff."""

    line_type: str  # "context", "added", "removed"
    content: str


class VersionDiffResponse(BaseModel):
    """Structured side-by-side diff payload between two submission versions (Subflow A-2)."""

    v1_submission_id: uuid.UUID
    v2_submission_id: uuid.UUID
    v1_version: int
    v2_version: int
    summary: str
    lines: List[VersionDiffLineDTO] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# T2-P-M5-05: Muted Policy, Poka-Yoke Final Lock & Audit Trail Schemas
# ---------------------------------------------------------------------------
class PostGradesRequest(BaseModel):
    """Request to unmute and publish grades for a column."""

    scope: PostGradesScope = PostGradesScope.ALL
    send_notification: bool = True


class PostGradesResponse(BaseModel):
    """Result after publishing grades for a column."""

    column_id: uuid.UUID
    is_muted: bool
    scope: str
    published_grades_count: int
    notification_queued: bool


class GradebookLockPreviewResponse(BaseModel):
    """Class summary statistics shown inside the Poka-yoke lock modal (T2-P-M5-05)."""

    course_id: uuid.UUID
    is_locked: bool
    total_students: int
    passed_count: int
    failed_count: int
    hurdle_failed_count: int
    pass_rate_pct: float
    fail_rate_pct: float
    class_average_10: Optional[Decimal] = None
    muted_columns: List[str] = Field(default_factory=list)
    can_lock: bool


class GradebookLockRequest(BaseModel):
    """Poka-yoke lock request requiring exact 'KHOA DIEM' confirmation phrase."""

    confirmation_text: str


class GradebookLockResponse(BaseModel):
    """Result of sealing a course gradebook."""

    course_id: uuid.UUID
    is_locked: bool
    locked_at: datetime
    locked_by: Optional[uuid.UUID] = None
    locked_by_name: Optional[str] = None


class EmergencyUnlockRequest(BaseModel):
    """Subflow A-1 request to temporarily unlock a sealed gradebook after formal appeal."""

    decision_code: str = Field(..., min_length=3, max_length=100)
    reason: str = Field(..., min_length=30, max_length=1000)


class GradeAuditLogResponse(BaseModel):
    """Immutable audit log item returned for academic transparency."""

    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    action_type: str
    entity_name: str
    entity_id: uuid.UUID
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
