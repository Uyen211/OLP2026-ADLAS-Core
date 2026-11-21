# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_tier1_e2e_lifecycle_and_audit_trail():
    """
    End-to-End integration test validating the end-to-end lifecycle across
    all Layer-1 platform administrative modules:
    Identity Provisioning -> Gateway Policies -> Storage Quotas -> Backup -> DLQ -> Health -> Audit Logs
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Health Probe Verification (BR-SYS-10)
        health_res = await client.get("/api/v1/system/infrastructure/health")
        assert health_res.status_code == 200
        health_data = health_res.json()
        assert len(health_data) == 6
        assert all(h["status"] == "HEALTHY" for h in health_data)

        # 2. Gateway Telemetry & Dynamic Rate Limiting (T1-C-M0-02)
        metrics_res = await client.get("/api/v1/system/gateway/metrics")
        assert metrics_res.status_code == 200
        assert metrics_res.json()["status"] == "ONLINE"

        # Update Rate Limits enforcing BR-GATEWAY-01 and E-GATEWAY-02
        rate_res = await client.put(
            "/api/v1/system/gateway/rate-limits",
            json={
                "standard_rpm": 150,
                "exam_rpm": 400,
                "ip_block_duration_minutes": 5,
                "exam_mode_enabled": True,
            },
        )
        assert rate_res.status_code == 200
        assert rate_res.json()["exam_rpm"] == 400

        # Register Exam Room CIDR Whitelist (E-SYS-02)
        whitelist_res = await client.post(
            "/api/v1/system/gateway/ip-whitelist",
            json={
                "cidr": "192.168.100.0/24",
                "description": "Integration Test Exam Hall C4",
            },
        )
        assert whitelist_res.status_code == 201
        whitelist_id = whitelist_res.json()["id"]

        # 3. Storage Quotas & Backup Trigger (T1-C-M0-03)
        quota_res = await client.put(
            "/api/v1/system/storage/quotas",
            json={
                "max_slide_mb": 75,
                "max_video_mb": 750,
                "max_submission_mb": 35,
                "max_course_storage_gb": 20,
                "warning_threshold_pct": 85,
            },
        )
        assert quota_res.status_code == 200
        assert quota_res.json()["max_submission_mb"] == 35

        # Re-index pgvector HNSW (BR-SYS-06)
        reindex_res = await client.post("/api/v1/system/database/reindex")
        assert reindex_res.status_code == 200
        assert reindex_res.json()["algorithm"] == "HNSW"

        # Trigger Manual Snapshot Backup (AC-03)
        backup_res = await client.post("/api/v1/system/database/backup")
        assert backup_res.status_code == 201
        assert backup_res.json()["status"] == "COMPLETED"

        # 4. Event Bus, Outbox & Dead-Letter Queue (T1-C-M0-04)
        outbox_res = await client.get("/api/v1/system/events/outbox?limit=5")
        assert outbox_res.status_code == 200
        assert len(outbox_res.json()) >= 1

        active_tasks_res = await client.get("/api/v1/system/tasks/active")
        assert active_tasks_res.status_code == 200
        assert len(active_tasks_res.json()) >= 1

        # Retry DLQ Event
        fake_dlq_id = str(uuid.UUID("11111111-2222-3333-4444-555555555555"))
        dlq_res = await client.post(f"/api/v1/system/tasks/dlq/{fake_dlq_id}/retry")
        assert dlq_res.status_code == 200
        assert dlq_res.json()["status"] == "RESOLVED"

        # 5. Clean up Whitelist Entry
        del_whitelist_res = await client.delete(f"/api/v1/system/gateway/ip-whitelist/{whitelist_id}")
        assert del_whitelist_res.status_code == 204

        # 6. Immutable Audit Trail Verification (BR-SYS-11)
        audit_res = await client.get("/api/v1/system/audit-logs?page=1&page_size=20")
        assert audit_res.status_code == 200
        audit_data = audit_res.json()
        assert audit_data["total"] >= 1
        actions_recorded = {item["action"] for item in audit_data["items"]}
        expected_actions = {
            "UPDATE_RATE_LIMITS",
            "ADD_IP_WHITELIST",
            "DELETE_IP_WHITELIST",
            "UPDATE_GLOBAL_QUOTAS",
            "REINDEX_VECTOR_HNSW",
            "MANUAL_BACKUP_TRIGGER",
            "RETRY_DLQ_EVENT",
        }
        assert expected_actions.issubset(actions_recorded)
