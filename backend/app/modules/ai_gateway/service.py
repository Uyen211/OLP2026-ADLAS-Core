# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""AI Gateway Service orchestrating Gemini Long-Context 2-Call Summarization and Viva Generation."""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import httpx
from app.core.config import settings
from app.modules.assessment.ingestion.document_summarizer import (
    MAX_SINGLE_CALL_WORDS,
    DocumentSummarizer,
)

logger = logging.getLogger(__name__)


class AIGatewayService:
    """Gateway coordinating Gemini 2-Call pipeline (Summarize -> Viva Questions) with deterministic fallback."""

    def __init__(self):
        self.provider = settings.AI_PROVIDER
        self.gemini_key = settings.GEMINI_API_KEY
        self.gemini_model = settings.GEMINI_MODEL
        self.last_generation_source: str = "deterministic_fallback"

    def _candidate_models(self) -> List[str]:
        candidates = [
            self.gemini_model,
            "gemini-3.6-flash",
            "gemini-flash-lite-latest",
            "gemini-3-flash-preview",
        ]
        return list(dict.fromkeys([m for m in candidates if m]))

    async def _call_gemini_raw(
        self,
        prompt: str,
        response_mime_type: Optional[str] = None,
        temperature: float = 0.2,
    ) -> Optional[str]:
        """Call Gemini REST API with automatic model failover and backoff on 503/429."""
        if self.provider != "gemini" or not self.gemini_key:
            return None

        gen_config: Dict[str, Any] = {
            "temperature": temperature,
            "thinkingConfig": {"thinkingBudget": 0},
        }
        if response_mime_type:
            gen_config["responseMimeType"] = response_mime_type

        async with httpx.AsyncClient(timeout=40.0) as client:
            for model_name in self._candidate_models():
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": dict(gen_config),
                }
                for attempt in range(2):
                    url = (
                        f"https://generativelanguage.googleapis.com/v1beta/models/"
                        f"{model_name}:generateContent?key={self.gemini_key}"
                    )
                    try:
                        resp = await client.post(url, json=payload)
                        if resp.status_code == 200:
                            candidates = resp.json().get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                if parts and parts[0].get("text"):
                                    logger.info("Gemini call succeeded with model %s", model_name)
                                    return parts[0]["text"].strip()
                            break
                        elif resp.status_code == 400 and "thinkingConfig" in payload["generationConfig"]:
                            # Some lite models reject thinkingConfig; retry once without it
                            payload["generationConfig"].pop("thinkingConfig", None)
                            continue
                        elif resp.status_code in (503, 429):
                            logger.warning(
                                "Gemini model %s returned %d (attempt %d/2), backing off...",
                                model_name,
                                resp.status_code,
                                attempt + 1,
                            )
                            await asyncio.sleep(0.8 * (attempt + 1))
                            continue
                        else:
                            logger.warning("Gemini model %s returned status %d", model_name, resp.status_code)
                            break
                    except Exception as exc:
                        logger.warning("Gemini model %s call failed: %s", model_name, exc)
                        break
        return None

    async def summarize_submission(
        self,
        digest_type: str,
        raw_content: str,
        project_title: str = "",
        assignment_title: str = "",
    ) -> Tuple[str, str]:
        """
        Gemini Call 1: Summarize full cleaned document or Repomix AST XML into a structured
        <= 500-word executive summary using Long-Context best practices (XML tags + trailing instructions).
        Returns (summary_text, summarizer_mode).
        """
        if not raw_content or not raw_content.strip():
            return ("Bài nộp không có nội dung văn bản hoặc mã nguồn đọc được.", "empty_fallback")

        title_hint = project_title.strip() or assignment_title.strip() or "Bài nộp đồ án"

        if digest_type == "CODE":
            prompt = (
                f"<repository>\n{raw_content}\n</repository>\n\n"
                f"=== CHỈ DẪN TÓM TẮT MÃ NGUỒN ({title_hint}) ===\n"
                "Hãy đọc cấu trúc thư mục và mã nguồn AST ở trên, viết một bản tóm tắt kỹ thuật bằng tiếng Việt "
                "(tối đa 500 từ) theo đúng 4 mục sau:\n"
                "1. Kiến trúc tổng thể & các module chính (nêu rõ tên file/thư mục quan trọng).\n"
                "2. Luồng xử lý nghiệp vụ cốt lõi, thuật toán hoặc cơ chế kỹ thuật chính.\n"
                "3. Mô hình dữ liệu, API endpoint hoặc tương tác giữa các tầng.\n"
                "4. Điểm cần kiểm chứng về xử lý ngoại lệ, bảo mật hoặc hiệu năng.\n"
                "Yêu cầu: Chỉ nêu tên file, hàm, lớp có thật trong thẻ <repository> ở trên."
            )
            res = await self._call_gemini_raw(prompt, temperature=0.2)
            if res:
                return (res, "gemini_long_context")
            return (raw_content[:3000], "offline_excerpt")

        # DOCUMENT flow
        word_count = len(raw_content.split())
        if word_count <= MAX_SINGLE_CALL_WORDS:
            prompt = (
                f"<document>\n{raw_content}\n</document>\n\n"
                f"=== CHỈ DẪN TÓM TẮT TÀI LIỆU ({title_hint}) ===\n"
                "Hãy đọc toàn bộ tài liệu trong thẻ <document> ở trên và viết một bản tóm tắt học thuật "
                "bằng tiếng Việt (khoảng 350-500 từ) theo đúng 4 mục sau:\n"
                "1. Bài toán & Mục tiêu chính.\n"
                "2. Phương pháp, giải pháp hoặc mô hình do CHÍNH TÁC GIẢ đề xuất và thực hiện "
                "(tách bạch rõ với phần điểm lại nghiên cứu của các tác giả khác).\n"
                "3. Dữ liệu, công cụ, quy trình hoặc thiết lập thực nghiệm.\n"
                "4. Kết quả chính đạt được, đóng góp mới và hạn chế.\n"
                "Yêu cầu: Chỉ dùng thông tin có thật trong <document>, giữ nguyên tên mô hình, bộ dữ liệu và số liệu thực nghiệm."
            )
            res = await self._call_gemini_raw(prompt, temperature=0.2)
            if res:
                return (res, "gemini_long_context")
        else:
            # Oversized document (> 45,000 words): split into large paragraph blocks, summarize each, then combine
            chunks = DocumentSummarizer.split_large_text_by_paragraphs(raw_content, max_words=20000)
            part_summaries: List[str] = []
            for idx, chunk in enumerate(chunks, start=1):
                p_prompt = (
                    f"<document_part index=\"{idx}\" total=\"{len(chunks)}\">\n{chunk}\n</document_part>\n\n"
                    f"Hãy tóm tắt các nội dung chính, phương pháp, dữ liệu và kết quả trong phần {idx}/{len(chunks)} "
                    f"của tài liệu '{title_hint}' (tối đa 250 từ bằng tiếng Việt)."
                )
                part_res = await self._call_gemini_raw(p_prompt, temperature=0.2)
                if part_res:
                    part_summaries.append(part_res)
            if part_summaries:
                merged = "\n\n".join(part_summaries)
                reduce_prompt = (
                    f"<part_summaries>\n{merged}\n</part_summaries>\n\n"
                    f"Hãy hợp nhất các phần tóm tắt trên của '{title_hint}' thành một bản tóm tắt thống nhất "
                    "(350-500 từ tiếng Việt) gồm 4 mục: (1) Bài toán & Mục tiêu, (2) Phương pháp tác giả thực hiện, "
                    "(3) Dữ liệu & Thực nghiệm, (4) Kết quả & Hạn chế."
                )
                final_res = await self._call_gemini_raw(reduce_prompt, temperature=0.2)
                if final_res:
                    return (final_res, "gemini_long_context")

        return (DocumentSummarizer.build_offline_excerpt(raw_content, max_words=500), "offline_excerpt")

    async def generate_viva_questions(
        self,
        assignment_title: str,
        assignment_instructions: str,
        digest_type: str,
        digest_content: str,
        ai_disclosure: Dict[str, Any],
        question_count: int = 3,
        course_name: str = "",
        project_title: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Gemini Call 2: Generate N adaptive Viva defense questions from the Call-1 summary.
        Sets self.last_generation_source to 'gemini_live' or 'deterministic_fallback'.
        """
        prompt = self._build_viva_prompt(
            course_name=course_name,
            assignment_title=assignment_title,
            project_title=project_title,
            digest_type=digest_type,
            digest_content=digest_content,
            ai_disclosure=ai_disclosure,
            question_count=question_count,
        )

        raw_text = await self._call_gemini_raw(
            prompt,
            response_mime_type="application/json",
            temperature=0.3,
        )
        if raw_text:
            cleaned = raw_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            try:
                parsed = json.loads(cleaned.strip())
                normalized = self._normalize_questions(parsed, question_count)
                if normalized:
                    self.last_generation_source = "gemini_live"
                    return normalized
            except Exception as exc:
                logger.warning("Failed to parse Gemini Viva JSON (%s)", exc)

        self.last_generation_source = "deterministic_fallback"
        return self._generate_deterministic_questions(
            course_name=course_name,
            assignment_title=assignment_title,
            project_title=project_title,
            digest_type=digest_type,
            digest_content=digest_content,
            ai_disclosure=ai_disclosure,
            question_count=question_count,
        )

    def _build_viva_prompt(
        self,
        course_name: str,
        assignment_title: str,
        project_title: str,
        digest_type: str,
        digest_content: str,
        ai_disclosure: Dict[str, Any],
        question_count: int,
    ) -> str:
        self_pct = ai_disclosure.get("self_contribution_pct", 100)
        tools = ", ".join(ai_disclosure.get("tools_used", [])) or "None reported"
        desc = ai_disclosure.get("usage_description", "None provided")
        proj_str = project_title.strip() if project_title else assignment_title
        c_name = course_name.strip() if course_name else "University Course"

        return f"""<submission_summary>
- Course: {c_name}
- Assignment: {assignment_title}
- Student Project Title: {proj_str}
- Submission Type: {digest_type}
- AI Disclosure: {self_pct}% self-work | Tools: {tools} | Notes: {desc}

{digest_content}
</submission_summary>

=== INSTRUCTIONS ===
You are a strict university oral defense examiner. Based ONLY on <submission_summary> above, formulate {question_count} probing oral defense questions in natural, academic Vietnamese:
1. Every question MUST reference specific file names, classes/functions, methodologies, datasets, or experimental metrics from <submission_summary>. Generic questions that could apply to any project are STRICTLY FORBIDDEN.
2. Focus on the student's own design decisions, implementation trade-offs, edge cases, and result validation (do NOT ask generic literature-review recall questions).
3. Include at least 1 question verifying how the student tested or validated the parts where AI ({tools}) assisted.
4. Return strictly a valid JSON array of {question_count} objects without markdown fences:
[
  {{
    "id": "q1",
    "question_index": 1,
    "total_questions": {question_count},
    "question_text": "...",
    "category": "DEFENSE"
  }}
]"""

    @staticmethod
    def _normalize_questions(raw: Any, expected_count: int) -> Optional[List[Dict[str, Any]]]:
        """Validate and normalize LLM JSON output to guarantee VivaQuestionSchema compliance."""
        if not isinstance(raw, list) or len(raw) < expected_count:
            return None
        normalized: List[Dict[str, Any]] = []
        for idx, item in enumerate(raw[:expected_count]):
            if not isinstance(item, dict):
                return None
            text = str(item.get("question_text") or item.get("question") or "").strip()
            if not text:
                return None
            normalized.append({
                "id": str(item.get("id") or f"q{idx + 1}"),
                "question_index": idx + 1,
                "total_questions": expected_count,
                "question_text": text,
                "category": str(item.get("category") or "DEFENSE"),
            })
        return normalized

    def _generate_deterministic_questions(
        self,
        course_name: str,
        assignment_title: str,
        project_title: str,
        digest_type: str,
        digest_content: str,
        ai_disclosure: Dict[str, Any],
        question_count: int,
    ) -> List[Dict[str, Any]]:
        """Last-resort offline fallback when Gemini API is completely unreachable."""
        self_pct = ai_disclosure.get("self_contribution_pct", 100)
        tools = ", ".join(ai_disclosure.get("tools_used", [])) or "công cụ hỗ trợ"
        ai_desc = ai_disclosure.get("usage_description", "").strip()
        proj_str = project_title.strip() if project_title else assignment_title

        file_refs = re.findall(r"[\w./-]+\.(?:py|ts|tsx|js|mjs|sql|java|cpp|go)", digest_content or "")
        unique_files = list(dict.fromkeys(file_refs))[:3]
        file_hint = ", ".join(unique_files) if unique_files else "các mô-đun chính trong bài nộp"

        if digest_type == "CODE":
            candidates = [
                (
                    "ARCHITECTURE_CODE",
                    f"Trong mã nguồn của đề tài '{proj_str}' (tại {file_hint}), hãy giải thích luồng xử lý chính và lý do bạn tổ chức cấu trúc các thành phần như vậy?",
                ),
                (
                    "EDGE_CASE_TESTING",
                    f"Khi triển khai xử lý dữ liệu và ngoại lệ trong {file_hint}, bạn đã kiểm thử những tình huống biên (edge cases) nào?",
                ),
                (
                    "AI_MASTERY",
                    f"Bạn khai báo tự làm {self_pct}% và có sử dụng {tools} ({ai_desc[:80] if ai_desc else 'hỗ trợ'}). Bạn đã kiểm chứng tính đúng đắn của phần mã nguồn do AI gợi ý như thế nào?",
                ),
                (
                    "TRADE_OFFS_LIMITATIONS",
                    f"Đâu là điểm nghẽn hoặc đánh đổi kỹ thuật lớn nhất trong thiết kế hiện tại của '{proj_str}'?",
                ),
            ]
        else:
            candidates = [
                (
                    "CORE_METHODOLOGY",
                    f"Trong đề tài '{proj_str}', hãy giải thích phương pháp hoặc giải pháp trọng tâm mà bạn đã lựa chọn và ưu thế so với các hướng tiếp cận khác?",
                ),
                (
                    "VALIDATION_EVALUATION",
                    f"Để đánh giá hiệu quả thực tế của '{proj_str}', bạn đã sử dụng dữ liệu, minh chứng và chỉ số đánh giá cụ thể nào?",
                ),
                (
                    "AI_MASTERY",
                    f"Bạn khai báo tự làm {self_pct}% và có sử dụng {tools} ({ai_desc[:80] if ai_desc else 'hỗ trợ'}). Bạn đã kiểm chứng tính xác thực của nội dung do AI hỗ trợ như thế nào?",
                ),
                (
                    "LIMITATIONS",
                    f"Những hạn chế hoặc sai số nào còn tồn tại trong nghiên cứu '{proj_str}' và hướng khắc phục của bạn?",
                ),
            ]

        questions = []
        for i in range(question_count):
            cat, text = candidates[i % len(candidates)]
            questions.append({
                "id": f"q{i + 1}",
                "question_index": i + 1,
                "total_questions": question_count,
                "question_text": text,
                "category": cat,
            })
        return questions
