# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

import uuid
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class GatewayMetricsResponse(BaseModel):
    status: Literal["ONLINE", "DEGRADED", "OFFLINE"] = "ONLINE"
    total_rps: float = Field(..., ge=0, description="Requests per second")
    average_latency_ms: float = Field(..., ge=0, description="Average response latency in ms")
    success_rate_pct: float = Field(..., ge=0, le=100, description="Successful requests percentage")
    p95_latency_ms: float = Field(..., ge=0, description="95th percentile latency")
    p99_latency_ms: float = Field(..., ge=0, description="99th percentile latency")
    active_connections: int = Field(..., ge=0, description="Current open connections")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ServiceModuleHealth(BaseModel):
    module_id: str
    name: str
    route_prefix: str
    status: Literal["HEALTHY", "HIGH_LOAD", "UNREACHABLE"]
    req_per_min: int
    error_rate_pct: float
    latency_ms: float
    last_restart: Optional[datetime] = None


class RateLimitConfig(BaseModel):
    standard_rpm: int = Field(120, ge=10, le=10000, description="Rate limit for regular students/teachers")
    exam_rpm: int = Field(300, ge=300, le=10000, description="Rate limit for exam room autosave (BR-GATEWAY-01)")
    ip_block_duration_minutes: int = Field(5, description="IP block duration: 1, 5, or 15 minutes")
    exam_mode_enabled: bool = Field(False, description="Whether strict exam prioritization is active")
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RateLimitUpdateRequest(BaseModel):
    standard_rpm: int = Field(..., description="Regular rate limit in requests per minute")
    exam_rpm: int = Field(..., description="Exam room rate limit in requests per minute")
    ip_block_duration_minutes: int = Field(..., description="Temporary block duration")
    exam_mode_enabled: Optional[bool] = False


class IpWhitelistEntry(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    cidr: str = Field(..., description="IPv4 or IPv6 CIDR block")
    description: str = Field(..., max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    is_active: bool = True


class AddIpWhitelistRequest(BaseModel):
    cidr: str = Field(..., description="CIDR network block, e.g. 192.168.10.0/24")
    description: str = Field(..., min_length=3, max_length=255)


class ModuleRestartResponse(BaseModel):
    module_id: str
    status: str
    message: str
    restarted_at: datetime
