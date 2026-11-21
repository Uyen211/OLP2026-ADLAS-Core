# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from app.modules.system.models import User
from app.modules.system.storage_schemas import GlobalQuotaUpdateRequest
from app.modules.system.storage_service import StorageAdminService


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()

    # Mock execute result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result

    return session


@pytest.fixture
def mock_admin_user():
    return User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        email="admin@adlas.edu.vn",
        user_code="SYSADMIN",
        full_name="Platform System Administrator",
        password_hash="system_managed",
        system_role="ADMIN",
        is_active=True,
    )


@pytest.mark.asyncio
async def test_get_database_schema_stats(mock_db_session):
    service = StorageAdminService(mock_db_session)
    schemas = await service.get_database_schemas()

    assert len(schemas) >= 7
    schema_names = {s.schema_name for s in schemas}
    expected_names = {"identity", "course", "learning", "assessment", "examination", "gradebook", "analytics"}
    assert expected_names.issubset(schema_names)

    for s in schemas:
        assert s.size_mb > 0
        assert s.table_count >= 1
        assert s.status in ["HEALTHY", "OPTIMAL", "ATTENTION"]


@pytest.mark.asyncio
async def test_vector_index_status_and_reindex_hnsw(mock_db_session, mock_admin_user):
    service = StorageAdminService(mock_db_session)

    # 1. Inspect status (BR-SYS-06)
    status_info = await service.get_vector_index_status()
    assert status_info.algorithm == "HNSW"
    assert status_info.m_parameter == 16
    assert status_info.ef_construction == 64
    assert status_info.avg_query_time_ms < 15.0

    # 2. Trigger Re-index
    updated_status = await service.reindex_vector_index(mock_admin_user)
    assert updated_status.last_reindexed_at is not None
    assert mock_db_session.add.called
    assert mock_db_session.commit.called


@pytest.mark.asyncio
async def test_storage_buckets_stats(mock_db_session):
    service = StorageAdminService(mock_db_session)
    buckets = await service.get_storage_buckets()

    assert len(buckets) == 3
    bucket_names = {b.bucket_name for b in buckets}
    assert bucket_names == {"course-materials", "student-submissions", "viva-recordings"}

    for b in buckets:
        assert b.object_count > 0
        assert 0 <= b.usage_pct <= 100
        assert b.status in ["NORMAL", "WARNING", "FULL"]


@pytest.mark.asyncio
async def test_orphaned_files_scan_and_cleanup_lifecycle(mock_db_session, mock_admin_user):
    service = StorageAdminService(mock_db_session)

    # 1. Scan orphaned files (BR-SYS-07: older than 24 hours)
    scan_result = await service.scan_orphaned_files()
    assert scan_result.total_orphaned_files >= 1
    assert scan_result.total_size_mb > 0
    for item in scan_result.items:
        assert item.age_hours >= 24.0

    # 2. Cleanup orphaned files (BR-STORAGE-01)
    cleanup_result = await service.cleanup_orphaned_files(mock_admin_user)
    assert cleanup_result.cleaned_count == scan_result.total_orphaned_files
    assert cleanup_result.freed_mb == scan_result.total_size_mb
    assert mock_db_session.add.called
    assert mock_db_session.commit.called

    # 3. Subsequent scan should be empty
    subsequent_scan = await service.scan_orphaned_files()
    assert subsequent_scan.total_orphaned_files == 0


@pytest.mark.asyncio
async def test_global_quotas_get_and_update_valid(mock_db_session, mock_admin_user):
    service = StorageAdminService(mock_db_session)

    # 1. Get default
    quotas = await service.get_global_quotas()
    assert quotas.max_slide_mb == 50
    assert quotas.max_video_mb == 500
    assert quotas.max_submission_mb == 25
    assert quotas.max_course_storage_gb == 10

    # 2. Update valid quotas (AC-01)
    update_payload = GlobalQuotaUpdateRequest(
        max_slide_mb=60,
        max_video_mb=600,
        max_submission_mb=30,
        max_course_storage_gb=15,
        warning_threshold_pct=80,
    )
    updated = await service.update_global_quotas(update_payload, mock_admin_user)
    assert updated.max_slide_mb == 60
    assert updated.max_video_mb == 600
    assert updated.max_submission_mb == 30
    assert updated.max_course_storage_gb == 15
    assert updated.warning_threshold_pct == 80
    assert mock_db_session.add.called
    assert mock_db_session.commit.called


@pytest.mark.asyncio
async def test_global_quotas_validation_rejections_ac02(mock_db_session, mock_admin_user):
    service = StorageAdminService(mock_db_session)

    # Slide size < 5 MB (Rule AC-02)
    invalid_slide = GlobalQuotaUpdateRequest(
        max_slide_mb=2,
        max_video_mb=500,
        max_submission_mb=25,
        max_course_storage_gb=10,
        warning_threshold_pct=85,
    )
    with pytest.raises(HTTPException) as exc_info:
        await service.update_global_quotas(invalid_slide, mock_admin_user)
    assert exc_info.value.status_code == 422
    assert "AC-02" in exc_info.value.detail

    # Submission size > 50 MB
    invalid_submission = GlobalQuotaUpdateRequest(
        max_slide_mb=50,
        max_video_mb=500,
        max_submission_mb=70,
        max_course_storage_gb=10,
        warning_threshold_pct=85,
    )
    with pytest.raises(HTTPException) as exc_info:
        await service.update_global_quotas(invalid_submission, mock_admin_user)
    assert exc_info.value.status_code == 422
    assert "AC-01" in exc_info.value.detail


@pytest.mark.asyncio
async def test_manual_backup_trigger_and_history(mock_db_session, mock_admin_user):
    service = StorageAdminService(mock_db_session)

    # 1. Trigger backup (Subflow A-1 / AC-03)
    backup_res = await service.trigger_manual_backup(mock_admin_user)
    assert backup_res.status == "COMPLETED"
    assert backup_res.backup_name.startswith("adlas_core_snapshot_")
    assert backup_res.file_size_bytes > 0
    assert mock_db_session.add.called
    assert mock_db_session.commit.called

    # 2. Get history
    history = await service.get_backup_history()
    assert isinstance(history, list)
