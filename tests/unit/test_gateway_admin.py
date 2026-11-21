# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from app.modules.system.gateway_schemas import (
    AddIpWhitelistRequest,
    RateLimitUpdateRequest,
)
from app.modules.system.gateway_service import GatewayAdminService
from app.modules.system.models import User


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
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
async def test_gateway_metrics_schema_and_status(mock_db_session):
    service = GatewayAdminService(mock_db_session)
    metrics = await service.get_metrics()

    assert metrics.status == "ONLINE"
    assert metrics.total_rps > 0
    assert metrics.average_latency_ms > 0
    assert 0 <= metrics.success_rate_pct <= 100
    assert metrics.p95_latency_ms >= metrics.average_latency_ms


@pytest.mark.asyncio
async def test_modules_health_probes(mock_db_session):
    service = GatewayAdminService(mock_db_session)
    modules = await service.get_modules_health()

    assert len(modules) >= 5
    module_ids = {m.module_id for m in modules}
    expected_ids = {"course", "learning", "assessment", "gradebook", "ai"}
    assert expected_ids.issubset(module_ids)

    for m in modules:
        assert m.status in ["HEALTHY", "HIGH_LOAD", "UNREACHABLE"]
        assert m.latency_ms > 0


@pytest.mark.asyncio
async def test_module_restart_action(mock_db_session, mock_admin_user):
    service = GatewayAdminService(mock_db_session)
    result = await service.restart_module("assessment", mock_admin_user)

    assert result.module_id == "assessment"
    assert result.status == "HEALTHY"
    assert result.restarted_at is not None
    assert mock_db_session.add.called
    assert mock_db_session.commit.called


@pytest.mark.asyncio
async def test_rate_limit_validation_out_of_range_e_gateway_02(mock_db_session, mock_admin_user):
    service = GatewayAdminService(mock_db_session)

    # Standard RPM too low (< 10)
    low_payload = RateLimitUpdateRequest(
        standard_rpm=5,
        exam_rpm=300,
        ip_block_duration_minutes=5,
    )
    with pytest.raises(HTTPException) as exc_info:
        await service.update_rate_limits(low_payload, mock_admin_user)
    assert exc_info.value.status_code == 422
    assert "E-GATEWAY-02" in exc_info.value.detail

    # Standard RPM too high (> 10000)
    high_payload = RateLimitUpdateRequest(
        standard_rpm=20000,
        exam_rpm=300,
        ip_block_duration_minutes=5,
    )
    with pytest.raises(HTTPException) as exc_info:
        await service.update_rate_limits(high_payload, mock_admin_user)
    assert exc_info.value.status_code == 422
    assert "E-GATEWAY-02" in exc_info.value.detail


@pytest.mark.asyncio
async def test_exam_rate_limit_protection_br_gateway_01(mock_db_session, mock_admin_user):
    service = GatewayAdminService(mock_db_session)

    # Exam RPM must be at least 300 (BR-GATEWAY-01)
    payload = RateLimitUpdateRequest(
        standard_rpm=100,
        exam_rpm=250,  # Below 300
        ip_block_duration_minutes=5,
    )
    with pytest.raises(HTTPException) as exc_info:
        await service.update_rate_limits(payload, mock_admin_user)
    assert exc_info.value.status_code == 422
    assert "BR-GATEWAY-01" in exc_info.value.detail


@pytest.mark.asyncio
async def test_ip_whitelist_cidr_validation_e_sys_02(mock_db_session, mock_admin_user):
    service = GatewayAdminService(mock_db_session)

    invalid_payload = AddIpWhitelistRequest(
        cidr="999.999.999.999/24",
        description="Exam Room Lab 1",
    )
    with pytest.raises(HTTPException) as exc_info:
        await service.add_ip_whitelist(invalid_payload, mock_admin_user)
    assert exc_info.value.status_code == 400
    assert "E-SYS-02" in exc_info.value.detail


@pytest.mark.asyncio
async def test_ip_whitelist_add_and_delete_lifecycle(mock_db_session, mock_admin_user):
    service = GatewayAdminService(mock_db_session)

    # 1. Add valid CIDR
    add_payload = AddIpWhitelistRequest(
        cidr="192.168.10.0/24",
        description="Main Lab Exam Hall",
    )
    entry = await service.add_ip_whitelist(add_payload, mock_admin_user)
    assert entry.cidr == "192.168.10.0/24"
    assert entry.created_by == mock_admin_user.email
    assert entry.is_active is True

    # 2. Verify in list
    whitelist = await service.list_ip_whitelist()
    assert any(e.id == entry.id for e in whitelist)

    # 3. Delete entry
    await service.delete_ip_whitelist(entry.id, mock_admin_user)
    whitelist_after = await service.list_ip_whitelist()
    assert not any(e.id == entry.id for e in whitelist_after)
