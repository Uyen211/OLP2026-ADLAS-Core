# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Unit tests for SpeedGrader 3-Column Service, Override Guard (E-GB-07), and Voice Feedback."""

from datetime import datetime, timezone
from decimal import Decimal
import uuid
from unittest.mock import AsyncMock
import pytest
from app.core.storage_client import ObjectStorageClient
from app.modules.assessment.public_api import SubmissionArtifactDTO
from app.modules.gradebook.exceptions import (
    GradebookInvalidVoiceFileException,
    GradeOverrideReasonRequiredException,
)
from app.modules.gradebook.models import GradebookColumn, GradeEntry
from app.modules.gradebook.schemas import SpeedGraderSaveGradeRequest
from app.modules.gradebook.speedgrader_service import SpeedGraderService


def _make_bundle(viva_status: str = "COMPLETED") -> SubmissionArtifactDTO:
    now = datetime.now(timezone.utc)
    return SubmissionArtifactDTO(
        submission_id=uuid.uuid4(),
        assignment_id=uuid.uuid4(),
        assignment_title="Do an Giua ky",
        course_id=uuid.uuid4(),
        course_name="IT4409",
        student_id=uuid.uuid4(),
        student_name="Tran Thi B",
        student_email="sv2@adlas.edu.vn",
        student_code="SV002",
        version=2,
        versions=[],
        project_title="He thong Quan ly",
        file_url="storage://adlas-submissions/sv2/v2.zip",
        git_repo_url=None,
        comments="Nop ban v2",
        self_contribution_pct=75,
        ai_disclosure_data={"tools_used": ["Copilot"]},
        submitted_at=now,
        is_late=False,
        late_penalty_applied=0.0,
        status="VIVA_COMPLETED",
        viva_status=viva_status,
        viva_started_at=now,
        viva_completed_at=now,
        ai_digest_summary="Tom tat kien truc 3 tang",
        digest_type="CODE",
        summarizer_mode="gemini_long_context",
        generation_source="gemini_live",
        questions=[],
        answers={},
        violation_logs=[
            {"type": "WINDOW_BLUR", "timestamp": now.isoformat()},
            {"type": "PASTE_ATTEMPT", "timestamp": now.isoformat()},
        ],
        rubric=None,
    )


@pytest.mark.asyncio
async def test_workspace_flags_missing_viva_e_speed_01():
    bundle = _make_bundle(viva_status="READY")
    db = AsyncMock()
    repo = AsyncMock()
    repo.is_course_locked.return_value = False
    repo.get_column_by_item.return_value = GradebookColumn(
        id=uuid.uuid4(), course_id=bundle.course_id, group_id=uuid.uuid4(), item_type="ASSIGNMENT", title="Do an", is_muted=True
    )
    repo.get_grade_entry.return_value = None
    assess_pub = AsyncMock()
    assess_pub.get_submission_bundle.return_value = bundle

    svc = SpeedGraderService(db, repo=repo, assessment_public=assess_pub)
    ws = await svc.get_workspace(bundle.submission_id)

    assert ws.missing_viva is True
    assert ws.window_blur_count == 1
    assert ws.paste_attempt_count == 1


@pytest.mark.asyncio
async def test_override_reason_required_when_delta_exceeds_1_5_e_gb_07():
    bundle = _make_bundle()
    col = GradebookColumn(
        id=uuid.uuid4(), course_id=bundle.course_id, group_id=uuid.uuid4(), item_type="ASSIGNMENT", title="Do an", is_muted=True
    )
    existing = GradeEntry(
        id=uuid.uuid4(),
        column_id=col.id,
        user_id=bundle.student_id,
        proposed_ai_score=Decimal("5.00"),
    )
    db = AsyncMock()
    repo = AsyncMock()
    repo.is_course_locked.return_value = False
    repo.get_column_by_item.return_value = col
    repo.get_grade_entry.return_value = existing
    assess_pub = AsyncMock()
    assess_pub.get_submission_bundle.return_value = bundle

    svc = SpeedGraderService(db, repo=repo, assessment_public=assess_pub)

    # Delta = |8.5 - 5.0| = 3.5 > 1.5 without reason -> E-GB-07
    with pytest.raises(GradeOverrideReasonRequiredException) as exc:
        await svc.save_official_grade(
            bundle.submission_id,
            SpeedGraderSaveGradeRequest(official_score=Decimal("8.5")),
            actor_id=uuid.uuid4(),
        )
    assert exc.value.detail["code"] == "E-GB-07"

    # With explicit override_reason -> succeeds & marks submission GRADED
    ws = await svc.save_official_grade(
        bundle.submission_id,
        SpeedGraderSaveGradeRequest(
            official_score=Decimal("8.5"),
            override_reason="Sinh vien bao ve truc tiep tren lop tot hon ban ghi van dap.",
        ),
        actor_id=uuid.uuid4(),
    )
    assert ws.official_score == Decimal("8.5")
    assert ws.is_overridden is True
    assess_pub.mark_submission_graded.assert_awaited_once_with(bundle.submission_id)


@pytest.mark.asyncio
async def test_voice_feedback_upload_and_download_roundtrip(tmp_path):
    storage = ObjectStorageClient(provider="s3", s3_endpoint="", local_root=str(tmp_path))
    svc = SpeedGraderService(AsyncMock(), repo=AsyncMock(), assessment_public=AsyncMock(), storage=storage)
    actor_id = uuid.uuid4()

    # Reject invalid extension
    with pytest.raises(GradebookInvalidVoiceFileException):
        await svc.upload_voice_feedback(b"abc", "malware.exe", "application/octet-stream", actor_id)

    # Valid .webm roundtrip
    audio_bytes = b"WEBM-VOICE-FEEDBACK-BYTES-0123456789"
    res = await svc.upload_voice_feedback(audio_bytes, "note.webm", "audio/webm", actor_id)
    assert res["voice_feedback_url"].startswith("/api/v1/gradebook/voice-feedback/")
    object_key = res["voice_feedback_url"].replace("/api/v1/gradebook/voice-feedback/", "")

    downloaded, _ = await svc.download_voice_feedback(object_key)
    assert downloaded == audio_bytes
