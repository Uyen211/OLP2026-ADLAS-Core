# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

import uuid
from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class DatabaseSchemaStats(BaseModel):
    schema_name: str
    description: str
    table_count: int
    record_count: int
    size_mb: float
    status: Literal["HEALTHY", "OPTIMAL", "ATTENTION"] = "HEALTHY"


class VectorIndexStatus(BaseModel):
    table_name: str
    index_name: str
    algorithm: str = "HNSW"
    m_parameter: int = 16
    ef_construction: int = 64
    indexed_vectors_count: int
    avg_query_time_ms: float
    last_reindexed_at: Optional[datetime] = None


class StorageBucketStats(BaseModel):
    bucket_name: str
    description: str
    object_count: int
    size_mb: float
    max_quota_mb: float
    usage_pct: float
    status: Literal["NORMAL", "WARNING", "FULL"] = "NORMAL"


class OrphanedFileItem(BaseModel):
    file_id: str
    bucket_name: str
    file_path: str
    size_bytes: int
    uploaded_at: datetime
    age_hours: float


class OrphanedFilesScanResponse(BaseModel):
    total_orphaned_files: int
    total_size_mb: float
    items: List[OrphanedFileItem]
    scanned_at: datetime = Field(default_factory=datetime.utcnow)


class OrphanedCleanupResponse(BaseModel):
    cleaned_count: int
    freed_mb: float
    message: str
    completed_at: datetime = Field(default_factory=datetime.utcnow)


class GlobalQuotaConfig(BaseModel):
    max_slide_mb: int = Field(50, ge=5, le=100, description="Max slide file size in MB")
    max_video_mb: int = Field(500, ge=50, le=1000, description="Max video file size in MB")
    max_submission_mb: int = Field(25, ge=5, le=50, description="Max submission file size in MB")
    max_course_storage_gb: int = Field(10, ge=1, le=50, description="Max course storage limit in GB")
    warning_threshold_pct: int = Field(85, ge=50, le=95, description="Warning threshold percentage")
    updated_at: Optional[datetime] = None


class GlobalQuotaUpdateRequest(BaseModel):
    max_slide_mb: int = Field(..., description="Max slide file size in MB (5 - 100)")
    max_video_mb: int = Field(..., description="Max video file size in MB (50 - 1000)")
    max_submission_mb: int = Field(..., description="Max submission file size in MB (5 - 50)")
    max_course_storage_gb: int = Field(..., description="Max course storage limit in GB (1 - 50)")
    warning_threshold_pct: int = Field(85, description="Warning threshold percentage (50 - 95)")


class BackupTriggerResponse(BaseModel):
    backup_id: uuid.UUID
    backup_name: str
    file_size_bytes: int
    storage_path: str
    status: str
    created_at: datetime
    created_by: str


class BackupHistoryItem(BaseModel):
    id: uuid.UUID
    backup_name: str
    file_size_bytes: int
    storage_path: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    status: str
