# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Section extraction, paragraph indexing, and scan detection for PDF/PPTX materials (T2-I-M2-04)."""

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.modules.learning.exceptions import (
    InvalidMaterialFormatException,
    NoTextLayerException,
)

logger = logging.getLogger(__name__)

MIN_TOTAL_ALPHA_CHARS = 50
MIN_AVG_ALPHA_CHARS_PER_PAGE = 15


@dataclass
class IndexedParagraph:
    """Single paragraph indexed by page/slide and paragraph order."""

    page: int
    paragraph: int
    text: str
    word_count: int


@dataclass
class ExtractedDocument:
    """Full extracted document with per-page titles and indexed paragraphs."""

    total_pages: int
    page_titles: Dict[int, str]
    page_word_counts: Dict[int, int]
    paragraphs: List[IndexedParagraph]
    toc_entries: List[Tuple[int, str, int]]  # (level, title, start_page)


class SectionExtractor:
    """Extracts paragraph-indexed text and hierarchical sections from PDF and PPTX files."""

    def extract_document(self, file_path: str) -> ExtractedDocument:
        """Extract raw text, check for scan/no-text-layer (E-RAG-01), and index paragraphs."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            doc = self._extract_pdf(file_path)
        elif ext == ".pptx":
            doc = self._extract_pptx(file_path)
        elif ext == ".ppt":
            raise InvalidMaterialFormatException(
                "Định dạng .ppt nhị phân cũ không hỗ trợ bóc tách tự động. "
                "Vui lòng chuyển đổi sang .pptx hoặc .pdf."
            )
        else:
            raise InvalidMaterialFormatException(
                f"Định dạng '{ext}' không hỗ trợ bóc tách chương mục. Chỉ hỗ trợ .pdf và .pptx."
            )

        # E-RAG-01: Scan / No Text Layer detection
        total_alpha = sum(
            sum(1 for ch in p.text if ch.isalpha()) for p in doc.paragraphs
        )
        avg_alpha = total_alpha / max(1, doc.total_pages)
        if total_alpha < MIN_TOTAL_ALPHA_CHARS or avg_alpha < MIN_AVG_ALPHA_CHARS_PER_PAGE:
            raise NoTextLayerException()

        return doc

    def _extract_pdf(self, file_path: str) -> ExtractedDocument:
        import fitz

        pdf = fitz.open(file_path)
        try:
            total_pages = len(pdf)
            toc = pdf.get_toc() or []
            toc_entries: List[Tuple[int, str, int]] = [
                (lvl, title.strip(), max(1, page))
                for lvl, title, page in toc
                if title and title.strip()
            ]
            page_titles: Dict[int, str] = {}
            page_word_counts: Dict[int, int] = {}
            paragraphs: List[IndexedParagraph] = []

            for page_idx, page in enumerate(pdf, start=1):
                raw_text = page.get_text("text") or ""
                blocks = [b.strip() for b in re.split(r"\n\s*\n", raw_text) if b.strip()]
                if not blocks:
                    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
                    if lines:
                        blocks = [" ".join(lines)]

                first_line = blocks[0].splitlines()[0].strip()[:90] if blocks else f"Trang {page_idx}"
                page_titles[page_idx] = first_line
                p_words = 0
                for para_idx, block in enumerate(blocks, start=1):
                    clean = re.sub(r"\s+", " ", block).strip()
                    if not clean:
                        continue
                    wc = len(clean.split())
                    p_words += wc
                    paragraphs.append(
                        IndexedParagraph(
                            page=page_idx,
                            paragraph=para_idx,
                            text=clean,
                            word_count=wc,
                        )
                    )
                page_word_counts[page_idx] = p_words

            return ExtractedDocument(
                total_pages=total_pages,
                page_titles=page_titles,
                page_word_counts=page_word_counts,
                paragraphs=paragraphs,
                toc_entries=toc_entries,
            )
        finally:
            pdf.close()

    def _extract_pptx(self, file_path: str) -> ExtractedDocument:
        from pptx import Presentation

        prs = Presentation(file_path)
        total_pages = len(prs.slides)
        page_titles: Dict[int, str] = {}
        page_word_counts: Dict[int, int] = {}
        paragraphs: List[IndexedParagraph] = []

        for slide_idx, slide in enumerate(prs.slides, start=1):
            title_text = ""
            if slide.shapes.title and slide.shapes.title.text:
                title_text = slide.shapes.title.text.strip()
            page_titles[slide_idx] = title_text or f"Slide {slide_idx}"

            para_counter = 0
            s_words = 0
            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue
                lines = [
                    re.sub(r"\s+", " ", p.text).strip()
                    for p in shape.text_frame.paragraphs
                    if p.text and p.text.strip()
                ]
                if not lines:
                    continue
                block_text = " ".join(lines)
                para_counter += 1
                wc = len(block_text.split())
                s_words += wc
                paragraphs.append(
                    IndexedParagraph(
                        page=slide_idx,
                        paragraph=para_counter,
                        text=block_text,
                        word_count=wc,
                    )
                )
            page_word_counts[slide_idx] = s_words

        return ExtractedDocument(
            total_pages=total_pages,
            page_titles=page_titles,
            page_word_counts=page_word_counts,
            paragraphs=paragraphs,
            toc_entries=[],
        )

    async def build_sections(
        self,
        doc: ExtractedDocument,
        ai_gateway: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """Build hierarchical sections using TOC if available, else Pass-1 LLM grouping with heuristic fallback."""
        # Fast-path: use PDF TOC if it has >= 2 top-level entries
        top_toc = [t for t in doc.toc_entries if t[0] == 1]
        if len(top_toc) >= 2:
            sections: List[Dict[str, Any]] = []
            for idx, (_, title, start_p) in enumerate(top_toc, start=1):
                end_p = (
                    top_toc[idx][2] - 1
                    if idx < len(top_toc)
                    else doc.total_pages
                )
                end_p = max(start_p, min(end_p, doc.total_pages))
                wc = sum(doc.page_word_counts.get(p, 0) for p in range(start_p, end_p + 1))
                sections.append(
                    {
                        "section_id": idx,
                        "title": f"{title} (Trang {start_p}-{end_p})",
                        "start_page": start_p,
                        "end_page": end_p,
                        "word_count": wc,
                        "summary": self._fallback_summary(doc, start_p, end_p),
                    }
                )
            return sections

        # Pass-1 LLM grouping if AI gateway is available
        if ai_gateway is not None:
            llm_sections = await self._group_with_llm(doc, ai_gateway)
            if llm_sections:
                return llm_sections

        # Deterministic fallback: group into chunks of ~5 pages
        return self._fallback_group_pages(doc, chunk_size=5)

    async def _group_with_llm(
        self, doc: ExtractedDocument, ai_gateway: Any
    ) -> Optional[List[Dict[str, Any]]]:
        spine_lines = [
            f"Trang {p}: {doc.page_titles.get(p, '')} ({doc.page_word_counts.get(p, 0)} từ)"
            for p in range(1, doc.total_pages + 1)
        ]
        prompt = (
            "<document_outline>\n"
            + "\n".join(spine_lines)
            + "\n</document_outline>\n\n"
            "Hãy gom các trang liên tiếp trên thành các chương/phân đoạn hợp lý (tối đa 10 phân đoạn). "
            "Trả về JSON array, mỗi phần tử gồm: "
            '{"title": "Tên chương/mục", "start_page": int, "end_page": int, "summary": "Tóm tắt ngắn 1-2 câu"}. '
            "Đảm bảo start_page và end_page phủ liên tục từ 1 đến "
            f"{doc.total_pages}."
        )
        raw = await ai_gateway._call_gemini_raw(
            prompt, response_mime_type="application/json", temperature=0.1
        )
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, list) or not parsed:
                return None
            sections: List[Dict[str, Any]] = []
            for idx, item in enumerate(parsed, start=1):
                sp = max(1, int(item.get("start_page", 1)))
                ep = min(doc.total_pages, max(sp, int(item.get("end_page", sp))))
                title = str(item.get("title") or f"Phần {idx}").strip()
                if f"Trang {sp}" not in title:
                    title = f"{title} (Trang {sp}-{ep})"
                wc = sum(doc.page_word_counts.get(p, 0) for p in range(sp, ep + 1))
                sections.append(
                    {
                        "section_id": idx,
                        "title": title,
                        "start_page": sp,
                        "end_page": ep,
                        "word_count": wc,
                        "summary": str(item.get("summary") or "").strip(),
                    }
                )
            return sections
        except Exception as exc:
            logger.warning("Failed to parse Pass-1 LLM sections JSON: %s", exc)
            return None

    def _fallback_group_pages(
        self, doc: ExtractedDocument, chunk_size: int = 5
    ) -> List[Dict[str, Any]]:
        sections: List[Dict[str, Any]] = []
        for idx, start_p in enumerate(range(1, doc.total_pages + 1, chunk_size), start=1):
            end_p = min(doc.total_pages, start_p + chunk_size - 1)
            wc = sum(doc.page_word_counts.get(p, 0) for p in range(start_p, end_p + 1))
            first_title = doc.page_titles.get(start_p, f"Phần {idx}")
            sections.append(
                {
                    "section_id": idx,
                    "title": f"{first_title} (Trang {start_p}-{end_p})",
                    "start_page": start_p,
                    "end_page": end_p,
                    "word_count": wc,
                    "summary": self._fallback_summary(doc, start_p, end_p),
                }
            )
        return sections

    def _fallback_summary(
        self, doc: ExtractedDocument, start_p: int, end_p: int
    ) -> str:
        snippets = [
            p.text for p in doc.paragraphs if start_p <= p.page <= end_p
        ][:2]
        joined = " ".join(snippets)
        words = joined.split()
        if len(words) <= 35:
            return joined
        return " ".join(words[:35]) + "..."
