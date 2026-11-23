# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Unit tests for Viva Sandbox examination sessions, paste-lock, blur bẫy, and word counts."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest
from app.modules.assessment.exceptions import (
    VivaAnswerWordCountException,
)
from app.modules.assessment.models import AssignmentSubmission, VivaTranscript
from app.modules.assessment.schemas import VivaAnswerSubmitRequest
from app.modules.assessment.viva_service import VivaSandboxService


@pytest.mark.asyncio
async def test_viva_start_session_duration_calculation():
    service = VivaSandboxService()
    user_id = uuid.uuid4()
    submission_id = uuid.uuid4()

    # Dynamic N = 4 questions -> 4 x 300s = 1200 seconds (20 minutes)
    qa_payload = {
        "total_questions": 4,
        "current_index": 1,
        "questions": [
            {"id": "q1", "question_index": 1, "total_questions": 4, "question_text": "Giải thích cấu trúc dữ liệu?", "category": "ALGORITHM"},
            {"id": "q2", "question_index": 2, "total_questions": 4, "question_text": "Xử lý tình huống biên?", "category": "EDGE_CASE"},
            {"id": "q3", "question_index": 3, "total_questions": 4, "question_text": "Giải trình phần dùng AI?", "category": "INTEGRITY"},
            {"id": "q4", "question_index": 4, "total_questions": 4, "question_text": "Đánh giá hiệu năng?", "category": "PERFORMANCE"}
        ],
        "answers": {}
    }

    mock_sub = AssignmentSubmission(id=submission_id, user_id=user_id, status="PENDING_VIVA")
    mock_transcript = VivaTranscript(
        id=uuid.uuid4(),
        submission_id=submission_id,
        questions_answers=qa_payload,
        violation_logs=[],
        started_at=datetime.now(timezone.utc),
        status="READY"
    )
    mock_transcript.submission = mock_sub

    db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_transcript
    db.execute.return_value = mock_res

    res = await service.start_session(db=db, submission_id=submission_id, user_id=user_id)

    assert res.total_questions == 4
    assert res.total_duration_seconds == 1200
    assert res.current_question_index == 1
    assert res.question.id == "q1"
    assert mock_transcript.status == "IN_PROGRESS"


@pytest.mark.asyncio
async def test_viva_answer_enforces_minimum_50_words():
    service = VivaSandboxService()
    user_id = uuid.uuid4()
    submission_id = uuid.uuid4()

    mock_sub = AssignmentSubmission(id=submission_id, user_id=user_id, status="IN_VIVA")
    mock_transcript = VivaTranscript(
        id=uuid.uuid4(),
        submission_id=submission_id,
        questions_answers={"total_questions": 2, "current_index": 1, "questions": [{"id": "q1", "question_index": 1, "total_questions": 2, "question_text": "Test?", "category": "TEST"}], "answers": {}},
        violation_logs=[],
        started_at=datetime.now(timezone.utc),
        status="IN_PROGRESS"
    )
    mock_transcript.submission = mock_sub

    db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_transcript
    db.execute.return_value = mock_res

    # Answer with only 10 words -> should raise VivaAnswerWordCountException (E-1)
    short_payload = VivaAnswerSubmitRequest(
        question_id="q1",
        answer_text="Đây là câu trả lời quá ngắn không đủ năm mươi từ."
    )

    with pytest.raises(VivaAnswerWordCountException) as exc_info:
        await service.submit_answer(db=db, submission_id=submission_id, user_id=user_id, payload=short_payload)

    assert exc_info.value.status_code == 400
    assert "E-1" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_viva_sequential_answers_and_final_completion():
    service = VivaSandboxService()
    user_id = uuid.uuid4()
    submission_id = uuid.uuid4()

    q1 = {"id": "q1", "question_index": 1, "total_questions": 2, "question_text": "Câu hỏi 1?", "category": "ALGORITHM"}
    q2 = {"id": "q2", "question_index": 2, "total_questions": 2, "question_text": "Câu hỏi 2?", "category": "INTEGRITY"}

    mock_sub = AssignmentSubmission(id=submission_id, user_id=user_id, status="IN_VIVA")
    mock_transcript = VivaTranscript(
        id=uuid.uuid4(),
        submission_id=submission_id,
        questions_answers={"total_questions": 2, "current_index": 1, "questions": [q1, q2], "answers": {}},
        violation_logs=[],
        started_at=datetime.now(timezone.utc),
        status="IN_PROGRESS"
    )
    mock_transcript.submission = mock_sub

    db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_transcript
    db.execute.return_value = mock_res

    valid_answer = " ".join(["từ_khóa"] * 55)

    # 1. Submit answer for Question 1 -> Should return next_question = q2
    res_1 = await service.submit_answer(
        db=db,
        submission_id=submission_id,
        user_id=user_id,
        payload=VivaAnswerSubmitRequest(question_id="q1", answer_text=valid_answer)
    )
    assert res_1.is_completed is False
    assert res_1.next_question.id == "q2"
    assert mock_transcript.questions_answers["current_index"] == 2

    # 2. Submit answer for Question 2 -> Final question! Should complete session
    res_2 = await service.submit_answer(
        db=db,
        submission_id=submission_id,
        user_id=user_id,
        payload=VivaAnswerSubmitRequest(question_id="q2", answer_text=valid_answer)
    )
    assert res_2.is_completed is True
    assert res_2.next_question is None
    assert mock_transcript.status == "COMPLETED"
    assert mock_sub.status == "VIVA_COMPLETED"


@pytest.mark.asyncio
async def test_viva_record_security_violations():
    service = VivaSandboxService()
    user_id = uuid.uuid4()
    submission_id = uuid.uuid4()

    mock_sub = AssignmentSubmission(id=submission_id, user_id=user_id, status="IN_VIVA")
    mock_transcript = VivaTranscript(
        id=uuid.uuid4(),
        submission_id=submission_id,
        questions_answers={"total_questions": 1, "current_index": 1, "questions": [], "answers": {}},
        violation_logs=[],
        started_at=datetime.now(timezone.utc),
        status="IN_PROGRESS"
    )
    mock_transcript.submission = mock_sub

    db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_transcript
    db.execute.return_value = mock_res

    # Record PASTE_ATTEMPT (E-9)
    recorded_paste = await service.record_security_violation(
        db=db,
        submission_id=submission_id,
        user_id=user_id,
        violation_type="PASTE_ATTEMPT",
        details={"attempted_length": 150}
    )
    assert recorded_paste is True

    # Record WINDOW_BLUR (E-VIVA-01)
    recorded_blur = await service.record_security_violation(
        db=db,
        submission_id=submission_id,
        user_id=user_id,
        violation_type="WINDOW_BLUR",
        details={"blur_duration_seconds": 12}
    )
    assert recorded_blur is True

    assert len(mock_transcript.violation_logs) == 2
    assert mock_transcript.violation_logs[0]["type"] == "PASTE_ATTEMPT"
    assert mock_transcript.violation_logs[1]["type"] == "WINDOW_BLUR"
