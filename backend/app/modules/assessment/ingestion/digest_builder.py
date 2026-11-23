# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Universal Submission Digest Builder uniting Code (Repomix) and Text (Summarizer)."""

import os
from typing import Any, Dict, Optional
from app.modules.assessment.ingestion.document_summarizer import DocumentSummarizer
from app.modules.assessment.ingestion.repomix_client import RepomixClient


class UniversalSubmissionDigest:
    """Unified context object passed to AI Gateway to generate Viva defense questions."""

    def __init__(self, digest_type: str, content: str, metadata: Dict[str, Any]):
        self.digest_type = digest_type  # "CODE" | "DOCUMENT"
        self.content = content
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        return {
            "digest_type": self.digest_type,
            "content": self.content,
            "metadata": self.metadata
        }


class UniversalDigestBuilder:
    """Orchestrates ingestion across code repositories and text reports."""

    def __init__(self, repomix_client: Optional[RepomixClient] = None, summarizer: Optional[DocumentSummarizer] = None):
        self.repomix_client = repomix_client or RepomixClient()
        self.summarizer = summarizer or DocumentSummarizer()

    async def build_digest(
        self,
        file_path: Optional[str] = None,
        git_repo_url: Optional[str] = None,
        file_name: Optional[str] = None
    ) -> UniversalSubmissionDigest:
        """Analyze submission type and construct a token-budgeted universal digest."""
        # 1. Git Repository Submission
        if git_repo_url:
            pack_res = await self.repomix_client.pack_source_code(git_url=git_repo_url, max_tokens=1800)
            return UniversalSubmissionDigest(
                digest_type="CODE",
                content=pack_res.get("packed_xml", ""),
                metadata={
                    "source": "git_repository",
                    "url": git_repo_url,
                    "estimated_tokens": pack_res.get("estimated_tokens", 0)
                }
            )

        # 2. File Upload Submission
        if file_path and os.path.exists(file_path):
            ext = os.path.splitext(file_path)[1].lower()

            # Zip Archive (Source code)
            if ext in {".zip", ".tar", ".gz"}:
                pack_res = await self.repomix_client.pack_source_code(source_path=file_path, max_tokens=1800)
                return UniversalSubmissionDigest(
                    digest_type="CODE",
                    content=pack_res.get("packed_xml", ""),
                    metadata={
                        "source": "zip_archive",
                        "file_name": file_name or os.path.basename(file_path),
                        "estimated_tokens": pack_res.get("estimated_tokens", 0)
                    }
                )

            # Document (PDF, DOCX, TXT)
            elif ext in {".pdf", ".docx", ".txt", ".md"}:
                text = self.summarizer.extract_text_from_file(file_path)
                summary_res = self.summarizer.recursive_map_reduce(text)
                return UniversalSubmissionDigest(
                    digest_type="DOCUMENT",
                    content=summary_res["executive_summary"],
                    metadata={
                        "source": "document_report",
                        "file_name": file_name or os.path.basename(file_path),
                        "original_word_count": summary_res["original_word_count"],
                        "digest_word_count": summary_res["digest_word_count"]
                    }
                )

        # Fallback when no content could be extracted from file
        doc_label = file_name or (os.path.basename(file_path) if file_path else "Tài liệu nộp bài")
        return UniversalSubmissionDigest(
            digest_type="DOCUMENT",
            content=f"Tài liệu nộp: {doc_label}. Sinh viên tham gia phản biện trực tiếp dựa trên nội dung đề tài và sản phẩm đã nộp.",
            metadata={"source": "empty_fallback", "file_name": doc_label}
        )
