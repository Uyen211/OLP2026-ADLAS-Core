# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.system.models import User
from app.modules.system.router import get_current_admin
from app.modules.system.workflow_schemas import (
    ActiveBackgroundTask,
    CoreInfrastructureHealth,
    DeadLetterItem,
    DlqRetryResponse,
    OutboxEventItem,
    PaginatedAuditLogsResponse,
)
from app.modules.system.workflow_service import WorkflowAdminService

router = APIRouter(prefix="/api/v1/system", tags=["Platform Admin - Event Bus, Tasks & Audit Trail"])


@router.get("/events/outbox", response_model=List[OutboxEventItem])
async def get_outbox_events(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Fetch latest transactional outbox events (Rule BR-SYS-08)."""
    service = WorkflowAdminService(db)
    return await service.get_outbox_events(limit=limit)


@router.get("/tasks/active", response_model=List[ActiveBackgroundTask])
async def get_active_tasks(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Fetch currently running asynchronous background workers and progress."""
    service = WorkflowAdminService(db)
    return await service.get_active_tasks()


@router.get("/tasks/dlq", response_model=List[DeadLetterItem])
async def get_dlq_events(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Retrieve dead-letter queue items isolated after 3 retry failures (BR-SYS-09)."""
    service = WorkflowAdminService(db)
    return await service.get_dlq_events()


@router.post("/tasks/dlq/{dlq_id}/retry", response_model=DlqRetryResponse)
async def retry_dlq_event(
    dlq_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Re-dispatch a failed event from DLQ back into the Event Bus pipeline."""
    service = WorkflowAdminService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    return await service.retry_dlq_event(
        dlq_id=dlq_id,
        actor=admin,
        ip_address=client_ip,
        user_agent=user_agent,
    )


@router.post("/tasks/dlq/{dlq_id}/discard", status_code=status.HTTP_204_NO_CONTENT)
async def discard_dlq_event(
    dlq_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Acknowledge and permanently discard an unrecoverable dead letter event."""
    service = WorkflowAdminService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    await service.discard_dlq_event(
        dlq_id=dlq_id,
        actor=admin,
        ip_address=client_ip,
        user_agent=user_agent,
    )


@router.get("/infrastructure/health", response_model=List[CoreInfrastructureHealth])
async def get_core_infrastructure_health(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Probe health status and latency of the 6 core Layer-1 platform services (BR-SYS-10)."""
    service = WorkflowAdminService(db)
    return await service.get_core_infrastructure_health()


@router.get("/audit-logs", response_model=PaginatedAuditLogsResponse)
async def get_audit_logs(
    module: Optional[str] = Query(None, description="Filter by subsystem module"),
    action: Optional[str] = Query(None, description="Filter by action name"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Query immutable audit trail with filtering and pagination (BR-SYS-11)."""
    service = WorkflowAdminService(db)
    return await service.get_audit_logs(
        module=module,
        action=action,
        severity=severity,
        page=page,
        page_size=page_size,
    )
