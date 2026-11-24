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
