# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Unit tests for AIGatewayService 2-Call Long-Context Summarization and Viva Generation."""

import json
from unittest.mock import AsyncMock, patch
import pytest
from app.modules.ai_gateway.service import AIGatewayService


@pytest.mark.asyncio
async def test_ai_gateway_two_call_live_pipeline():
    ai = AIGatewayService()
    ai.gemini_key = "test-key"

    mock_summary = (
        "1. Bài toán: Nhận dạng thực thể y sinh BioNER.\n"
        "2. Phương pháp: Mô hình ViPubmedDeBERTa kết hợp Active Learning.\n"
        "3. Dữ liệu: VietBioNER.\n"
        "4. Kết quả: F1 đạt 82.5%."
    )
    mock_questions = json.dumps([
        {"id": "q1", "question_index": 1, "total_questions": 2, "question_text": "Tại sao chọn ViPubmedDeBERTa?", "category": "DEFENSE"},
        {"id": "q2", "question_index": 2, "total_questions": 2, "question_text": "Bạn kiểm chứng code AI hỗ trợ ra sao?", "category": "AI_MASTERY"},
    ])

    with patch.object(ai, "_call_gemini_raw", new=AsyncMock(side_effect=[mock_summary, mock_questions])):
        summary, mode = await ai.summarize_submission(
            digest_type="DOCUMENT",
            raw_content="Nội dung báo cáo nghiên cứu đầy đủ...",
            project_title="VietBioNER",
        )
        assert mode == "gemini_long_context"
        assert "ViPubmedDeBERTa" in summary

        questions = await ai.generate_viva_questions(
            assignment_title="BTL NLP",
            assignment_instructions="Xây dựng hệ thống BioNER",
            digest_type="DOCUMENT",
            digest_content=summary,
            ai_disclosure={"self_contribution_pct": 85, "tools_used": ["ChatGPT"], "usage_description": "Kiểm tra ngữ pháp và giải thích công thức."},
            question_count=2,
            project_title="VietBioNER",
        )
        assert ai.last_generation_source == "gemini_live"
        assert len(questions) == 2
        assert "ViPubmedDeBERTa" in questions[0]["question_text"]


@pytest.mark.asyncio
async def test_ai_gateway_fallback_marks_deterministic_source():
    ai = AIGatewayService()
    ai.gemini_key = "test-key"

    with patch.object(ai, "_call_gemini_raw", new=AsyncMock(return_value=None)):
        summary, mode = await ai.summarize_submission(
            digest_type="CODE",
            raw_content='<file path="backend/app/modules/assessment/service.py">def create_submission(): pass</file>',
            project_title="ADLAS",
        )
        assert mode == "offline_excerpt"

        questions = await ai.generate_viva_questions(
            assignment_title="Đồ án",
            assignment_instructions="Build backend",
            digest_type="CODE",
            digest_content=summary,
            ai_disclosure={"self_contribution_pct": 80, "tools_used": ["Copilot"], "usage_description": "Sinh unit test."},
            question_count=3,
            project_title="ADLAS",
        )
        assert ai.last_generation_source == "deterministic_fallback"
        assert len(questions) == 3
        assert "service.py" in questions[0]["question_text"]
