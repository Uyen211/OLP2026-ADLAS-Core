# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class OutboxEventItem(BaseModel):
    id: uuid.UUID
    event_type: str
    aggregate_type: str
    aggregate_id: uuid.UUID
    payload: Dict[str, Any]
    status: Literal["PENDING", "PROCESSING", "PROCESSED", "FAILED"]
    retry_count: int
    created_at: datetime
    processed_at: Optional[datetime] = None


class ActiveBackgroundTask(BaseModel):
    task_id: str
    name: str
    category: Literal["AI_EXTRACTION", "RUBRIC_CALCULATION", "PLAGIARISM_SCAN", "REPORT_GEN"]
    progress_pct: int = Field(..., ge=0, le=100)
    started_at: datetime
    eta_seconds: int
    status: Literal["RUNNING", "COMPLETED", "FAILED"] = "RUNNING"


class DeadLetterItem(BaseModel):
    id: uuid.UUID
    outbox_event_id: Optional[uuid.UUID] = None
    event_type: str
    payload: Dict[str, Any]
    error_message: str
    stack_trace: Optional[str] = None
    retry_attempts: int
    status: Literal["DEAD_LETTER", "RETRYING", "RESOLVED"]
    created_at: datetime
    resolved_at: Optional[datetime] = None


class DlqRetryResponse(BaseModel):
    dlq_id: uuid.UUID
    status: str
    message: str
    resolved_at: datetime


class CoreInfrastructureHealth(BaseModel):
    component_id: str
    name: str
    endpoint: str
    status: Literal["HEALTHY", "DEGRADED", "UNHEALTHY"]
    latency_ms: float
    details: Dict[str, Any]
    last_heartbeat: datetime


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    actor_id: Optional[uuid.UUID] = None
    actor_email: Optional[str] = None
    action: str
    module: str
    severity: Literal["INFO", "WARNING", "CRITICAL"]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Dict[str, Any]
    created_at: datetime


class PaginatedAuditLogsResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
