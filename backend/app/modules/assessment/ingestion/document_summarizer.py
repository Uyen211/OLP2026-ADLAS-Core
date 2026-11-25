# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Clean raw document extractor for academic PDF, DOCX, TXT, and Markdown submissions."""

import logging
import os
from typing import List

logger = logging.getLogger(__name__)

MAX_SINGLE_CALL_WORDS = 45000


class DocumentSummarizer:
    """
    Extracts clean raw text from student document submissions (.pdf, .docx, .txt, .md)
    and splits oversized documents (> 45,000 words) along paragraph boundaries for
    Long-Context Gemini summarization without regex or heuristic truncation.
    """

    def extract_text_from_file(self, file_path: str) -> str:
        """Extract raw text content from PDF, DOCX, TXT, or Markdown file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            return self._extract_pdf(file_path)
        elif ext == ".docx":
            return self._extract_docx(file_path)
        elif ext in {".txt", ".md"}:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read().strip()
        else:
            raise ValueError(f"Unsupported document format: {ext}")

    def _extract_pdf(self, file_path: str) -> str:
        """Extract text from all pages of a PDF using PyMuPDF (fitz)."""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            pages = []
            for page in doc:
                text = page.get_text("text")
                if text and text.strip():
                    pages.append(text.strip())
            doc.close()
            return "\n\n".join(pages)
        except Exception as exc:
            logger.warning("PyMuPDF extraction failed (%s), falling back to raw read", exc)
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(100000).strip()

    def _extract_docx(self, file_path: str) -> str:
        """Extract paragraphs and table contents cleanly from a DOCX file."""
        try:
            import docx
            doc = docx.Document(file_path)
            blocks: List[str] = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

            for table in doc.tables:
                table_rows = []
                for row in table.rows:
                    cells = [c.text.strip() for c in row.cells if c.text.strip()]
                    if cells:
                        table_rows.append(" | ".join(cells))
                if table_rows:
                    blocks.append("\n".join(table_rows))

            return "\n\n".join(blocks)
        except Exception as exc:
            logger.warning("python-docx extraction failed (%s), falling back to raw read", exc)
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(100000).strip()

    @staticmethod
    def split_large_text_by_paragraphs(
        text: str,
        max_words: int = 20000,
        overlap_paragraphs: int = 2,
    ) -> List[str]:
        """Split oversized documents (> 45,000 words) along paragraph boundaries."""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            return []

        total_words = sum(len(p.split()) for p in paragraphs)
        if total_words <= max_words:
            return ["\n\n".join(paragraphs)]

        chunks: List[str] = []
        idx = 0
        n = len(paragraphs)
        while idx < n:
            curr: List[str] = []
            curr_words = 0
            j = idx
            while j < n:
                p_words = len(paragraphs[j].split())
                if curr and curr_words + p_words > max_words:
                    break
                curr.append(paragraphs[j])
                curr_words += p_words
                j += 1

            chunks.append("\n\n".join(curr))
            if j >= n:
                break
            idx = max(idx + 1, j - overlap_paragraphs)

        return chunks

    @staticmethod
    def build_offline_excerpt(text: str, max_words: int = 500) -> str:
        """Clean fallback excerpt when Gemini API is unreachable."""
        words = text.split()
        if not words:
            return "Tài liệu không có nội dung văn bản đáng kể."
        if len(words) <= max_words:
            return text.strip()
        head = " ".join(words[: max_words // 2])
        tail = " ".join(words[-(max_words // 2):])
        return f"{head}\n\n[...]\n\n{tail}"
