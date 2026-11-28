# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Pydantic DTOs for assignment authoring, Mastery rubric and integrity pledge (TV3)."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator

AIPolicyLevel = Literal["GREEN", "YELLOW", "RED"]
SubmissionType = Literal["FILE_UPLOAD", "GIT_REPOSITORY", "HYBRID"]
MasteryLevelCode = Literal["EXCELLENT", "GOOD", "PROFICIENT", "INSUFFICIENT"]

MASTERY_LEVELS = ("EXCELLENT", "GOOD", "PROFICIENT", "INSUFFICIENT")
RUBRIC_TOTAL_POINTS = Decimal("10.0")


def _clean_title(value: str) -> str:
    trimmed = value.strip()
    if not 5 <= len(trimmed) <= 150:
        raise ValueError("Title must contain between 5 and 150 characters.")
    return trimmed


# ----------------------------------------------------------------------
# Assignment authoring (T2-P-M3-01)
# ----------------------------------------------------------------------
class AssignmentCreateRequest(BaseModel):
    """Payload to create an assignment as Draft (default) or Published."""

    title: str
    instructions: str = Field(..., min_length=1)
    attachment_url: Optional[str] = Field(None, max_length=500)
    submission_type: SubmissionType = "FILE_UPLOAD"
    allowed_extensions: str = Field(".zip,.pdf,.docx", max_length=100)
    max_file_size_mb: int = Field(50, ge=1, le=500)
    is_group_assignment: bool = False
    is_transfer_task: bool = False
    assignment_type: str = "standard"
    group_min_size: int = Field(1, ge=1, le=50)
    group_max_size: int = Field(1, ge=1, le=50)
    group_formation_deadline: Optional[datetime] = None
    grade_group_id: Optional[uuid.UUID] = None
    available_from: Optional[datetime] = None
    due_date: datetime
    until_date: Optional[datetime] = None
    late_penalty_percent: Decimal = Field(Decimal("5.0"), ge=0, le=100)
    is_viva_required: bool = True
    viva_question_count: int = Field(3, ge=1, le=10)
    ai_policy_level: AIPolicyLevel = "YELLOW"
    max_attempts: Optional[int] = Field(None, ge=1, le=50)
    publish: bool = False

    @field_validator("title")
    @classmethod
    def _validate_title(cls, v: str) -> str:
        return _clean_title(v)


class AssignmentUpdateRequest(BaseModel):
    """Partial update of assignment configuration (all fields optional)."""

    title: Optional[str] = None
    instructions: Optional[str] = Field(None, min_length=1)
    attachment_url: Optional[str] = Field(None, max_length=500)
    submission_type: Optional[SubmissionType] = None
    allowed_extensions: Optional[str] = Field(None, max_length=100)
    max_file_size_mb: Optional[int] = Field(None, ge=1, le=500)
    is_group_assignment: Optional[bool] = None
    is_transfer_task: Optional[bool] = None
    assignment_type: Optional[str] = None
    group_min_size: Optional[int] = Field(None, ge=1, le=50)
    group_max_size: Optional[int] = Field(None, ge=1, le=50)
    group_formation_deadline: Optional[datetime] = None
    grade_group_id: Optional[uuid.UUID] = None
    available_from: Optional[datetime] = None
    due_date: Optional[datetime] = None
    until_date: Optional[datetime] = None
    late_penalty_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    is_viva_required: Optional[bool] = None
    viva_question_count: Optional[int] = Field(None, ge=1, le=10)
    ai_policy_level: Optional[AIPolicyLevel] = None
    max_attempts: Optional[int] = Field(None, ge=1, le=50)

    @field_validator("title")
    @classmethod
    def _validate_title(cls, v: Optional[str]) -> Optional[str]:
        return None if v is None else _clean_title(v)


class AssignmentAuthoringResponse(BaseModel):
    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    instructions: str
    attachment_url: Optional[str] = None
    submission_type: str
    allowed_extensions: str
    max_file_size_mb: int
    is_group_assignment: bool
    is_transfer_task: bool
    assignment_type: Optional[str] = "standard"
    group_min_size: Optional[int] = 1
    group_max_size: Optional[int] = 1
    group_formation_deadline: Optional[datetime] = None
    grade_group_id: Optional[uuid.UUID] = None
    available_from: Optional[datetime] = None

    @field_validator("assignment_type", mode="before")
    @classmethod
    def _default_type(cls, v: Any) -> str:
        return v or "standard"

    @field_validator("group_min_size", mode="before")
    @classmethod
    def _default_min_size(cls, v: Any) -> int:
        return 1 if v is None else v

    @field_validator("group_max_size", mode="before")
    @classmethod
    def _default_max_size(cls, v: Any) -> int:
        return 1 if v is None else v
    due_date: datetime
    until_date: Optional[datetime] = None
    late_penalty_percent: float
    is_viva_required: bool
    viva_question_count: int
    ai_policy_level: str
    is_published: bool
    max_points: float
    max_attempts: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class AssignmentDeleteResponse(BaseModel):
    id: uuid.UUID
    deleted: bool = True


# ----------------------------------------------------------------------
# Rubric (T2-P-M3-02)
# ----------------------------------------------------------------------
class MasteryLevelSchema(BaseModel):
    """One of the four Mastery levels of a criterion."""

    level: MasteryLevelCode
    label: Optional[str] = Field(None, max_length=100)
    description: str = Field("", max_length=1000)
    points: Decimal = Field(..., ge=0, decimal_places=1)


class RubricCriterionSchema(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    lo_id: Optional[uuid.UUID] = None
    competency_code: Optional[str] = Field(None, max_length=20)
    max_points: Decimal = Field(..., gt=0, decimal_places=1)
    rating_levels: List[MasteryLevelSchema] = Field(..., min_length=4, max_length=4)

    @field_validator("rating_levels")
    @classmethod
    def _validate_levels(cls, levels: List[MasteryLevelSchema]) -> List[MasteryLevelSchema]:
        codes = [lv.level for lv in levels]
        if set(codes) != set(MASTERY_LEVELS) or len(codes) != 4:
            raise ValueError("Exactly 4 distinct Mastery levels are required.")
        order = {code: i for i, code in enumerate(MASTERY_LEVELS)}
        return sorted(levels, key=lambda lv: order[lv.level])


class RubricSaveRequest(BaseModel):
    title: str = Field("Rubric", min_length=1, max_length=200)
    criteria: List[RubricCriterionSchema] = Field(..., min_length=1)

    def total_points(self) -> Decimal:
        """Exact Decimal sum of all criterion max points."""
        return sum((c.max_points for c in self.criteria), Decimal("0"))


class RubricCriterionResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    lo_id: Optional[uuid.UUID] = None
    competency_code: Optional[str] = None
    max_points: float
    rating_levels: List[Dict[str, Any]]
    order_index: int


class RubricResponse(BaseModel):
    assignment_id: uuid.UUID
    exists: bool = False
    rubric_id: Optional[uuid.UUID] = None
    title: Optional[str] = None
    total_points: float = 10.0
    is_frozen: bool = False
    version: int = 0
    submission_count: int = 0
    criteria: List[RubricCriterionResponse] = Field(default_factory=list)


# ----------------------------------------------------------------------
# Integrity pledge (T2-P-M3-03)
# ----------------------------------------------------------------------
class PledgeTerm(BaseModel):
    code: str
    text: str


class PledgeSignRequest(BaseModel):
    accepted: bool = Field(..., description="Student ticked the pledge checkbox")
    self_contribution_pct: int = Field(100, ge=0, le=100)
    tools_used: List[str] = Field(default_factory=list)
    usage_description: Optional[str] = Field(None, max_length=1000)


class PledgeStatusResponse(BaseModel):
    assignment_id: uuid.UUID
    pledge_version: str
    ai_policy_level: str
    terms: List[PledgeTerm]
    signed: bool = False
    signed_at: Optional[datetime] = None
    self_contribution_pct: Optional[int] = None


class PledgeSignResponse(PledgeStatusResponse):
    pledge_id: uuid.UUID


# ----------------------------------------------------------------------
# Milestones (TV3 Feature)
# ----------------------------------------------------------------------
class MilestoneCreateSchema(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    weight_percent: Decimal = Field(..., ge=0, le=100)
    due_date: datetime
    until_date: Optional[datetime] = None
    order_index: int = Field(1, ge=1)

    @field_validator("until_date")
    @classmethod
    def _validate_dates(cls, until_date: Optional[datetime], info: Any) -> Optional[datetime]:
        due_date = info.data.get("due_date")
        if due_date and until_date and until_date < due_date:
            raise ValueError("Milestone until_date cannot be earlier than due_date.")
        return until_date


class MilestoneUpdateSchema(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    weight_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    due_date: Optional[datetime] = None
    until_date: Optional[datetime] = None
    order_index: Optional[int] = Field(None, ge=1)


class MilestoneResponse(BaseModel):
    id: uuid.UUID
    assignment_id: uuid.UUID
    title: str
    description: Optional[str] = None
    weight_percent: float
    due_date: datetime
    until_date: Optional[datetime] = None
    order_index: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MilestonesBatchCreateRequest(BaseModel):
    milestones: List[MilestoneCreateSchema]

    @field_validator("milestones")
    @classmethod
    def _validate_weights_sum(cls, v: List[MilestoneCreateSchema]) -> List[MilestoneCreateSchema]:
        if not v:
            return v
        total = sum(m.weight_percent for m in v)
        if total != Decimal("100.0"):
            raise ValueError(f"Total weight of milestones must be exactly 100% (got {total}%).")
        return v


# ----------------------------------------------------------------------
# Topics & Groups (TV3 Feature)
# ----------------------------------------------------------------------
class TopicCreateRequest(BaseModel):
    topic_code: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    max_groups: int = Field(1, ge=1, le=100)


class TopicResponse(BaseModel):
    id: uuid.UUID
    assignment_id: uuid.UUID
    topic_code: str
    title: str
    description: Optional[str] = None
    max_groups: int
    current_groups_count: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class TopicSelectRequest(BaseModel):
    topic_id: uuid.UUID


class GroupMemberResponse(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    student_id: uuid.UUID
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    role: str = "MEMBER"
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentGroupCreateRequest(BaseModel):
    group_name: str = Field(..., min_length=1, max_length=100)
    topic_id: Optional[uuid.UUID] = None
    member_ids: List[uuid.UUID] = Field(default_factory=list)


class StudentGroupResponse(BaseModel):
    id: uuid.UUID
    assignment_id: uuid.UUID
    group_name: str
    topic_id: Optional[uuid.UUID] = None
    topic_code: Optional[str] = None
    topic_title: Optional[str] = None
    leader_student_id: uuid.UUID
    is_finalized: bool
    members: List[GroupMemberResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------------------------------------
# Blind Peer Review & Factor Fi (TV3 Feature)
# ----------------------------------------------------------------------
class PeerReviewSubmitRequest(BaseModel):
    milestone_id: Optional[uuid.UUID] = None
    reviewee_id: uuid.UUID
    criteria_scores: Dict[str, float] = Field(default_factory=dict)
    total_score: Decimal = Field(..., ge=0, le=100)
    comment: Optional[str] = None


class PeerReviewResponse(BaseModel):
    id: uuid.UUID
    assignment_id: uuid.UUID
    milestone_id: Optional[uuid.UUID] = None
    reviewee_id: uuid.UUID
    criteria_scores_json: Dict[str, Any] = Field(default_factory=dict)
    total_score: float
    comment: Optional[str] = None
    submitted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PeerReviewMemberSummary(BaseModel):
    student_id: uuid.UUID
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    average_score_received: float
    group_average_score: float
    factor_f: float
    raw_grade: float
    adjusted_grade: float


class PeerReviewSummaryResponse(BaseModel):
    assignment_id: uuid.UUID
    group_id: uuid.UUID
    milestone_id: Optional[uuid.UUID] = None
    summaries: List[PeerReviewMemberSummary] = Field(default_factory=list)
