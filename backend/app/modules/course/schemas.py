# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Pydantic v2 request and response schemas for Course & Roster Management."""

from datetime import date, datetime, timedelta
from typing import List, Optional
import uuid
from pydantic import BaseModel, Field, field_validator, model_validator
from app.modules.course.enums import (
    BloomLevel,
    ContextualRole,
    CourseStatus,
    EnrollmentStatus,
    GroupingMode,
    RosterRowStatus,
)


class CourseCreate(BaseModel):
    """Payload for POST /api/v1/courses."""

    course_code: str = Field(..., pattern=r"^[A-Z0-9_-]{2,30}$")
    section_code: str = Field(..., min_length=1, max_length=30)
    name: str = Field(..., min_length=3, max_length=200)
    semester: str = Field(..., min_length=2, max_length=50)
    credits: int = Field(..., ge=1, le=6)
    grading_scheme: str = Field("SCALE_10", max_length=30)
    start_date: date
    end_date: date
    syllabus_text: Optional[str] = None
    is_template: bool = False

    @field_validator("section_code", "name", "semester")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Truong nay khong duoc de trong.")
        return cleaned

    @model_validator(mode="after")
    def validate_date_span(self) -> "CourseCreate":
        if self.end_date < self.start_date + timedelta(days=7):
            raise ValueError("Ngay ket thuc phai sau ngay bat dau it nhat 7 ngay.")
        return self


class CourseCloneRequest(BaseModel):
    """Payload for POST /api/v1/courses/clone (BR-03)."""

    template_id: uuid.UUID
    section_code: str = Field(..., min_length=1, max_length=30)
    semester: str = Field(..., min_length=2, max_length=50)
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_date_span(self) -> "CourseCloneRequest":
        if self.end_date < self.start_date + timedelta(days=7):
            raise ValueError("Ngay ket thuc phai sau ngay bat dau it nhat 7 ngay.")
        return self


class SyllabusUpdate(BaseModel):
    """Payload for PUT /api/v1/courses/{id}/syllabus."""

    name: str = Field(..., min_length=3, max_length=200)
    credits: int = Field(..., ge=1, le=6)
    syllabus_text: Optional[str] = None


class SyllabusImportTemplateRequest(BaseModel):
    """Payload for POST /api/v1/courses/{id}/syllabus/import-template."""

    template_id: uuid.UUID


class SyllabusImportTemplateResponse(BaseModel):
    """Result of importing syllabus and LOs from a course template."""

    copied_los: int
    skipped_duplicate_codes: List[str] = Field(default_factory=list)


class CourseStatusUpdateRequest(BaseModel):
    """Payload for POST /api/v1/courses/{id}/status."""

    target_status: CourseStatus


class LOResponse(BaseModel):
    """Learning Objective output DTO."""

    id: uuid.UUID
    course_id: uuid.UUID
    code: str
    description: str
    detail_description: Optional[str] = None
    weight_percent: Optional[float] = None
    bloom_level: BloomLevel
    order_index: int
    created_at: datetime
    updated_at: datetime


class LOCreate(BaseModel):
    """Payload for POST /api/v1/courses/{id}/learning-objectives."""

    code: str = Field(..., pattern=r"^[A-Za-z0-9-]{2,30}$")
    description: str = Field(..., min_length=10, max_length=150)
    detail_description: Optional[str] = Field(None, max_length=1000)
    weight_percent: Optional[float] = Field(None, ge=0, le=100)
    bloom_level: BloomLevel = BloomLevel.UNDERSTAND

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class LOUpdate(BaseModel):
    """Payload for PUT /api/v1/courses/{id}/learning-objectives/{lo_id}."""

    code: Optional[str] = Field(None, pattern=r"^[A-Za-z0-9-]{2,30}$")
    description: Optional[str] = Field(None, min_length=10, max_length=150)
    detail_description: Optional[str] = Field(None, max_length=1000)
    weight_percent: Optional[float] = Field(None, ge=0, le=100)
    bloom_level: Optional[BloomLevel] = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: Optional[str]) -> Optional[str]:
        return value.strip().upper() if value is not None else None


class LOOrderUpdateRequest(BaseModel):
    """Payload for PUT /api/v1/courses/{id}/learning-objectives/order."""

    ordered_ids: List[uuid.UUID] = Field(..., min_length=1)


class CourseSummary(BaseModel):
    """Summary card representation for course listing."""

    id: uuid.UUID
    course_code: str
    section_code: str
    name: str
    semester: str
    credits: int
    start_date: date
    end_date: date
    is_template: bool
    is_enrollment_open: bool
    status: CourseStatus
    my_role: Optional[ContextualRole] = None
    student_count: int = 0
    lo_count: int = 0


class CourseDetail(CourseSummary):
    """Detailed course representation including syllabus, join code, and LOs."""

    grading_scheme: str
    syllabus_text: Optional[str] = None
    join_code: Optional[str] = None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    learning_objectives: List[LOResponse] = Field(default_factory=list)


class JoinCodeResponse(BaseModel):
    """Join code metadata for instructor management."""

    join_code: Optional[str]
    is_enrollment_open: bool


class JoinCodeSettingsRequest(BaseModel):
    """Toggle self-enrollment via join code (BR-ROSTER-02)."""

    is_enrollment_open: bool


class JoinCourseRequest(BaseModel):
    """Payload for student self-enrollment via 6-character join code."""

    join_code: str = Field(..., min_length=6, max_length=10)


class RosterStudentCreate(BaseModel):
    """Payload for manually adding a single student to a course roster."""

    user_code: str = Field(..., min_length=2, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=150)
    email: str = Field(..., min_length=3, max_length=150)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if "@" not in cleaned or "." not in cleaned.split("@")[-1]:
            raise ValueError("Dia chi email khong hop le.")
        return cleaned


class RosterItemResponse(BaseModel):
    """Single enrolled student entry in the roster table."""

    user_id: uuid.UUID
    user_code: Optional[str]
    full_name: str
    email: str
    group_name: Optional[str] = None
    status: EnrollmentStatus
    enrolled_at: datetime


class RosterPageResponse(BaseModel):
    """Paginated student roster response."""

    total: int
    page: int
    page_size: int
    items: List[RosterItemResponse]


class RosterPreviewRow(BaseModel):
    """Preview row returned before confirming Excel/CSV import."""

    row_number: int
    user_code: str
    full_name: str
    email: str
    status: RosterRowStatus
    reason: Optional[str] = None


class RosterRowError(BaseModel):
    """Validation error detail for an invalid roster row."""

    row_number: int
    reason: str


class RosterPreviewResponse(BaseModel):
    """Response for POST /api/v1/courses/{id}/roster/preview."""

    total_rows: int
    valid_count: int
    duplicate_count: int
    error_count: int
    missing_columns: List[str] = Field(default_factory=list)
    preview_rows: List[RosterPreviewRow] = Field(default_factory=list)
    errors: List[RosterRowError] = Field(default_factory=list)


class RosterImportResult(BaseModel):
    """Response for POST /api/v1/courses/{id}/roster/confirm."""

    added: int
    skipped_duplicates: int
    created_accounts: int
    errors: List[RosterRowError] = Field(default_factory=list)


class GroupMemberResponse(BaseModel):
    """Student member inside a project group."""

    user_id: uuid.UUID
    user_code: Optional[str]
    full_name: str
    email: str


class GroupItemResponse(BaseModel):
    """Single project group with its members."""

    id: Optional[uuid.UUID] = None
    name: str
    members: List[GroupMemberResponse] = Field(default_factory=list)


class GroupSetResponse(BaseModel):
    """Named collection of project groups within a course."""

    group_set_name: str
    groups: List[GroupItemResponse] = Field(default_factory=list)


class GroupPartitionPreviewRequest(BaseModel):
    """Payload for POST /api/v1/courses/{id}/groups/partition/preview."""

    group_set_name: str = Field(..., min_length=2, max_length=100)
    mode: GroupingMode = GroupingMode.RANDOM
    group_size: int = Field(4, ge=2, le=10)


class GroupSaveItem(BaseModel):
    """Single group definition when saving a group set."""

    name: str = Field(..., min_length=1, max_length=100)
    member_ids: List[uuid.UUID] = Field(default_factory=list)


class GroupSetSaveRequest(BaseModel):
    """Payload for PUT /api/v1/courses/{id}/groups/sets/{group_set_name}."""

    groups: List[GroupSaveItem] = Field(..., min_length=1)
