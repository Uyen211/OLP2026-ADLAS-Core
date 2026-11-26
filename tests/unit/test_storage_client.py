# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""
Unit tests verifying Dual-Mode ObjectStorageClient (Supabase Storage & S3 SigV4),
persistent JWT revocation (identity.revoked_tokens), and persistent IP whitelist.
"""

import os
import uuid
from unittest.mock import AsyncMock, MagicMock
import httpx
import pytest
from app.core.security import (
    _token_blacklist,
    create_access_token,
    hash_token,
    is_token_revoked_persistent,
    revoke_token_persistent,
)
from app.core.storage_client import ObjectStorageClient, _aws_sigv4_headers
from app.modules.system.gateway_schemas import AddIpWhitelistRequest
from app.modules.system.gateway_service import GatewayAdminService
from app.modules.system.models import GatewayIpWhitelist, RevokedToken, User


def test_aws_sigv4_headers_format():
    headers = _aws_sigv4_headers(
        method="PUT",
        url="http://minio:8000/adlas-voice-feedback/test.webm",
        payload=b"audio-bytes",
        access_key="minio_admin",
        secret_key="minio_secure_password",
        content_type="audio/webm",
    )
    assert headers["Authorization"].startswith("AWS4-HMAC-SHA256 Credential=minio_admin/")
    assert "SignedHeaders=content-type;host;x-amz-content-sha256;x-amz-date" in headers["Authorization"]
    assert headers["Content-Type"] == "audio/webm"
    assert len(headers["x-amz-content-sha256"]) == 64


@pytest.mark.asyncio
async def test_storage_client_supabase_upload_download_delete(monkeypatch, tmp_path):
    """Verify full save -> retrieve -> delete round-trip against Supabase Storage REST API."""
    remote_store = {}

    async def mock_post(self, url, headers=None, content=None, json=None):
        resp = MagicMock()
        if "/storage/v1/bucket" in url:
            resp.status_code = 200
            return resp
        assert headers["Authorization"] == "Bearer test-service-key"
        remote_store[url] = (content, headers.get("Content-Type", "application/octet-stream"))
        resp.status_code = 200
        return resp

    async def mock_get(self, url, headers=None):
        resp = MagicMock()
        if url in remote_store:
            resp.status_code = 200
            resp.content, ctype = remote_store[url]
            resp.headers = {"content-type": ctype}
        else:
            resp.status_code = 404
        return resp

    async def mock_delete(self, url, headers=None):
        resp = MagicMock()
        if url in remote_store:
            remote_store.pop(url)
            resp.status_code = 200
        else:
            resp.status_code = 404
        return resp

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
    monkeypatch.setattr(httpx.AsyncClient, "delete", mock_delete)

    client = ObjectStorageClient(
        provider="supabase",
        supabase_url="https://demo.supabase.co",
        supabase_service_key="test-service-key",
        s3_endpoint="",
        local_root=str(tmp_path),
    )

    payload = b"OggS-voice-feedback-sample-data-12345"
    uri = await client.upload_bytes("adlas-voice-feedback", "grade-1/feedback.webm", payload, "audio/webm")
    assert uri == "storage://adlas-voice-feedback/grade-1/feedback.webm"
    assert client.last_backend == "supabase"

    downloaded, content_type = await client.download_bytes(uri)
    assert downloaded == payload
    assert content_type == "audio/webm"
    assert client.last_backend == "supabase"

    tmp_file, should_cleanup = await client.materialize_temp_file(uri)
    assert should_cleanup is True
    assert os.path.isfile(tmp_file)
    with open(tmp_file, "rb") as f:
        assert f.read() == payload
    os.remove(tmp_file)

    deleted = await client.delete_object(uri)
    assert deleted is True


@pytest.mark.asyncio
async def test_storage_client_s3_upload_auto_creates_bucket_and_downloads(monkeypatch, tmp_path):
    """Verify S3 (Zenko/MinIO) round-trip including 404 bucket auto-creation."""
    buckets = set()
    objects = {}

    async def mock_put(self, url, headers=None, content=None):
        resp = MagicMock()
        assert "AWS4-HMAC-SHA256" in headers["Authorization"]
        path_parts = url.replace("http://minio:8000/", "").split("/", 1)
        bucket = path_parts[0]
        if len(path_parts) == 1:
            buckets.add(bucket)
            resp.status_code = 200
            return resp
        key = path_parts[1]
        if bucket not in buckets:
            resp.status_code = 404
            resp.text = "NoSuchBucket"
            return resp
        objects[(bucket, key)] = (content, headers.get("Content-Type", "application/octet-stream"))
        resp.status_code = 200
        return resp

    async def mock_get(self, url, headers=None):
        resp = MagicMock()
        path_parts = url.replace("http://minio:8000/", "").split("/", 1)
        bucket, key = path_parts[0], path_parts[1]
        if (bucket, key) in objects:
            resp.status_code = 200
            resp.content, ctype = objects[(bucket, key)]
            resp.headers = {"content-type": ctype}
        else:
            resp.status_code = 404
        return resp

    monkeypatch.setattr(httpx.AsyncClient, "put", mock_put)
    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    client = ObjectStorageClient(
        provider="s3",
        s3_endpoint="minio:8000",
        s3_access_key="minio_admin",
        s3_secret_key="minio_secure_password",
        local_root=str(tmp_path),
    )

    data = b"PK\x03\x04-zip-submission-content"
    uri = await client.upload_bytes("adlas-submissions", "stu-1/project.zip", data, "application/zip")
    assert uri == "storage://adlas-submissions/stu-1/project.zip"
    assert client.last_backend == "s3"
    assert "adlas-submissions" in buckets

    downloaded, _ = await client.download_bytes(uri)
    assert downloaded == data


@pytest.mark.asyncio
async def test_storage_client_fallback_and_path_traversal_guard(tmp_path):
    """Verify safe local fallback when offline and strict path traversal rejection."""
    client = ObjectStorageClient(
        provider="s3",
        s3_endpoint="",
        local_root=str(tmp_path),
    )

    with pytest.raises(ValueError, match="parent directory"):
        await client.upload_bytes("adlas-submissions", "../escape.txt", b"bad")

    stored_path = await client.upload_bytes("adlas-voice-feedback", "u1/note.webm", b"voice-local", "audio/webm")
    assert client.last_backend == "local_fallback"
    assert os.path.isfile(stored_path)

    content, _ = await client.download_bytes(stored_path)
    assert content == b"voice-local"

    with pytest.raises(ValueError, match="forbidden"):
        await client.download_bytes(os.path.join(str(tmp_path), "..", "outside.txt"))


@pytest.mark.asyncio
async def test_persistent_revoked_token_survives_l1_cache_clear():
    """Verify JWT revocation persists via identity.revoked_tokens even after RAM cache is cleared."""
    token = create_access_token(subject=str(uuid.uuid4()), claims={"type": "access"})
    digest = hash_token(token)
    saved_rows = {}

    db = AsyncMock()
    db.add = MagicMock(side_effect=lambda obj: saved_rows.__setitem__(obj.token_hash, obj))
    db.flush = AsyncMock()

    async def mock_execute(stmt):
        res = MagicMock()
        res.scalar_one_or_none.return_value = saved_rows.get(digest)
        return res

    db.execute = AsyncMock(side_effect=mock_execute)

    await revoke_token_persistent(db, token, user_id=uuid.uuid4())
    assert digest in saved_rows
    assert isinstance(saved_rows[digest], RevokedToken)

    # Simulate container restart by clearing L1 RAM cache
    _token_blacklist.discard(token)
    assert await is_token_revoked_persistent(db, token) is True


@pytest.mark.asyncio
async def test_gateway_ip_whitelist_persists_to_database_rows():
    """Verify GatewayAdminService writes and reads GatewayIpWhitelist ORM rows from DB."""
    stored_rows = {}
    db = AsyncMock()

    def mock_add(obj):
        if isinstance(obj, GatewayIpWhitelist):
            stored_rows[obj.id] = obj

    db.add = MagicMock(side_effect=mock_add)
    db.commit = AsyncMock()
    db.delete = AsyncMock(side_effect=lambda obj: stored_rows.pop(obj.id, None))

    async def mock_execute(stmt):
        res = MagicMock()
        scalars = MagicMock()
        scalars.all.return_value = list(stored_rows.values())
        res.scalars.return_value = scalars
        res.scalar_one_or_none.return_value = next(iter(stored_rows.values()), None)
        return res

    db.execute = AsyncMock(side_effect=mock_execute)

    admin = User(
        id=uuid.uuid4(),
        email="admin@adlas.edu.vn",
        user_code="ADM01",
        full_name="Admin",
        password_hash="x",
        system_role="ADMIN",
        is_active=True,
    )
    service = GatewayAdminService(db)
    GatewayAdminService._ip_whitelist.clear()

    entry = await service.add_ip_whitelist(
        AddIpWhitelistRequest(cidr="10.20.30.0/24", description="Phong thi B1-201"),
        admin,
    )
    assert entry.id in stored_rows

    # Simulate container restart by clearing L1 cache -> must still load from DB
    GatewayAdminService._ip_whitelist.clear()
    listed = await service.list_ip_whitelist()
    assert len(listed) == 1
    assert listed[0].cidr == "10.20.30.0/24"

    await service.delete_ip_whitelist(entry.id, admin)
    assert entry.id not in stored_rows
