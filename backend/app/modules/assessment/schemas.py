# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Pydantic DTO schemas for Assignment, Submission and Viva Sandbox."""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator


class AIDisclosureSchema(BaseModel):
    """Schema for AI usage declaration."""

    self_contribution_pct: int = Field(..., ge=0, le=100, description="Percentage of student own contribution (0-100)")
    tools_used: List[str] = Field(default_factory=list, description="List of AI tools used (e.g. ChatGPT, Claude, Copilot)")
    usage_description: str = Field(..., min_length=20, max_length=1000, description="Detailed explanation of AI assistance and prompts")

    @field_validator("usage_description")
    @classmethod
    def validate_description_length(cls, v: str) -> str:
        trimmed = v.strip()
        if len(trimmed) < 20:
            raise ValueError("AI usage description must contain at least 20 characters.")
        return trimmed


class SubmissionCreateRequest(BaseModel):
    """Payload for submitting an assignment (v1 or subsequent version)."""

    project_title: Optional[str] = Field(None, max_length=255, description="Specific project or topic title")
    file_url: Optional[str] = Field(None, max_length=500)
    file_name: Optional[str] = Field(None, max_length=255)
    git_repo_url: Optional[str] = Field(None, max_length=500)
    comments: Optional[str] = None
    ai_disclosure: AIDisclosureSchema
    is_pledge_signed: bool = Field(True, description="Student academic integrity pledge")

    @field_validator("git_repo_url")
    @classmethod
    def validate_git_url(cls, v: Optional[str]) -> Optional[str]:
        if v:
            trimmed = v.strip()
            if not (trimmed.startswith("https://") or trimmed.startswith("http://") or trimmed.startswith("git@")):
                raise ValueError("Invalid Git repository URL format.")
            return trimmed
        return v


class SubmissionResponse(BaseModel):
    """Response model for a submission."""

    id: uuid.UUID
    assignment_id: uuid.UUID
    user_id: uuid.UUID
    version: int
    project_title: Optional[str] = None
    file_url: Optional[str] = None
    git_repo_url: Optional[str] = None
    comments: Optional[str] = None
    ai_disclosure_data: Dict[str, Any]
    self_contribution_pct: int
    is_pledge_signed: bool
    submitted_at: datetime
    is_late: bool
    late_penalty_applied: float
    status: str

    model_config = ConfigDict(from_attributes=True)


class AssignmentDetailResponse(BaseModel):
    """Response model for assignment details and submission history."""

    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    instructions: str
    attachment_url: Optional[str] = None
    submission_type: str
    allowed_extensions: str
    max_file_size_mb: int
    due_date: datetime
    until_date: Optional[datetime] = None
    late_penalty_percent: float
    is_viva_required: bool
    viva_question_count: int
    submissions: List[SubmissionResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class VivaQuestionSchema(BaseModel):
    """Schema for an individual Viva defense question."""

    id: str
    question_index: int
    total_questions: int
    question_text: str
    category: str = "COMPETENCY_VERIFICATION"


class VivaStartResponse(BaseModel):
    """Initial payload when entering Viva Sandbox room."""

    session_id: uuid.UUID
    submission_id: uuid.UUID
    total_questions: int
    total_duration_seconds: int
    current_question_index: int
    question: VivaQuestionSchema
    status: str
    violation_logs: List[Dict[str, Any]] = Field(default_factory=list)


class VivaAnswerSubmitRequest(BaseModel):
    """Student submission of an answer to a specific Viva question."""

    question_id: str
    answer_text: str = Field(..., min_length=1, description="Direct typed answer")
    time_spent_seconds: Optional[int] = Field(None, ge=0)


class VivaAnswerSubmitResponse(BaseModel):
    """Response returned upon submitting a Viva answer."""

    session_id: uuid.UUID
    is_completed: bool
    next_question: Optional[VivaQuestionSchema] = None
    status: str
    message: str


class VivaSecurityViolationRequest(BaseModel):
    """Payload to record security violation during Viva exam."""

    violation_type: str = Field(..., description="'PASTE_ATTEMPT' or 'WINDOW_BLUR'")
    details: Optional[Dict[str, Any]] = None


class PresignedUploadUrlRequest(BaseModel):
    """Request presigned URL for direct S3 / MinIO upload."""

    file_name: str
    content_type: str
    file_size_bytes: int
