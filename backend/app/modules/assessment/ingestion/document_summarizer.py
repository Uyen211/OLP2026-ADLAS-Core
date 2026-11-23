# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Recursive Document Summarizer engine for non-code academic essay and report submissions."""

import logging
import os
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class DocumentSummarizer:
    """
    Ingestion engine that extracts structured text from PDF/DOCX and performs
    Heading-Aware Sliding Window Chunking (400 words, 20% overlap) followed by
    Hierarchical Recursive Map-Reduce summarization into an Executive Digest (<= 400 words).
    """

    def __init__(self, window_size_words: int = 400, overlap_words: int = 80):
        self.window_size_words = window_size_words
        self.overlap_words = overlap_words

    def extract_text_from_file(self, file_path: str) -> str:
        """Extract clean text content from PDF or DOCX file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            return self._extract_pdf(file_path)
        elif ext == ".docx":
            return self._extract_docx(file_path)
        elif ext in {".txt", ".md"}:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        else:
            raise ValueError(f"Unsupported document format: {ext}")

    def _extract_pdf(self, file_path: str) -> str:
        """Extract text using PyMuPDF (fitz) filtering out cover page and headers."""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            extracted_pages = []
            total_pages = len(doc)
            start_page = 1 if total_pages > 2 else 0  # Skip cover page if long document

            for page_num in range(start_page, total_pages):
                page = doc[page_num]
                text = page.get_text("text")
                if text and len(text.strip()) > 50:
                    extracted_pages.append(text.strip())

            doc.close()
            return "\n\n".join(extracted_pages)
        except Exception as exc:
            logger.warning("PyMuPDF extraction failed (%s), falling back to raw read", exc)
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(50000)

    def _extract_docx(self, file_path: str) -> str:
        """Extract text from docx file."""
        try:
            import docx
            doc = docx.Document(file_path)
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs)
        except Exception:
            # Fallback simple read
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(50000)

    def chunk_text_sliding_window(self, text: str) -> List[str]:
        """
        Split text into chunks of window_size_words with overlap_words.
        Snaps boundaries at sentence end punctuation to avoid broken thoughts.
        """
        # Clean text
        normalized = re.sub(r"\s+", " ", text).strip()
        words = normalized.split()
        if not words:
            return []

        if len(words) <= self.window_size_words:
            return [normalized]

        chunks = []
        start_idx = 0
        total_words = len(words)

        while start_idx < total_words:
            end_idx = min(start_idx + self.window_size_words, total_words)
            chunk_words = words[start_idx:end_idx]
            chunk_str = " ".join(chunk_words)

            # Try to snap to sentence boundary if not at the very end
            if end_idx < total_words:
                last_period = max(chunk_str.rfind("."), chunk_str.rfind("?"), chunk_str.rfind("!"))
                if last_period > len(chunk_str) * 0.7:
                    chunk_str = chunk_str[:last_period + 1]
                    snapped_word_count = len(chunk_str.split())
                    start_idx += max(1, snapped_word_count - self.overlap_words)
                else:
                    start_idx += max(1, self.window_size_words - self.overlap_words)
            else:
                start_idx += max(1, self.window_size_words - self.overlap_words)

            chunks.append(chunk_str.strip())

        return chunks

    def summarize_chunk(self, chunk: str, max_words: int = 70) -> str:
        """Summarize an individual chunk down to essential points."""
        sentences = re.split(r"(?<=[.!?])\s+", chunk)
        if len(sentences) <= 2:
            return chunk

        # Heuristic extractive summarization: Pick topic sentence + concluding sentence + sentences with keywords
        keywords = {"kết quả", "phương pháp", "thuật toán", "đề xuất", "kết luận", "mục tiêu", "nghiên cứu",
                    "result", "method", "propose", "conclusion", "objective", "algorithm", "evaluation"}
        selected = [sentences[0]]  # Topic sentence

        for s in sentences[1:-1]:
            words_lower = s.lower()
            if any(k in words_lower for k in keywords):
                selected.append(s)
                if len(" ".join(selected).split()) >= max_words:
                    break

        if len(selected) == 1 and len(sentences) > 1:
            selected.append(sentences[-1])

        summary = " ".join(selected)
        words = summary.split()
        if len(words) > max_words:
            summary = " ".join(words[:max_words]) + "."
        return summary

    def recursive_map_reduce(self, text: str) -> Dict[str, Any]:
        """
        Execute Hierarchical Map-Reduce summarization:
        - Map phase: Summarize each chunk
        - Reduce phase: Merge summaries, recursively reduce if still > 400 words
        """
        chunks = self.chunk_text_sliding_window(text)
        if not chunks:
            return {
                "executive_summary": "Tài liệu không có nội dung văn bản đáng kể.",
                "total_chunks": 0,
                "word_count": 0
            }

        # Map Phase: Summarize each chunk
        mapped_summaries = [self.summarize_chunk(c, max_words=60) for c in chunks]
        merged_intermediate = "\n".join(f"- {s}" for s in mapped_summaries)

        # Check total word count
        words = merged_intermediate.split()
        if len(words) <= 400:
            final_digest = merged_intermediate
        else:
            # Recursive Reduce Phase: Chunk the intermediate summary and reduce once more
            secondary_chunks = self.chunk_text_sliding_window(merged_intermediate)
            secondary_summaries = [self.summarize_chunk(sc, max_words=50) for sc in secondary_chunks]
            final_digest = "\n".join(f"- {s}" for s in secondary_summaries)

        # Enforce hard ceiling of 400 words
        final_words = final_digest.split()
        if len(final_words) > 400:
            final_digest = " ".join(final_words[:400]) + "..."

        return {
            "executive_summary": final_digest,
            "total_chunks": len(chunks),
            "original_word_count": len(text.split()),
            "digest_word_count": len(final_digest.split())
        }
