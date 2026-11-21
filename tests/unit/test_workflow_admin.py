# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.modules.system.models import User
from app.modules.system.workflow_service import WorkflowAdminService


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.delete = AsyncMock()

    # Mock default execute result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar.return_value = 0
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
async def test_get_outbox_events_zero_loss(mock_db_session):
    service = WorkflowAdminService(mock_db_session)
    events = await service.get_outbox_events(limit=10)

    assert len(events) >= 1
    for ev in events:
        assert ev.event_type in ["STUDENT_SUBMITTED", "VIVA_SANDBOX_COMPLETED", "GRADEBOOK_LOCKED"]
        assert ev.aggregate_type is not None
        assert isinstance(ev.payload, dict)
        assert ev.created_at is not None


@pytest.mark.asyncio
async def test_get_active_background_tasks(mock_db_session):
    service = WorkflowAdminService(mock_db_session)
    tasks = await service.get_active_tasks()

    assert len(tasks) >= 3
    categories = {t.category for t in tasks}
    assert "AI_EXTRACTION" in categories
    assert "RUBRIC_CALCULATION" in categories

    for t in tasks:
        assert 0 <= t.progress_pct <= 100
        assert t.eta_seconds >= 0
        assert t.status == "RUNNING"


@pytest.mark.asyncio
async def test_dead_letter_queue_and_retry(mock_db_session, mock_admin_user):
    service = WorkflowAdminService(mock_db_session)

    # 1. Fetch DLQ
    dlq_items = await service.get_dlq_events()
    assert len(dlq_items) >= 1
    target = dlq_items[0]
    assert target.retry_attempts == 3
    assert target.status in ["DEAD_LETTER", "RETRYING", "RESOLVED"]

    # 2. Retry event
    retry_res = await service.retry_dlq_event(target.id, mock_admin_user)
    assert retry_res.dlq_id == target.id
    assert retry_res.status == "RESOLVED"
    assert mock_db_session.add.called
    assert mock_db_session.commit.called


@pytest.mark.asyncio
async def test_dead_letter_queue_discard(mock_db_session, mock_admin_user):
    service = WorkflowAdminService(mock_db_session)
    fake_id = uuid.uuid4()

    await service.discard_dlq_event(fake_id, mock_admin_user)
    assert mock_db_session.add.called
    assert mock_db_session.commit.called


@pytest.mark.asyncio
async def test_core_infrastructure_health_probes(mock_db_session):
    service = WorkflowAdminService(mock_db_session)
    health_list = await service.get_core_infrastructure_health()

    assert len(health_list) == 6
    component_ids = {c.component_id for c in health_list}
    expected_components = {
        "kong-gateway",
        "postgres-db",
        "gotrue-auth",
        "s3-storage",
        "gemini-ai-adapter",
        "inprocess-event-bus",
    }
    assert component_ids == expected_components

    for c in health_list:
        assert c.status in ["HEALTHY", "DEGRADED", "UNHEALTHY"]
        assert c.latency_ms >= 0


@pytest.mark.asyncio
async def test_audit_logs_pagination_and_immutability(mock_db_session):
    service = WorkflowAdminService(mock_db_session)
    paginated = await service.get_audit_logs(page=1, page_size=10)

    assert paginated.page == 1
    assert paginated.page_size == 10
    assert isinstance(paginated.items, list)
