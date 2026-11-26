# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Universal Submission Digest Builder uniting Repomix AST Code Packing and Gemini 2-Call Summarization."""

import logging
import os
import shutil
import tarfile
import tempfile
from typing import Any, Dict, Optional
import uuid
import zipfile
from app.core.storage_client import STORAGE_URI_PREFIX, storage_client
from app.modules.ai_gateway.service import AIGatewayService
from app.modules.assessment.ingestion.document_summarizer import DocumentSummarizer
from app.modules.assessment.ingestion.repomix_client import RepomixClient

logger = logging.getLogger(__name__)
SHARED_EXTRACT_ROOT = "/app/uploads/tmp_extract"
MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024  # 100MB safety limit


class UniversalSubmissionDigest:
    """Unified context object passed to AI Gateway Call 2 to generate Viva defense questions."""

    def __init__(self, digest_type: str, content: str, metadata: Dict[str, Any]):
        self.digest_type = digest_type  # "CODE" | "DOCUMENT"
        self.content = content
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        return {
            "digest_type": self.digest_type,
            "content": self.content,
            "metadata": self.metadata,
        }


class UniversalDigestBuilder:
    """Orchestrates ingestion across code repositories (Repomix AST) and documents (Gemini Call 1)."""

    def __init__(
        self,
        repomix_client: Optional[RepomixClient] = None,
        summarizer: Optional[DocumentSummarizer] = None,
        ai_gateway: Optional[AIGatewayService] = None,
    ):
        self.repomix_client = repomix_client or RepomixClient()
        self.summarizer = summarizer or DocumentSummarizer()
        self.ai_gateway = ai_gateway or AIGatewayService()

    async def build_digest(
        self,
        file_path: Optional[str] = None,
        git_repo_url: Optional[str] = None,
        file_name: Optional[str] = None,
        project_title: str = "",
        assignment_title: str = "",
    ) -> UniversalSubmissionDigest:
        """Analyze submission type, pack/extract raw content, and run Call 1 summarization."""
        # 1. Git Repository Submission
        if git_repo_url:
            pack_res = await self.repomix_client.pack_source_code(git_url=git_repo_url, max_tokens=45000)
            packed_xml = pack_res.get("packed_xml", "")
            summary, mode = await self.ai_gateway.summarize_submission(
                digest_type="CODE",
                raw_content=packed_xml,
                project_title=project_title,
                assignment_title=assignment_title,
            )
            return UniversalSubmissionDigest(
                digest_type="CODE",
                content=summary,
                metadata={
                    "source": "git_repository",
                    "url": git_repo_url,
                    "repomix_source": pack_res.get("source"),
                    "estimated_tokens": pack_res.get("estimated_tokens", 0),
                    "summarizer_mode": mode,
                },
            )

        # 2. File Upload Submission (supports storage:// Supabase/S3 URI and legacy local paths)
        resolved_path = file_path
        cleanup_temp = False
        if file_path and file_path.startswith(STORAGE_URI_PREFIX):
            try:
                resolved_path, cleanup_temp = await storage_client.materialize_temp_file(file_path)
            except Exception as exc:
                logger.warning("Failed to materialize storage object %s: %s", file_path, exc)
                resolved_path = None

        try:
            if resolved_path and os.path.exists(resolved_path):
                ext = os.path.splitext(resolved_path)[1].lower()

                # Zip / Tar Archive (Source code) -> extract to shared directory for Repomix AST packing
                if ext in {".zip", ".tar", ".gz", ".tgz"}:
                    extract_dir = self._safe_extract_archive(resolved_path, ext)
                    try:
                        pack_res = await self.repomix_client.pack_source_code(
                            source_path=extract_dir,
                            max_tokens=45000,
                        )
                    finally:
                        if extract_dir and os.path.exists(extract_dir):
                            shutil.rmtree(extract_dir, ignore_errors=True)

                    packed_xml = pack_res.get("packed_xml", "")
                    summary, mode = await self.ai_gateway.summarize_submission(
                        digest_type="CODE",
                        raw_content=packed_xml,
                        project_title=project_title,
                        assignment_title=assignment_title,
                    )
                    return UniversalSubmissionDigest(
                        digest_type="CODE",
                        content=summary,
                        metadata={
                            "source": "zip_archive",
                            "file_name": file_name or os.path.basename(resolved_path),
                            "repomix_source": pack_res.get("source"),
                            "estimated_tokens": pack_res.get("estimated_tokens", 0),
                            "summarizer_mode": mode,
                        },
                    )

                # Document (PDF, DOCX, TXT, MD)
                elif ext in {".pdf", ".docx", ".txt", ".md"}:
                    raw_text = self.summarizer.extract_text_from_file(resolved_path)
                    doc_label = file_name or os.path.basename(resolved_path)
                    summary, mode = await self.ai_gateway.summarize_submission(
                        digest_type="DOCUMENT",
                        raw_content=raw_text,
                        project_title=project_title or doc_label,
                        assignment_title=assignment_title,
                    )
                    return UniversalSubmissionDigest(
                        digest_type="DOCUMENT",
                        content=summary,
                        metadata={
                            "source": "document_report",
                            "file_name": doc_label,
                            "original_word_count": len(raw_text.split()),
                            "digest_word_count": len(summary.split()),
                            "summarizer_mode": mode,
                        },
                    )
        finally:
            if cleanup_temp and resolved_path and os.path.exists(resolved_path):
                try:
                    os.remove(resolved_path)
                except OSError:
                    pass

        # Fallback when no content could be extracted from file
        doc_label = file_name or (os.path.basename(file_path) if file_path else "Tài liệu nộp bài")
        return UniversalSubmissionDigest(
            digest_type="DOCUMENT",
            content=f"Tài liệu nộp: {doc_label}. Sinh viên tham gia phản biện trực tiếp dựa trên nội dung đề tài và sản phẩm đã nộp.",
            metadata={"source": "empty_fallback", "file_name": doc_label, "summarizer_mode": "empty_fallback"},
        )

    def _safe_extract_archive(self, archive_path: str, ext: str) -> str:
        """Extract .zip or .tar(.gz) archive safely into a temporary directory on shared storage."""
        try:
            os.makedirs(SHARED_EXTRACT_ROOT, exist_ok=True)
            extract_dir = os.path.join(SHARED_EXTRACT_ROOT, str(uuid.uuid4()))
            os.makedirs(extract_dir, exist_ok=True)
        except OSError:
            extract_dir = tempfile.mkdtemp(prefix="adlas-extract-")

        real_root = os.path.realpath(extract_dir)
        total_bytes = 0

        try:
            if ext == ".zip" and zipfile.is_zipfile(archive_path):
                with zipfile.ZipFile(archive_path, "r") as zf:
                    for info in zf.infolist():
                        if info.is_dir():
                            continue
                        total_bytes += info.file_size
                        if total_bytes > MAX_UNCOMPRESSED_BYTES:
                            logger.warning("Archive %s exceeds uncompressed size limit.", archive_path)
                            break
                        target = os.path.realpath(os.path.join(extract_dir, info.filename))
                        if not target.startswith(real_root + os.sep):
                            continue
                        os.makedirs(os.path.dirname(target), exist_ok=True)
                        with zf.open(info) as src, open(target, "wb") as dst:
                            shutil.copyfileobj(src, dst)
            elif tarfile.is_tarfile(archive_path):
                with tarfile.open(archive_path, "r:*") as tf:
                    for member in tf.getmembers():
                        if not member.isfile():
                            continue
                        total_bytes += member.size
                        if total_bytes > MAX_UNCOMPRESSED_BYTES:
                            break
                        target = os.path.realpath(os.path.join(extract_dir, member.name))
                        if not target.startswith(real_root + os.sep):
                            continue
                        os.makedirs(os.path.dirname(target), exist_ok=True)
                        src = tf.extractfile(member)
                        if src:
                            with src, open(target, "wb") as dst:
                                shutil.copyfileobj(src, dst)
        except Exception as exc:
            logger.warning("Failed to extract archive %s: %s", archive_path, exc)

        return extract_dir
