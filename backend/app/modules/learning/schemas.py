# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Pydantic v2 schemas for Learning Modules and Materials REST API contracts."""

from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.modules.learning.enums import MaterialType


# -----------------------------------------------------------------------------
# Module Schemas
# -----------------------------------------------------------------------------
class ModuleCreate(BaseModel):
    """Payload to create a new module in a course."""

    title: str = Field(..., min_length=1, max_length=200, description="Tiêu đề chương/bài học")
    order_index: Optional[int] = Field(None, ge=1, description="Thứ tự hiển thị bài học")
    unlock_at: Optional[datetime] = Field(None, description="Thời điểm mở khóa tự động")
    prerequisite_module_id: Optional[uuid.UUID] = Field(None, description="ID bài học tiên quyết")
    is_published: bool = Field(False, description="Trạng thái phát hành")


class ModuleUpdate(BaseModel):
    """Payload to update an existing module."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    order_index: Optional[int] = Field(None, ge=1)
    unlock_at: Optional[datetime] = None
    prerequisite_module_id: Optional[uuid.UUID] = None
    is_published: Optional[bool] = None


class ModuleReorderRequest(BaseModel):
    """Payload to reorder modules in a course."""

    module_ids: List[uuid.UUID] = Field(..., min_length=1, description="Danh sách ID module theo thứ tự mới")


class PublishToggleRequest(BaseModel):
    """Payload to toggle publish status."""

    is_published: bool = Field(..., description="Trạng thái xuất bản")


# -----------------------------------------------------------------------------
# Learning Material Schemas
# -----------------------------------------------------------------------------
class MaterialCreate(BaseModel):
    """Payload to create a new learning resource in a module."""

    title: str = Field(..., min_length=1, max_length=200, description="Tiêu đề học liệu")
    material_type: MaterialType = Field(..., description="Loại học liệu (SLIDE, PDF, VIDEO, DOCUMENT)")
    lo_id: Optional[uuid.UUID] = Field(None, description="Chuẩn đầu ra liên kết (BR-LO-01)")
    file_url: Optional[str] = Field(None, max_length=500, description="Đường dẫn tệp hoặc URL video")
    is_mandatory: bool = Field(True, description="Học liệu bắt buộc hay đọc thêm")
    est_duration_minutes: int = Field(30, ge=1, le=1440, description="Thời lượng học dự kiến (phút)")
    is_published: bool = Field(False, description="Trạng thái phát hành")


class MaterialUpdate(BaseModel):
    """Payload to update an existing learning material."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    material_type: Optional[MaterialType] = None
    lo_id: Optional[uuid.UUID] = None
    file_url: Optional[str] = Field(None, max_length=500)
    is_mandatory: Optional[bool] = None
    est_duration_minutes: Optional[int] = Field(None, ge=1, le=1440)
    is_published: Optional[bool] = None


class MaterialResponse(BaseModel):
    """Public representation of a learning material resource."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    module_id: uuid.UUID
    lo_id: Optional[uuid.UUID] = None
    lo_code: Optional[str] = None
    title: str
    material_type: MaterialType
    file_url: Optional[str] = None
    is_mandatory: bool
    est_duration_minutes: int
    is_published: bool
    created_at: datetime


class ModuleResponse(BaseModel):
    """Public representation of a learning module including its materials."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    order_index: int
    unlock_at: Optional[datetime] = None
    prerequisite_module_id: Optional[uuid.UUID] = None
    prerequisite_title: Optional[str] = None
    is_published: bool
    is_locked: bool = False
    lock_reason: Optional[str] = None
    created_at: datetime
    materials: List[MaterialResponse] = Field(default_factory=list)


class MaterialUploadResponse(BaseModel):
    """Response returned upon successful file upload."""

    file_url: str
    file_name: str
    size_bytes: int
    material_type: MaterialType


# -----------------------------------------------------------------------------
# Checkpoint Schemas (Task T2-P-M2-03)
# -----------------------------------------------------------------------------
class CheckpointCreate(BaseModel):
    """Payload to create a new interactive checkpoint."""

    question_text: str = Field(..., min_length=5, max_length=1000, description="Nội dung câu hỏi kiểm tra")
    question_type: str = Field("MULTIPLE_CHOICE", description="Loại câu hỏi (MULTIPLE_CHOICE)")
    stop_time_seconds: Optional[int] = Field(None, ge=0, description="Mốc giây dừng trên video")
    section_index: Optional[int] = Field(None, ge=1, description="Đề mục hoặc số trang tài liệu")
    options: dict = Field(default_factory=dict, description="Danh sách 4 phương án A, B, C, D")
    correct_option: str = Field(..., min_length=1, max_length=10, description="Đáp án đúng (A, B, C, D)")
    expected_concept: Optional[str] = Field(None, description="Khái niệm trọng tâm mong đợi")
    is_blocking: bool = Field(True, description="Bắt buộc vượt qua mới được tính hoàn thành")
    time_limit_seconds: int = Field(10, ge=5, le=120, description="Thời gian đếm ngược (giây)")
    rewind_seconds: int = Field(15, ge=0, le=120, description="Thời gian tự động lùi khi sai (giây)")
    lo_id: Optional[uuid.UUID] = Field(None, description="Chuẩn đầu ra liên kết")


class CheckpointUpdate(BaseModel):
    """Payload to update an existing checkpoint."""

    question_text: Optional[str] = Field(None, min_length=5, max_length=1000)
    stop_time_seconds: Optional[int] = Field(None, ge=0)
    section_index: Optional[int] = Field(None, ge=1)
    options: Optional[dict] = None
    correct_option: Optional[str] = Field(None, min_length=1, max_length=10)
    expected_concept: Optional[str] = None
    is_blocking: Optional[bool] = None
    time_limit_seconds: Optional[int] = Field(None, ge=5, le=120)
    rewind_seconds: Optional[int] = Field(None, ge=0, le=120)
    lo_id: Optional[uuid.UUID] = None


class CheckpointInstructorResponse(BaseModel):
    """Checkpoint response for instructor view (includes correct_option)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    material_id: uuid.UUID
    lo_id: Optional[uuid.UUID] = None
    stop_time_seconds: Optional[int] = None
    section_index: Optional[int] = None
    question_text: str
    question_type: str
    options: Optional[dict] = None
    correct_option: Optional[str] = None
    expected_concept: Optional[str] = None
    is_blocking: bool
    time_limit_seconds: int
    rewind_seconds: int
    created_at: datetime


class CheckpointStudentResponse(BaseModel):
    """Checkpoint response for student view (hides correct_option, includes pass status)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    material_id: uuid.UUID
    lo_id: Optional[uuid.UUID] = None
    stop_time_seconds: Optional[int] = None
    section_index: Optional[int] = None
    question_text: str
    question_type: str
    options: Optional[dict] = None
    expected_concept: Optional[str] = None
    is_blocking: bool
    time_limit_seconds: int
    rewind_seconds: int
    is_passed: bool = False
    created_at: datetime


class CheckpointSubmitRequest(BaseModel):
    """Payload when student submits answer to a checkpoint."""

    selected_option: str = Field(..., min_length=1, max_length=10, description="Phương án sinh viên chọn (A, B, C, D)")


class CheckpointSubmitResponse(BaseModel):
    """Response returned upon submitting an answer to a checkpoint."""

    checkpoint_id: uuid.UUID
    is_correct: bool
    is_passed: bool
    rewind_seconds: int
    message: str


class MaterialPageItem(BaseModel):
    """Single page, slide, or document section extracted for interactive studio/reader."""

    index: int = Field(..., ge=1)
    title: str
    content_lines: List[str] = Field(default_factory=list)
    image_url: Optional[str] = None


class MaterialStructuredContentResponse(BaseModel):
    """Structured paginated/sectioned representation of a PDF, Slide deck, or Document."""

    material_id: uuid.UUID
    content_kind: str  # PDF_PAGES | SLIDE_DECK | DOC_SECTIONS | UNSUPPORTED
    total_items: int
    items: List[MaterialPageItem]
