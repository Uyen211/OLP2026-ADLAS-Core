# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Unit tests for Assessment submission lifecycle, late penalty BR-11, and cutoff rules."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest
from pydantic import ValidationError
from app.modules.assessment.exceptions import (
    IntegrityPledgeRequiredException,
    InvalidSubmissionPayloadException,
    SubmissionCutoffExceededException,
)
from app.modules.assessment.models import Assignment, Rubric
from app.modules.assessment.schemas import (
    AIDisclosureSchema,
    SubmissionCreateRequest,
)
from app.modules.assessment.service import AssessmentSubmissionService


def test_ai_disclosure_validation_length():
    # Valid disclosure (>= 20 chars)
    valid_disclosure = AIDisclosureSchema(
        self_contribution_pct=80,
        tools_used=["ChatGPT"],
        usage_description="Used ChatGPT to brainstorm project outline and clarify concepts."
    )
    assert valid_disclosure.self_contribution_pct == 80

    # Invalid disclosure (< 20 chars)
    with pytest.raises(ValidationError):
        AIDisclosureSchema(
            self_contribution_pct=50,
            tools_used=["Claude"],
            usage_description="Too short."
        )


def test_submission_create_request_git_url_validation():
    # Valid git URL
    req = SubmissionCreateRequest(
        git_repo_url="https://github.com/adlas/project.git",
        ai_disclosure=AIDisclosureSchema(
            self_contribution_pct=90,
            tools_used=["Copilot"],
            usage_description="Used Copilot for standard boilerplate code completion."
        )
    )
    assert req.git_repo_url == "https://github.com/adlas/project.git"

    # Invalid git URL scheme
    with pytest.raises(ValidationError):
        SubmissionCreateRequest(
            git_repo_url="ftp://invalid.com/repo.git",
            ai_disclosure=AIDisclosureSchema(
                self_contribution_pct=90,
                tools_used=["Copilot"],
                usage_description="Used Copilot for standard boilerplate code completion."
            )
        )


@pytest.mark.asyncio
async def test_submission_past_until_date_raises_e8():
    service = AssessmentSubmissionService()
    now = datetime.now(timezone.utc)
    mock_assignment = Assignment(
        id=uuid.uuid4(),
        course_id=uuid.uuid4(),
        title="Web Development Assignment",
        instructions="Complete the project",
        due_date=now - timedelta(days=5),
        until_date=now - timedelta(days=2),  # Past cutoff
        late_penalty_percent=5.0
    )

    db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_assignment
    db.execute.return_value = mock_res

    payload = SubmissionCreateRequest(
        file_url="http://storage/adlas-submissions/code.zip",
        ai_disclosure=AIDisclosureSchema(
            self_contribution_pct=100,
            tools_used=[],
            usage_description="Completely implemented without any external AI assistance."
        )
    )

    with pytest.raises(SubmissionCutoffExceededException):
        await service.create_submission(
            db=db,
            assignment_id=mock_assignment.id,
            user_id=uuid.uuid4(),
            payload=payload
        )


@pytest.mark.asyncio
async def test_submission_late_penalty_br11_calculation():
    service = AssessmentSubmissionService()
    now = datetime.now(timezone.utc)
    mock_assignment = Assignment(
        id=uuid.uuid4(),
        course_id=uuid.uuid4(),
        title="Web Development Assignment",
        instructions="Complete the project",
        due_date=now - timedelta(hours=36),  # 1.5 days late -> rounded up to 2 days
        until_date=now + timedelta(days=3),   # Still open
        late_penalty_percent=5.0,
        is_viva_required=False
    )

    db = AsyncMock()
    # Mock sequence of db.execute calls: 1. Assignment, 2. Version check, 3. Rubric check
    call_count = 0
    def mock_execute_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        res = MagicMock()
        if call_count == 1:
            res.scalar_one_or_none.return_value = mock_assignment
        elif call_count == 2:
            res.scalar_one_or_none.return_value = None  # No prior version -> v1
        elif call_count == 3:
            res.scalar_one_or_none.return_value = None  # No rubric
        return res

    db.execute.side_effect = mock_execute_side_effect

    payload = SubmissionCreateRequest(
        file_url="http://storage/adlas-submissions/code.zip",
        ai_disclosure=AIDisclosureSchema(
            self_contribution_pct=70,
            tools_used=["ChatGPT"],
            usage_description="ChatGPT assisted with CSS styling and flexbox layouts."
        )
    )

    res = await service.create_submission(
        db=db,
        assignment_id=mock_assignment.id,
        user_id=uuid.uuid4(),
        payload=payload
    )

    assert res.version == 1
    assert res.is_late is True
    # 2 days * 5.0% = 10.0%
    assert res.late_penalty_applied == 10.0


@pytest.mark.asyncio
async def test_submission_freezes_rubric_on_first_submission():
    service = AssessmentSubmissionService()
    now = datetime.now(timezone.utc)
    mock_assignment = Assignment(
        id=uuid.uuid4(),
        course_id=uuid.uuid4(),
        title="Project Assignment",
        instructions="Build project",
        due_date=now + timedelta(days=2),
        until_date=now + timedelta(days=5),
        late_penalty_percent=5.0,
        is_viva_required=False
    )
    mock_rubric = Rubric(
        id=uuid.uuid4(),
        assignment_id=mock_assignment.id,
        title="Assessment Rubric",
        is_frozen=False
    )

    db = AsyncMock()
    call_count = 0
    def mock_execute_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        res = MagicMock()
        if call_count == 1:
            res.scalar_one_or_none.return_value = mock_assignment
        elif call_count == 2:
            res.scalar_one_or_none.return_value = None  # First submission -> version 1
        elif call_count == 3:
            res.scalar_one_or_none.return_value = mock_rubric
        return res

    db.execute.side_effect = mock_execute_side_effect

    payload = SubmissionCreateRequest(
        file_url="http://storage/adlas-submissions/code.zip",
        ai_disclosure=AIDisclosureSchema(
            self_contribution_pct=95,
            tools_used=["Claude"],
            usage_description="Used Claude for drafting README and testing edge cases."
        )
    )

    await service.create_submission(
        db=db,
        assignment_id=mock_assignment.id,
        user_id=uuid.uuid4(),
        payload=payload
    )

    assert mock_rubric.is_frozen is True


@pytest.mark.asyncio
async def test_submission_rejects_unsigned_pledge_and_bad_extension():
    service = AssessmentSubmissionService()
    now = datetime.now(timezone.utc)
    mock_assignment = Assignment(
        id=uuid.uuid4(),
        course_id=uuid.uuid4(),
        title="Project Assignment",
        instructions="Build project",
        submission_type="FILE_UPLOAD",
        allowed_extensions=".zip,.pdf",
        due_date=now + timedelta(days=2),
        until_date=now + timedelta(days=5),
        late_penalty_percent=5.0,
        is_viva_required=False
    )

    db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_assignment
    db.execute.return_value = mock_res

    unsigned_payload = SubmissionCreateRequest(
        file_url="/app/uploads/submissions/code.zip",
        is_pledge_signed=False,
        ai_disclosure=AIDisclosureSchema(
            self_contribution_pct=90,
            tools_used=[],
            usage_description="Implemented core module independently and verified tests."
        )
    )
    with pytest.raises(IntegrityPledgeRequiredException):
        await service.create_submission(db=db, assignment_id=mock_assignment.id, user_id=uuid.uuid4(), payload=unsigned_payload)

    bad_ext_payload = SubmissionCreateRequest(
        file_url="/app/uploads/submissions/malware.exe",
        is_pledge_signed=True,
        ai_disclosure=AIDisclosureSchema(
            self_contribution_pct=90,
            tools_used=[],
            usage_description="Implemented core module independently and verified tests."
        )
    )
    with pytest.raises(InvalidSubmissionPayloadException):
        await service.create_submission(db=db, assignment_id=mock_assignment.id, user_id=uuid.uuid4(), payload=bad_ext_payload)


@pytest.mark.asyncio
async def test_initialize_viva_transcript_persists_ai_digest_summary():
    from app.modules.assessment.ingestion.digest_builder import UniversalSubmissionDigest
    from app.modules.assessment.models import VivaTranscript

    mock_builder = MagicMock()
    mock_builder.build_digest = AsyncMock(
        return_value=UniversalSubmissionDigest(
            digest_type="CODE",
            content="### TÓM TẮT KỸ THUẬT\n1. Kiến trúc Binary Search...",
            metadata={"source": "zip_archive", "summarizer_mode": "gemini_long_context"},
        )
    )
    mock_gateway = MagicMock()
    mock_gateway.last_generation_source = "gemini_live"
    mock_gateway.generate_viva_questions = AsyncMock(
        return_value=[
            {
                "id": "q1",
                "question_index": 1,
                "total_questions": 1,
                "question_text": "Giải thích hàm binary_search?",
                "category": "DEFENSE",
            }
        ]
    )

    service = AssessmentSubmissionService(digest_builder=mock_builder, ai_gateway=mock_gateway)
    assignment = Assignment(
        id=uuid.uuid4(),
        course_id=uuid.uuid4(),
        title="Thuật toán Tìm kiếm",
        instructions="Cài đặt thuật toán",
        viva_question_count=1,
    )
    submission = MagicMock(id=uuid.uuid4(), project_title="Tìm kiếm nhị phân")
    payload = SubmissionCreateRequest(
        file_url="/app/uploads/submissions/algo.zip",
        file_name="algo.zip",
        ai_disclosure=AIDisclosureSchema(
            self_contribution_pct=85,
            tools_used=["Copilot"],
            usage_description="Used Copilot for generating boundary unit tests.",
        ),
    )

    added_objects = []
    db = MagicMock()
    db.add = MagicMock(side_effect=added_objects.append)

    await service._initialize_viva_transcript(
        db=db,
        assignment=assignment,
        submission=submission,
        payload=payload,
    )

    transcripts = [obj for obj in added_objects if isinstance(obj, VivaTranscript)]
    assert len(transcripts) == 1
    qa = transcripts[0].questions_answers
    assert qa["ai_digest_summary"] == "### TÓM TẮT KỸ THUẬT\n1. Kiến trúc Binary Search..."
    assert qa["digest_type"] == "CODE"
    assert qa["summarizer_mode"] == "gemini_long_context"
    assert qa["generation_source"] == "gemini_live"


@pytest.mark.asyncio
async def test_instructor_review_requires_instructor_and_returns_digest_and_qa():
    from app.modules.assessment.exceptions import AssessmentAccessDeniedException
    from app.modules.assessment.models import AssignmentSubmission, VivaTranscript

    service = AssessmentSubmissionService()
    course_id = uuid.uuid4()
    assignment = Assignment(id=uuid.uuid4(), course_id=course_id, title="BTL AI")
    student = MagicMock(id=uuid.uuid4(), full_name="Le Hoang Nam", email="student1@adlas.edu.vn")
    transcript = VivaTranscript(
        id=uuid.uuid4(),
        submission_id=uuid.uuid4(),
        status="COMPLETED",
        questions_answers={
            "ai_digest_summary": "Tóm tắt nội dung bài nộp...",
            "digest_type": "DOCUMENT",
            "digest_metadata": {"original_word_count": 5000},
            "summarizer_mode": "gemini_long_context",
            "generation_source": "gemini_live",
            "total_questions": 1,
            "questions": [
                {
                    "id": "q1",
                    "question_index": 1,
                    "total_questions": 1,
                    "question_text": "Trình bày đóng góp chính?",
                    "category": "DEFENSE",
                }
            ],
            "answers": {
                "q1": {
                    "answer_text": "Em thực hiện mô hình chính và kiểm thử trên tập dữ liệu VietBioNER.",
                    "time_spent_seconds": 120,
                    "submitted_at": "2026-11-25T07:00:00+00:00",
                }
            },
        },
        violation_logs=[{"type": "WINDOW_BLUR", "timestamp": "2026-11-25T06:59:00+00:00"}],
    )
    sub = AssignmentSubmission(
        id=transcript.submission_id,
        assignment_id=assignment.id,
        user_id=student.id,
        version=1,
        project_title="BioNER Active Learning",
        self_contribution_pct=90,
        ai_disclosure_data={"tools_used": ["ChatGPT"], "usage_description": "Check grammar."},
        is_pledge_signed=True,
        submitted_at=datetime.now(timezone.utc),
        is_late=False,
        late_penalty_applied=0.0,
        status="VIVA_COMPLETED",
    )
    sub.assignment = assignment
    sub.user = student
    sub.viva_transcript = transcript

    # 1. Student denied
    db_student = AsyncMock()
    r1 = MagicMock()
    r1.scalar_one_or_none.return_value = sub
    r2 = MagicMock()
    r2.scalar_one_or_none.return_value = "STUDENT"
    db_student.execute.side_effect = [r1, r2]

    student_user = MagicMock(id=student.id, system_role="USER")
    with pytest.raises(AssessmentAccessDeniedException):
        await service.get_submission_review(db=db_student, submission_id=sub.id, current_user=student_user)

    # 2. Instructor allowed and gets digest + Q&A
    db_inst = AsyncMock()
    i1 = MagicMock()
    i1.scalar_one_or_none.return_value = sub
    i2 = MagicMock()
    i2.scalar_one_or_none.return_value = "INSTRUCTOR"
    db_inst.execute.side_effect = [i1, i2]

    instructor_user = MagicMock(id=uuid.uuid4(), system_role="USER")
    review = await service.get_submission_review(db=db_inst, submission_id=sub.id, current_user=instructor_user)
    assert review.ai_digest_summary == "Tóm tắt nội dung bài nộp..."
    assert review.digest_type == "DOCUMENT"
    assert len(review.questions) == 1
    assert review.answers["q1"].answer_text.startswith("Em thực hiện")
    assert len(review.violation_logs) == 1
