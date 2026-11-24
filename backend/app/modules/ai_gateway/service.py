# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""AI Gateway Service coordinating local and cloud LLM inference for Viva defense generation."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class AIGatewayService:
    """Gateway coordinating LLM generation with fallback for Viva questions and evaluation."""

    def __init__(self):
        self.provider = settings.AI_PROVIDER
        self.gemini_key = settings.GEMINI_API_KEY
        self.gemini_model = settings.GEMINI_MODEL
        self.ollama_url = settings.OLLAMA_BASE_URL
        self.ollama_model = settings.OLLAMA_MODEL_CODE

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
        Generate N adaptive Viva defense questions based on actual student submission digest.
        Uses Gemini Flash API or Ollama Local, falling back to dynamic content-grounded generator.
        """
        prompt = self._build_viva_prompt(
            course_name=course_name,
            assignment_title=assignment_title,
            project_title=project_title,
            digest_type=digest_type,
            digest_content=digest_content,
            ai_disclosure=ai_disclosure,
            question_count=question_count
        )

        # 1. Try Gemini Cloud if configured
        if self.provider == "gemini" and self.gemini_key:
            try:
                questions = await self._call_gemini_json(prompt, question_count)
                if questions and len(questions) >= question_count:
                    return questions[:question_count]
            except Exception as exc:
                logger.warning("Gemini generation failed (%s), falling back to Ollama/deterministic", exc)

        # 2. Try Ollama Local if configured
        if self.provider == "ollama" or not self.gemini_key:
            try:
                questions = await self._call_ollama_json(prompt, question_count)
                if questions and len(questions) >= question_count:
                    return questions[:question_count]
            except Exception as exc:
                logger.info("Ollama offline (%s), falling back to deterministic generator", exc)

        # 3. Dynamic Content-Grounded Generator (Guarantees zero-failure offline operation)
        return self._generate_deterministic_questions(
            course_name=course_name,
            assignment_title=assignment_title,
            project_title=project_title,
            digest_type=digest_type,
            digest_content=digest_content,
            ai_disclosure=ai_disclosure,
            question_count=question_count
        )

    def _build_viva_prompt(
        self,
        course_name: str,
        assignment_title: str,
        project_title: str,
        digest_type: str,
        digest_content: str,
        ai_disclosure: Dict[str, Any],
        question_count: int
    ) -> str:
        self_pct = ai_disclosure.get("self_contribution_pct", 100)
        tools = ", ".join(ai_disclosure.get("tools_used", [])) or "None reported"
        desc = ai_disclosure.get("usage_description", "None provided")
        proj_str = project_title.strip() if project_title else assignment_title
        c_name = course_name.strip() if course_name else "University Course"

        return f"""You are a university oral defense examiner conducting a defense session for a student's project submission.
Your goal is to evaluate the student's actual understanding and the core substance of their submitted work.

=== SUBMISSION DETAILS ===
- Course: {c_name}
- Assignment: {assignment_title}
- Student Project Title: {proj_str}

=== STUDENT'S DECLARED WORK & AI USAGE ===
- Self-contribution: {self_pct}%
- AI Tools: {tools}
- Student's notes on AI usage: {desc}

=== SUBMISSION CONTENT DIGEST ===
{digest_content[:4000]}

=== INSTRUCTIONS ===
1. Every question MUST cite specific entities from SUBMISSION CONTENT DIGEST (e.g., exact file names, module/function names, algorithms, datasets, metrics, or architectural choices).
2. Generic questions that could apply to any arbitrary project without reading the digest are STRICTLY FORBIDDEN.
3. Include at least one question probing their declared AI usage ({self_pct}% self-work, tools: {tools}) in relation to a specific part of their submitted work.
4. Output language: Each question ('question_text') must be written in clear, natural, academic Vietnamese.
5. Output format: Return strictly a valid JSON array of {question_count} objects without markdown code fences or additional commentary:
[
  {{
    "id": "q1",
    "question_index": 1,
    "total_questions": {question_count},
    "question_text": "...",
    "category": "DEFENSE"
  }}
]
"""

    async def _call_gemini_json(self, prompt: str, expected_count: int) -> Optional[List[Dict[str, Any]]]:
        """Call Gemini API directly with thinkingBudget=0, fast retry on 503/429."""
        candidate_models = [self.gemini_model, "gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-flash-latest"]
        models_to_try = list(dict.fromkeys([m for m in candidate_models if m]))

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "responseMimeType": "application/json",
                "thinkingConfig": {"thinkingBudget": 0}
            }
        }

        async with httpx.AsyncClient(timeout=12.0) as client:
            for model_name in models_to_try:
                for attempt in range(2):
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.gemini_key}"
                    try:
                        resp = await client.post(url, json=payload)
                        if resp.status_code == 200:
                            data = resp.json()
                            candidates = data.get("candidates", [])
                            if not candidates:
                                break
                            raw_text = candidates[0]["content"]["parts"][0]["text"].strip()
                            if raw_text.startswith("```json"):
                                raw_text = raw_text[7:]
                            if raw_text.startswith("```"):
                                raw_text = raw_text[3:]
                            if raw_text.endswith("```"):
                                raw_text = raw_text[:-3]
                            parsed = json.loads(raw_text.strip())
                            normalized = self._normalize_questions(parsed, expected_count)
                            if normalized:
                                logger.info("Successfully generated Viva questions using %s", model_name)
                                return normalized
                        elif resp.status_code in (503, 429):
                            logger.warning(
                                "Gemini model %s returned %d (attempt %d/2), backing off...",
                                model_name, resp.status_code, attempt + 1
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

    async def _call_ollama_json(self, prompt: str, expected_count: int) -> Optional[List[Dict[str, Any]]]:
        """Call Ollama local server."""
        url = f"{self.ollama_url}/api/generate"
        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.2}
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                raw_text = resp.json().get("response", "")
                parsed = json.loads(raw_text)
                normalized = self._normalize_questions(parsed, expected_count)
                if normalized:
                    return normalized
        return None

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
        question_count: int
    ) -> List[Dict[str, Any]]:
        """Generate content-grounded fallback questions extracting real anchors from the submission digest."""
        import re

        self_pct = ai_disclosure.get("self_contribution_pct", 100)
        tools = ", ".join(ai_disclosure.get("tools_used", [])) or "công cụ hỗ trợ"
        ai_desc = ai_disclosure.get("usage_description", "").strip()
        proj_str = project_title.strip() if project_title else assignment_title

        # Extract concrete anchors from digest_content (files for CODE, key terms/lines for DOCUMENT)
        file_refs = re.findall(r"[\w./-]+\.(?:py|ts|tsx|js|mjs|sql|java|cpp|go)", digest_content or "")
        unique_files = list(dict.fromkeys(file_refs))[:3]
        file_hint = ", ".join(unique_files) if unique_files else "các mô-đun chính trong bài nộp"

        doc_lines = [ln.lstrip("- ").strip() for ln in (digest_content or "").splitlines() if len(ln.strip()) > 30]
        anchor_1 = doc_lines[0][:140] if len(doc_lines) > 0 else ""
        anchor_2 = doc_lines[min(2, len(doc_lines) - 1)][:140] if len(doc_lines) > 1 else ""

        if digest_type == "CODE":
            candidates = [
                (
                    "ARCHITECTURE_CODE",
                    f"Trong mã nguồn của đề tài '{proj_str}' (cụ thể tại {file_hint}), hãy giải thích luồng xử lý chính và lý do bạn tổ chức cấu trúc các thành phần như vậy?"
                ),
                (
                    "EDGE_CASE_TESTING",
                    f"Khi triển khai xử lý dữ liệu và ngoại lệ trong {file_hint}, bạn đã kiểm thử những tình huống biên (edge cases) nào để đảm bảo hệ thống không gặp lỗi?"
                ),
                (
                    "AI_MASTERY",
                    f"Bạn khai báo tự làm {self_pct}% và có sử dụng {tools} ({ai_desc[:80] if ai_desc else 'hỗ trợ'}). Bạn đã rà soát và kiểm chứng tính đúng đắn của phần mã nguồn do AI gợi ý như thế nào?"
                ),
                (
                    "TRADE_OFFS_LIMITATIONS",
                    f"Đâu là điểm nghẽn hoặc đánh đổi kỹ thuật (trade-offs) lớn nhất trong thiết kế hiện tại của '{proj_str}' và hướng cải tiến tiếp theo?"
                ),
            ]
        else:
            a1_part = f' (trích: "{anchor_1}...")' if anchor_1 else ""
            a2_part = f' (liên quan: "{anchor_2}...")' if anchor_2 else ""
            candidates = [
                (
                    "CORE_METHODOLOGY",
                    f"Dựa trên nội dung báo cáo '{proj_str}'{a1_part}, hãy giải thích cơ sở phương pháp luận bạn đã lựa chọn và ưu thế so với các hướng tiếp cận khác?"
                ),
                (
                    "VALIDATION_EVALUATION",
                    f"Trong phần thực nghiệm của đề tài '{proj_str}'{a2_part}, bạn đã sử dụng bộ dữ liệu và chỉ số đánh giá nào để chứng minh hiệu quả?"
                ),
                (
                    "AI_MASTERY",
                    f"Bạn khai báo tự làm {self_pct}% và có sử dụng {tools} ({ai_desc[:80] if ai_desc else 'hỗ trợ'}). Bạn đã kiểm chứng tính xác thực của nội dung/công thức do AI hỗ trợ như thế nào?"
                ),
                (
                    "LIMITATIONS",
                    f"Những hạn chế hoặc sai số thực nghiệm nào còn tồn tại trong nghiên cứu '{proj_str}' và bạn đề xuất hướng khắc phục gì?"
                ),
            ]

        questions = []
        for i in range(question_count):
            cat, text = candidates[i % len(candidates)]
            questions.append({
                "id": f"q{i+1}",
                "question_index": i + 1,
                "total_questions": question_count,
                "question_text": text,
                "category": cat
            })

        return questions
