# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

import uuid
from typing import List
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.system.gateway_schemas import (
    AddIpWhitelistRequest,
    GatewayMetricsResponse,
    IpWhitelistEntry,
    ModuleRestartResponse,
    RateLimitConfig,
    RateLimitUpdateRequest,
    ServiceModuleHealth,
)
from app.modules.system.gateway_service import GatewayAdminService
from app.modules.system.models import User
from app.modules.system.router import get_current_admin

router = APIRouter(prefix="/api/v1/system/gateway", tags=["Platform Admin - Gateway & Traffic"])


@router.get("/metrics", response_model=GatewayMetricsResponse)
async def get_gateway_metrics(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Get real-time gateway performance metrics and latency telemetry."""
    service = GatewayAdminService(db)
    return await service.get_metrics()


@router.get("/health", response_model=List[ServiceModuleHealth])
async def get_modules_health(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Probe health status and load across all 5 modular business subsystems."""
    service = GatewayAdminService(db)
    return await service.get_modules_health()


@router.post("/modules/{module_id}/restart", response_model=ModuleRestartResponse)
async def restart_service_module(
    module_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Trigger emergency restart for a degrading or stalled module (AC-03)."""
    service = GatewayAdminService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    return await service.restart_module(
        module_id=module_id,
        actor=admin,
        ip_address=client_ip,
        user_agent=user_agent,
    )


@router.get("/rate-limits", response_model=RateLimitConfig)
async def get_rate_limits(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Retrieve current dynamic edge rate limiting policies."""
    service = GatewayAdminService(db)
    return await service.get_rate_limits()


@router.put("/rate-limits", response_model=RateLimitConfig)
async def update_rate_limits(
    payload: RateLimitUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Update dynamic rate limits. Enforces Rule E-GATEWAY-02 and BR-GATEWAY-01."""
    service = GatewayAdminService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    return await service.update_rate_limits(
        payload=payload,
        actor=admin,
        ip_address=client_ip,
        user_agent=user_agent,
    )


@router.get("/ip-whitelist", response_model=List[IpWhitelistEntry])
async def list_ip_whitelist(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """List registered exam room CIDR network blocks."""
    service = GatewayAdminService(db)
    return await service.list_ip_whitelist()


@router.post("/ip-whitelist", response_model=IpWhitelistEntry, status_code=status.HTTP_201_CREATED)
async def add_ip_whitelist(
    payload: AddIpWhitelistRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Add an authorized CIDR block for exam room isolation (BR-SYS-04, E-SYS-02)."""
    service = GatewayAdminService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    return await service.add_ip_whitelist(
        payload=payload,
        actor=admin,
        ip_address=client_ip,
        user_agent=user_agent,
    )


@router.delete("/ip-whitelist/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ip_whitelist(
    entry_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Remove a CIDR block from the exam room whitelist."""
    service = GatewayAdminService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    await service.delete_ip_whitelist(
        entry_id=entry_id,
        actor=admin,
        ip_address=client_ip,
        user_agent=user_agent,
    )
