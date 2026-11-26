# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""
Dual-Mode Object Storage Client (Supabase Storage REST API & S3-compatible Zenko/MinIO).
Uses pure stdlib AWS SigV4 signing + httpx with zero external SDK dependencies.
Frontend never accesses storage credentials or databases directly; all traffic proxies through Backend.
"""

from datetime import datetime, timezone
import hashlib
import hmac
import logging
import os
import tempfile
from typing import Dict, Optional, Tuple
from urllib.parse import quote, urlparse
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

STORAGE_URI_PREFIX = "storage://"
LOCAL_FALLBACK_ROOT = "/app/uploads"


def _sign_hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _aws_sigv4_headers(
    method: str,
    url: str,
    payload: bytes,
    access_key: str,
    secret_key: str,
    region: str = "us-east-1",
    content_type: Optional[str] = None,
) -> Dict[str, str]:
    """Compute AWS Signature Version 4 headers for S3-compatible object storage."""
    parsed = urlparse(url)
    host = parsed.netloc
    canonical_uri = quote(parsed.path or "/", safe="/-_.~")
    canonical_querystring = parsed.query or ""

    now = datetime.now(timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    payload_hash = hashlib.sha256(payload).hexdigest()

    headers_to_sign: Dict[str, str] = {
        "host": host,
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amz_date,
    }
    if content_type:
        headers_to_sign["content-type"] = content_type

    sorted_keys = sorted(headers_to_sign.keys())
    canonical_headers = "".join(f"{k}:{headers_to_sign[k].strip()}\n" for k in sorted_keys)
    signed_headers = ";".join(sorted_keys)

    canonical_request = "\n".join(
        [
            method.upper(),
            canonical_uri,
            canonical_querystring,
            canonical_headers,
            signed_headers,
            payload_hash,
        ]
    )

    credential_scope = f"{date_stamp}/{region}/s3/aws4_request"
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )

    k_date = _sign_hmac(f"AWS4{secret_key}".encode("utf-8"), date_stamp)
    k_region = _sign_hmac(k_date, region)
    k_service = _sign_hmac(k_region, "s3")
    k_signing = _sign_hmac(k_service, "aws4_request")
    signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    authorization = (
        f"AWS4-HMAC-SHA256 Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    out_headers = {
        "x-amz-date": amz_date,
        "x-amz-content-sha256": payload_hash,
        "Authorization": authorization,
    }
    if content_type:
        out_headers["Content-Type"] = content_type
    return out_headers


class ObjectStorageClient:
    """
    Unified async storage adapter supporting:
    1. Supabase Storage REST API (when STORAGE_PROVIDER='supabase' and SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY set)
    2. S3-compatible storage (Zenko CloudServer / MinIO in Docker Compose)
    3. Safe local fallback (/app/uploads) for offline unit tests and legacy file reads
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        supabase_url: Optional[str] = None,
        supabase_service_key: Optional[str] = None,
        s3_endpoint: Optional[str] = None,
        s3_access_key: Optional[str] = None,
        s3_secret_key: Optional[str] = None,
        local_root: str = LOCAL_FALLBACK_ROOT,
        timeout: float = 15.0,
    ):
        self.provider = (provider or settings.STORAGE_PROVIDER or "s3").strip().lower()
        self.supabase_url = (supabase_url or settings.SUPABASE_URL or "").rstrip("/")
        self.supabase_service_key = supabase_service_key or settings.SUPABASE_SERVICE_ROLE_KEY or ""
        raw_ep = (s3_endpoint or settings.MINIO_ENDPOINT or "minio:8000").strip().rstrip("/")
        if raw_ep and not raw_ep.startswith(("http://", "https://")):
            raw_ep = f"http://{raw_ep}"
        self.s3_endpoint = raw_ep
        self.s3_access_key = s3_access_key or settings.MINIO_ROOT_USER
        self.s3_secret_key = s3_secret_key or settings.MINIO_ROOT_PASSWORD
        self.local_root = local_root
        self.timeout = timeout
        self.last_backend: str = "none"

    def _use_supabase(self) -> bool:
        return (
            self.provider == "supabase"
            and bool(self.supabase_url)
            and bool(self.supabase_service_key)
        )

    @staticmethod
    def build_uri(bucket: str, object_key: str) -> str:
        clean_bucket = bucket.strip("/")
        clean_key = object_key.lstrip("/")
        return f"{STORAGE_URI_PREFIX}{clean_bucket}/{clean_key}"

    @staticmethod
    def parse_uri(uri: str) -> Optional[Tuple[str, str]]:
        if not uri or not uri.startswith(STORAGE_URI_PREFIX):
            return None
        remainder = uri[len(STORAGE_URI_PREFIX) :]
        if "/" not in remainder:
            return None
        bucket, key = remainder.split("/", 1)
        if not bucket or not key:
            return None
        return bucket, key

    def _safe_local_path(self, bucket: str, object_key: str) -> str:
        """Resolve local fallback path while strictly preventing path traversal."""
        base = os.path.realpath(self.local_root)
        joined = os.path.realpath(os.path.join(base, bucket, object_key.lstrip("/")))
        if not joined.startswith(base + os.sep):
            raise ValueError("Invalid storage object key: path traversal detected.")
        return joined

    async def _ensure_supabase_bucket(self, client: httpx.AsyncClient, bucket: str) -> None:
        url = f"{self.supabase_url}/storage/v1/bucket"
        headers = {
            "Authorization": f"Bearer {self.supabase_service_key}",
            "apikey": self.supabase_service_key,
            "Content-Type": "application/json",
        }
        try:
            await client.post(url, headers=headers, json={"id": bucket, "name": bucket, "public": False})
        except Exception as exc:
            logger.debug("Supabase bucket ensure ignored for %s: %s", bucket, exc)

    async def _ensure_s3_bucket(self, client: httpx.AsyncClient, bucket: str) -> None:
        url = f"{self.s3_endpoint}/{bucket}"
        headers = _aws_sigv4_headers("PUT", url, b"", self.s3_access_key, self.s3_secret_key)
        try:
            await client.put(url, headers=headers)
        except Exception as exc:
            logger.debug("S3 bucket ensure ignored for %s: %s", bucket, exc)

    async def upload_bytes(
        self,
        bucket: str,
        object_key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload raw bytes to Supabase Storage or S3, falling back safely to local volume if unreachable."""
        clean_key = object_key.lstrip("/")
        if ".." in clean_key.split("/"):
            raise ValueError("Invalid object key: parent directory reference forbidden.")

        if self._use_supabase():
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    url = f"{self.supabase_url}/storage/v1/object/{bucket}/{quote(clean_key, safe='/')}"
                    headers = {
                        "Authorization": f"Bearer {self.supabase_service_key}",
                        "apikey": self.supabase_service_key,
                        "Content-Type": content_type,
                        "x-upsert": "true",
                    }
                    resp = await client.post(url, headers=headers, content=data)
                    if resp.status_code in (400, 404):
                        await self._ensure_supabase_bucket(client, bucket)
                        resp = await client.post(url, headers=headers, content=data)
                    if resp.status_code in (200, 201):
                        self.last_backend = "supabase"
                        return self.build_uri(bucket, clean_key)
                    logger.warning("Supabase upload returned %s: %s", resp.status_code, resp.text[:200])
            except Exception as exc:
                logger.warning("Supabase upload failed, falling back: %s", exc)

        if self.s3_endpoint:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    url = f"{self.s3_endpoint}/{bucket}/{quote(clean_key, safe='/')}"
                    headers = _aws_sigv4_headers(
                        "PUT",
                        url,
                        data,
                        self.s3_access_key,
                        self.s3_secret_key,
                        content_type=content_type,
                    )
                    resp = await client.put(url, headers=headers, content=data)
                    if resp.status_code == 404:
                        await self._ensure_s3_bucket(client, bucket)
                        headers = _aws_sigv4_headers(
                            "PUT",
                            url,
                            data,
                            self.s3_access_key,
                            self.s3_secret_key,
                            content_type=content_type,
                        )
                        resp = await client.put(url, headers=headers, content=data)
                    if resp.status_code in (200, 201, 204):
                        self.last_backend = "s3"
                        return self.build_uri(bucket, clean_key)
                    logger.warning("S3 upload returned %s: %s", resp.status_code, resp.text[:200])
            except Exception as exc:
                logger.warning("S3 upload failed, using local volume fallback: %s", exc)

        local_path = self._safe_local_path(bucket, clean_key)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(data)
        self.last_backend = "local_fallback"
        return local_path

    async def download_bytes(self, file_uri: str) -> Tuple[bytes, str]:
        """Download object bytes by storage:// URI or safe local legacy path. Returns (bytes, content_type)."""
        parsed = self.parse_uri(file_uri)
        if parsed is not None:
            bucket, key = parsed
            if self._use_supabase():
                try:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        url = f"{self.supabase_url}/storage/v1/object/{bucket}/{quote(key, safe='/')}"
                        headers = {
                            "Authorization": f"Bearer {self.supabase_service_key}",
                            "apikey": self.supabase_service_key,
                        }
                        resp = await client.get(url, headers=headers)
                        if resp.status_code == 200:
                            self.last_backend = "supabase"
                            return resp.content, resp.headers.get("content-type", "application/octet-stream")
                except Exception as exc:
                    logger.warning("Supabase download failed for %s: %s", file_uri, exc)

            if self.s3_endpoint:
                try:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        url = f"{self.s3_endpoint}/{bucket}/{quote(key, safe='/')}"
                        headers = _aws_sigv4_headers("GET", url, b"", self.s3_access_key, self.s3_secret_key)
                        resp = await client.get(url, headers=headers)
                        if resp.status_code == 200:
                            self.last_backend = "s3"
                            return resp.content, resp.headers.get("content-type", "application/octet-stream")
                except Exception as exc:
                    logger.warning("S3 download failed for %s: %s", file_uri, exc)

            # Local fallback lookup for storage:// URI
            local_path = self._safe_local_path(bucket, key)
            if os.path.isfile(local_path):
                with open(local_path, "rb") as f:
                    self.last_backend = "local_fallback"
                    return f.read(), "application/octet-stream"
            raise FileNotFoundError(f"Object not found in storage: {file_uri}")

        # Legacy local file path inside local_root (strictly validated against path traversal)
        base = os.path.realpath(self.local_root)
        real_target = os.path.realpath(file_uri)
        if not real_target.startswith(base + os.sep):
            raise ValueError("Access outside permitted storage root is forbidden.")
        if not os.path.isfile(real_target):
            raise FileNotFoundError(f"Local file not found: {file_uri}")
        with open(real_target, "rb") as f:
            self.last_backend = "local_legacy"
            return f.read(), "application/octet-stream"

    async def delete_object(self, file_uri: str) -> bool:
        """Delete an object from Supabase Storage, S3, or local fallback."""
        parsed = self.parse_uri(file_uri)
        if parsed is not None:
            bucket, key = parsed
            if self._use_supabase():
                try:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        url = f"{self.supabase_url}/storage/v1/object/{bucket}/{quote(key, safe='/')}"
                        headers = {
                            "Authorization": f"Bearer {self.supabase_service_key}",
                            "apikey": self.supabase_service_key,
                        }
                        resp = await client.delete(url, headers=headers)
                        if resp.status_code in (200, 204):
                            return True
                except Exception as exc:
                    logger.warning("Supabase delete failed for %s: %s", file_uri, exc)
            if self.s3_endpoint:
                try:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        url = f"{self.s3_endpoint}/{bucket}/{quote(key, safe='/')}"
                        headers = _aws_sigv4_headers("DELETE", url, b"", self.s3_access_key, self.s3_secret_key)
                        resp = await client.delete(url, headers=headers)
                        if resp.status_code in (200, 204):
                            return True
                except Exception as exc:
                    logger.warning("S3 delete failed for %s: %s", file_uri, exc)
            local_path = self._safe_local_path(bucket, key)
            if os.path.isfile(local_path):
                os.remove(local_path)
                return True
            return False

        base = os.path.realpath(self.local_root)
        real_target = os.path.realpath(file_uri)
        if real_target.startswith(base + os.sep) and os.path.isfile(real_target):
            os.remove(real_target)
            return True
        return False

    async def materialize_temp_file(self, file_uri: str, suffix: str = "") -> Tuple[str, bool]:
        """
        Ensure a readable local file path exists for ingestion tools (Repomix / PyMuPDF).
        Returns (local_file_path, should_cleanup).
        """
        if not file_uri.startswith(STORAGE_URI_PREFIX):
            return file_uri, False

        data, _ = await self.download_bytes(file_uri)
        if not suffix:
            _, ext = os.path.splitext(file_uri)
            suffix = ext
        fd, tmp_path = tempfile.mkstemp(prefix="adlas-obj-", suffix=suffix)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise
        return tmp_path, True


storage_client = ObjectStorageClient()
