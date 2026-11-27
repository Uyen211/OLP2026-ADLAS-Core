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
    available_from: Optional[datetime] = None
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
