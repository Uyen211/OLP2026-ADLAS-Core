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
