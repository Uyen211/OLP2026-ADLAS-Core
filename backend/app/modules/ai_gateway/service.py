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
1. Formulate probing questions directly on the core substance, key decisions, methodologies, and findings presented in the student's submitted work ('{proj_str}') and the provided digest.
2. Inquire into their declared AI assistance: ask how they verified, tested, or understood parts where AI was used versus parts they developed themselves.
3. Output language: Each question ('question_text') must be written in clear, natural, academic Vietnamese (Tiếng Việt).
4. Output format: Return strictly a valid JSON array of {question_count} objects without markdown code fences or additional commentary:
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
        """Call Gemini API directly with thinkingBudget=0, retry with exponential backoff on 503/429."""
        candidate_models = [self.gemini_model, "gemini-3-flash-preview", "gemini-3.1-flash-lite-preview"]
        models_to_try = list(dict.fromkeys([m for m in candidate_models if m]))

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "responseMimeType": "application/json",
                "thinkingConfig": {"thinkingBudget": 0}
            }
        }

        async with httpx.AsyncClient(timeout=35.0) as client:
            for model_name in models_to_try:
                for attempt in range(3):
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
                            if isinstance(parsed, list) and len(parsed) >= expected_count:
                                logger.info("Successfully generated Viva questions using %s", model_name)
                                return parsed[:expected_count]
                        elif resp.status_code in (503, 429):
                            logger.warning(
                                "Gemini model %s returned %d (attempt %d/3), backing off...",
                                model_name, resp.status_code, attempt + 1
                            )
                            await asyncio.sleep(1.5 * (attempt + 1))
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
                if isinstance(parsed, list) and len(parsed) == expected_count:
                    return parsed
        return None

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
        """Generate tailored questions grounded in the student project title, methodology, and AI disclosure."""
        self_pct = ai_disclosure.get("self_contribution_pct", 100)
        tools = ", ".join(ai_disclosure.get("tools_used", [])) or "công cụ hỗ trợ"
        ai_desc = ai_disclosure.get("usage_description", "").strip()
        proj_str = project_title.strip() if project_title else assignment_title

        candidates = [
            (
                "CORE_METHODOLOGY",
                f"Trong đề tài '{proj_str}', hãy giải thích phương pháp cốt lõi hoặc giải pháp kỹ thuật then chốt mà bạn đã lựa chọn để giải quyết bài toán đặt ra, và lý do bạn lựa chọn giải pháp này?"
            ),
            (
                "VALIDATION_EVALUATION",
                f"Để đánh giá hiệu quả thực tế của đề tài '{proj_str}', bạn đã dựa vào bộ dữ liệu, chỉ số hoặc phương pháp kiểm chứng cụ thể nào? Kết quả đạt được phản ánh những ưu điểm và hạn chế gì?"
            ),
            (
                "AI_MASTERY",
                f"Bạn khai báo tự làm {self_pct}% và có sử dụng {tools} ({ai_desc[:80] if ai_desc else 'hỗ trợ'}). Bạn đã kiểm chứng phần kết quả hoặc mã nguồn do AI gợi ý như thế nào để đảm bảo tính chuẩn xác và tin cậy?"
            ),
            (
                "TRADE_OFFS_LIMITATIONS",
                f"Đâu là khó khăn kỹ thuật hoặc hạn chế lớn nhất mà bạn gặp phải khi thực hiện đề tài '{proj_str}', và bạn đã cân nhắc đánh đổi (trade-offs) những yếu tố nào trong thiết kế của mình?"
            ),
            (
                "PRACTICAL_EXPANSION",
                f"Nếu cần nâng cấp hoặc triển khai đề tài '{proj_str}' vào môi trường thực tế với quy mô dữ liệu lớn hơn, đâu là những điểm nghẽn bạn dự kiến sẽ gặp và hướng khắc phục tiếp theo?"
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
