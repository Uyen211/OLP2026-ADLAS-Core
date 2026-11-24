# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Recursive Document Summarizer engine for non-code academic essay and report submissions."""

from collections import Counter
import logging
import math
import os
import re
from typing import Any, Dict, List, Optional, Tuple
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class DocumentSummarizer:
    """
    Ingestion engine that extracts structured text from PDF/DOCX, performs
    sentence-boundary-safe Sliding Window Chunking (400 words, 20% overlap),
    and produces a coherent Executive Digest (<= 400 words) via Gemini Map-Reduce
    with a Section-Aware TF-IDF extractive fallback.
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
            start_page = 1 if total_pages > 2 else 0

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
        """Extract text from docx file, skipping cover page, TOC, and reference lists."""
        try:
            import docx
            doc = docx.Document(file_path)
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

            # Skip cover page / TOC boilerplate until main body starts
            start_idx = 0
            for idx, text in enumerate(paragraphs[:100]):
                upper = text.upper()
                if any(marker in upper for marker in ("CHƯƠNG 1", "CHƯƠNG I", "1.1.", "MỞ ĐẦU", "INTRODUCTION")):
                    if idx + 1 < len(paragraphs) and any(len(p.split()) > 20 for p in paragraphs[idx:idx + 8]):
                        start_idx = idx
                        break

            # Trim trailing bibliography / references section if near the end
            end_idx = len(paragraphs)
            for idx in range(len(paragraphs) - 1, max(start_idx, int(len(paragraphs) * 0.65)), -1):
                upper = paragraphs[idx].upper()
                if upper in {"TÀI LIỆU THAM KHẢO", "DANH MỤC TÀI LIỆU THAM KHẢO", "REFERENCES", "BIBLIOGRAPHY"}:
                    end_idx = idx
                    break

            return "\n\n".join(paragraphs[start_idx:end_idx])
        except Exception:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(50000)

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """Split text into complete sentences without breaking on section numbers (1.1.) or decimals (75.0%)."""
        # Normalize whitespace while keeping paragraph breaks as period-hints if needed
        cleaned = re.sub(r"[ \t]+", " ", text)
        cleaned = re.sub(r"\n{2,}", "\n", cleaned).strip()

        # Protect section numbers (e.g. 1.1., 3.2.1.), list numbers (1.), and common abbreviations
        protected = re.sub(r"\b(\d+(?:\.\d+)*)\.(?=\s)", r"\1<DOT>", cleaned)
        protected = re.sub(r"\b(TS|PGS|ThS|GS|KS|CN|VD|STT|Tp|TP)\.", r"\1<DOT>", protected)

        raw_parts = re.split(r"(?<=[.!?])\s+|\n+", protected)
        sentences: List[str] = []
        for part in raw_parts:
            restored = part.replace("<DOT>", ".").strip()
            if not restored:
                continue
            # Ensure sentence-like quality if coming from prose
            sentences.append(restored)
        return sentences

    def chunk_text_sliding_window(self, text: str) -> List[str]:
        """
        Split text into sentence-aligned chunks of ~window_size_words with ~overlap_words overlap.
        Guarantees every chunk begins and ends on a complete sentence boundary.
        """
        sentences = self._split_sentences(text)
        if not sentences:
            return []

        total_words = sum(len(s.split()) for s in sentences)
        if total_words <= self.window_size_words:
            return [" ".join(sentences)]

        chunks: List[str] = []
        idx = 0
        n = len(sentences)

        while idx < n:
            curr_sents: List[str] = []
            curr_words = 0
            j = idx
            while j < n:
                s_words = len(sentences[j].split())
                if curr_sents and curr_words + s_words > self.window_size_words:
                    break
                curr_sents.append(sentences[j])
                curr_words += s_words
                j += 1

            chunks.append(" ".join(curr_sents))
            if j >= n:
                break

            # Step back by complete sentences to achieve ~overlap_words overlap
            overlap_acc = 0
            next_idx = j
            while next_idx > idx + 1 and overlap_acc < self.overlap_words:
                next_idx -= 1
                overlap_acc += len(sentences[next_idx].split())
            idx = max(idx + 1, next_idx)

        return chunks

    @staticmethod
    def _is_well_formed_sentence(sent: str) -> bool:
        """Filter out headings, table fragments, and broken clauses."""
        words = sent.split()
        if len(words) < 8 or len(words) > 65:
            return False
        if not sent[0].isupper():
            return False
        if not sent.endswith((".", "!", "?")):
            return False
        # Reject lines that are mostly numbers/symbols
        alpha_chars = sum(1 for c in sent if c.isalpha())
        if alpha_chars < len(sent) * 0.55:
            return False
        return True

    def summarize_chunk(self, chunk: str, max_words: int = 70) -> str:
        """Summarize an individual sentence-aligned chunk down to complete essential sentences."""
        sentences = [s for s in self._split_sentences(chunk) if self._is_well_formed_sentence(s)]
        if not sentences:
            sentences = self._split_sentences(chunk)
        if len(sentences) <= 2:
            return " ".join(sentences)

        keywords = {
            "kết quả", "phương pháp", "thuật toán", "đề xuất", "kết luận", "mục tiêu",
            "nghiên cứu", "kiến trúc", "mô hình", "dữ liệu", "thực nghiệm", "đánh giá",
            "result", "method", "propose", "conclusion", "objective", "algorithm", "evaluation"
        }
        selected = [sentences[0]]
        used_words = len(sentences[0].split())

        for s in sentences[1:]:
            s_lower = s.lower()
            s_len = len(s.split())
            if any(k in s_lower for k in keywords) and used_words + s_len <= max_words:
                selected.append(s)
                used_words += s_len

        if len(selected) == 1 and len(sentences) > 1:
            last = sentences[-1]
            if used_words + len(last.split()) <= max_words + 15:
                selected.append(last)

        return " ".join(selected)

    def recursive_map_reduce(self, text: str) -> Dict[str, Any]:
        """
        Execute Section-Aware TF-IDF + Sliding-Window Extractive Summarization
        producing clean, complete Vietnamese sentences up to 400 words.
        """
        chunks = self.chunk_text_sliding_window(text)
        if not chunks:
            return {
                "executive_summary": "Tài liệu không có nội dung văn bản đáng kể.",
                "total_chunks": 0,
                "original_word_count": 0,
                "digest_word_count": 0,
            }

        all_sentences = self._split_sentences(text)
        candidates: List[Tuple[int, str]] = [
            (i, s) for i, s in enumerate(all_sentences) if self._is_well_formed_sentence(s)
        ]

        if not candidates:
            # Fallback to chunk summaries if document has non-standard punctuation
            mapped = [self.summarize_chunk(c, max_words=60) for c in chunks[:6]]
            final_digest = "\n".join(f"- {m}" for m in mapped if m)
            return {
                "executive_summary": final_digest,
                "total_chunks": len(chunks),
                "original_word_count": len(text.split()),
                "digest_word_count": len(final_digest.split()),
            }

        # Compute TF-IDF scores across all candidate sentences
        tokenized = [re.findall(r"[a-zA-ZÀ-ỹ0-9_]{2,}", s.lower()) for _, s in candidates]
        n_docs = len(tokenized)
        df: Counter = Counter()
        for toks in tokenized:
            df.update(set(toks))

        cues = (
            "mục tiêu", "đề tài", "nghiên cứu", "đề xuất", "phương pháp", "kiến trúc",
            "mô hình", "thuật toán", "tập dữ liệu", "dữ liệu", "thực nghiệm", "kết quả",
            "f1", "accuracy", "đánh giá", "kết luận", "hạn chế", "khắc phục", "cải thiện"
        )

        scored: List[Tuple[float, int, str]] = []
        for idx, ((orig_pos, sent), toks) in enumerate(zip(candidates, tokenized)):
            tf = Counter(toks)
            tfidf_sum = sum(
                (1 + math.log(freq)) * math.log((n_docs + 1) / (df[w] + 1))
                for w, freq in tf.items()
            )
            norm_score = tfidf_sum / max(1.0, math.sqrt(len(toks)))

            sent_lower = sent.lower()
            cue_bonus = sum(0.35 for cue in cues if cue in sent_lower)

            # Position bonus: boost introduction (first 12%) and conclusion (last 15%)
            rel_pos = orig_pos / max(1, len(all_sentences))
            pos_bonus = 0.6 if rel_pos < 0.12 or rel_pos > 0.85 else 0.0

            scored.append((norm_score + cue_bonus + pos_bonus, orig_pos, sent))

        # Select top sentences across 4 quartiles of the document to guarantee full-report coverage
        quartile_size = max(1, len(all_sentences) // 4)
        selected_items: List[Tuple[int, str]] = []
        used_texts = set()
        word_budget = 0

        for q in range(4):
            q_start = q * quartile_size
            q_end = (q + 1) * quartile_size if q < 3 else len(all_sentences) + 1
            q_cands = sorted(
                [item for item in scored if q_start <= item[1] < q_end],
                key=lambda x: x[0],
                reverse=True,
            )
            picked_in_q = 0
            for _, orig_pos, sent in q_cands:
                if sent in used_texts:
                    continue
                s_words = len(sent.split())
                if word_budget + s_words <= 380 and picked_in_q < 3:
                    selected_items.append((orig_pos, sent))
                    used_texts.add(sent)
                    word_budget += s_words
                    picked_in_q += 1

        # Sort selected sentences back into original document order
        selected_items.sort(key=lambda x: x[0])
        final_digest = "\n".join(f"- {sent}" for _, sent in selected_items)

        return {
            "executive_summary": final_digest,
            "total_chunks": len(chunks),
            "original_word_count": len(text.split()),
            "digest_word_count": len(final_digest.split()),
        }

    async def summarize_with_llm_or_fallback(self, text: str, doc_label: str = "Tài liệu") -> Dict[str, Any]:
        """
        Try structured abstractive summarization via Gemini Flash when available;
        fall back seamlessly to Section-Aware TF-IDF extractive summarization.
        """
        base_res = self.recursive_map_reduce(text)
        if settings.AI_PROVIDER == "gemini" and settings.GEMINI_API_KEY and len(text.split()) > 60:
            # Feed clean extracted body (up to ~18,000 chars) or structured extractive digest
            excerpt = text[:18000] if len(text) <= 22000 else (
                text[:6000] + "\n...\n" + base_res["executive_summary"] + "\n...\n" + text[-5000:]
            )
            prompt = (
                f"Hãy đọc nội dung tài liệu học thuật '{doc_label}' dưới đây và viết bản tóm tắt "
                "cô đọng bằng tiếng Việt (khoảng 250-350 từ) theo đúng 4 mục sau:\n"
                "1. Mục tiêu & Bài toán đặt ra\n"
                "2. Phương pháp, Kiến trúc & Thuật toán đề xuất\n"
                "3. Dữ liệu & Thiết lập thực nghiệm\n"
                "4. Kết quả chính, Hạn chế & Kết luận\n"
                "Yêu cầu: Chỉ nêu thông tin có thật trong văn bản, giữ nguyên tên mô hình/bộ dữ liệu/chỉ số.\n\n"
                f"=== NỘI DUNG TÀI LIỆU ===\n{excerpt}"
            )
            summary_text = await self._call_gemini_text(prompt)
            if summary_text and len(summary_text.split()) >= 60:
                return {
                    "executive_summary": summary_text.strip(),
                    "total_chunks": base_res["total_chunks"],
                    "original_word_count": base_res["original_word_count"],
                    "digest_word_count": len(summary_text.split()),
                    "summarizer_mode": "gemini_abstractive",
                }

        base_res["summarizer_mode"] = "section_tfidf_extractive"
        return base_res

    @staticmethod
    async def _call_gemini_text(prompt: str) -> Optional[str]:
        """Call Gemini API for abstractive summarization with fast failover."""
        models = [settings.GEMINI_MODEL, "gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-flash-latest"]
        models_to_try = list(dict.fromkeys([m for m in models if m]))
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "thinkingConfig": {"thinkingBudget": 0}},
        }
        async with httpx.AsyncClient(timeout=12.0) as client:
            for model_name in models_to_try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={settings.GEMINI_API_KEY}"
                try:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        cands = resp.json().get("candidates", [])
                        if cands:
                            return cands[0]["content"]["parts"][0]["text"]
                except Exception:
                    continue
        return None
