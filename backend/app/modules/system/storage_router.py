# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

from typing import List
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.system.models import User
from app.modules.system.router import get_current_admin
from app.modules.system.storage_schemas import (
    BackupHistoryItem,
    BackupTriggerResponse,
    DatabaseSchemaStats,
    GlobalQuotaConfig,
    GlobalQuotaUpdateRequest,
    OrphanedCleanupResponse,
    OrphanedFilesScanResponse,
    StorageBucketStats,
    VectorIndexStatus,
)
from app.modules.system.storage_service import StorageAdminService

router = APIRouter(prefix="/api/v1/system", tags=["Platform Admin - Database & Storage"])


@router.get("/database/schemas", response_model=List[DatabaseSchemaStats])
async def get_database_schemas(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Retrieve storage stats and record counts across all 7 business schemas."""
    service = StorageAdminService(db)
    return await service.get_database_schemas()


@router.get("/database/vector-index", response_model=VectorIndexStatus)
async def get_vector_index_status(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Inspect knowledge base vector HNSW index performance (BR-SYS-06)."""
    service = StorageAdminService(db)
    return await service.get_vector_index_status()


@router.post("/database/reindex", response_model=VectorIndexStatus)
async def reindex_vector_index(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Rebuild and optimize pgvector HNSW index tree (BR-SYS-06)."""
    service = StorageAdminService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    return await service.reindex_vector_index(
        actor=admin,
        ip_address=client_ip,
        user_agent=user_agent,
    )


@router.get("/storage/buckets", response_model=List[StorageBucketStats])
async def get_storage_buckets(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Query S3 object storage bucket capacities and current usage."""
    service = StorageAdminService(db)
    return await service.get_storage_buckets()


@router.get("/storage/orphaned-files", response_model=OrphanedFilesScanResponse)
async def scan_orphaned_files(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Scan for unreferenced S3 files older than 24 hours (BR-SYS-07)."""
    service = StorageAdminService(db)
    return await service.scan_orphaned_files()


@router.post("/storage/cleanup-orphaned", response_model=OrphanedCleanupResponse)
async def cleanup_orphaned_files(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Purge unreferenced temporary files without touching active student work (BR-STORAGE-01)."""
    service = StorageAdminService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    return await service.cleanup_orphaned_files(
        actor=admin,
        ip_address=client_ip,
        user_agent=user_agent,
    )


@router.get("/storage/quotas", response_model=GlobalQuotaConfig)
async def get_global_quotas(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Get global upload size limits and course storage quotas."""
    service = StorageAdminService(db)
    return await service.get_global_quotas()


@router.put("/storage/quotas", response_model=GlobalQuotaConfig)
async def update_global_quotas(
    payload: GlobalQuotaUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Update global upload size limits (Rule AC-01, AC-02, BR-STORAGE-02)."""
    service = StorageAdminService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    return await service.update_global_quotas(
        payload=payload,
        actor=admin,
        ip_address=client_ip,
        user_agent=user_agent,
    )


@router.post("/database/backup", response_model=BackupTriggerResponse, status_code=status.HTTP_201_CREATED)
async def trigger_manual_backup(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Trigger manual full snapshot backup of all academic schemas (Subflow A-1 / AC-03)."""
    service = StorageAdminService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    return await service.trigger_manual_backup(
        actor=admin,
        ip_address=client_ip,
        user_agent=user_agent,
    )


@router.get("/database/backups", response_model=List[BackupHistoryItem])
async def get_backup_history(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Retrieve chronological list of academic database snapshots."""
    service = StorageAdminService(db)
    return await service.get_backup_history()
