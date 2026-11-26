# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Unit tests for AI Rubric Cross-Evidence Evaluator (T2-I-M5-03)."""

from datetime import datetime, timezone
from decimal import Decimal
import json
import uuid
from unittest.mock import AsyncMock
import pytest
from app.modules.ai_gateway.service import AIGatewayService
from app.modules.assessment.public_api import (
    RubricCriterionDTO,
    RubricDTO,
    SubmissionArtifactDTO,
)
from app.modules.gradebook.ai_grader_service import AIGraderService
from app.modules.gradebook.enums import EvidenceFlag
from app.modules.gradebook.models import GradebookColumn, GradeEntry


def _sample_bundle() -> SubmissionArtifactDTO:
    now = datetime.now(timezone.utc)
    c1 = RubricCriterionDTO(
        id=uuid.uuid4(),
        lo_id=None,
        competency_code="C4",
        title="Kien truc phan tang",
        description="To chuc module sach",
        max_points=Decimal("5.0"),
        order_index=1,
        rating_levels=[],
    )
    c2 = RubricCriterionDTO(
        id=uuid.uuid4(),
        lo_id=None,
        competency_code="C6",
        title="Liem chinh & Van dap Viva",
        description="Giai trinh duoc quyet dinh thiet ke",
        max_points=Decimal("5.0"),
        order_index=2,
        rating_levels=[],
    )
    rubric = RubricDTO(
        id=uuid.uuid4(),
        assignment_id=uuid.uuid4(),
        title="Rubric Do an",
        total_points=Decimal("10.0"),
        is_frozen=True,
        criteria=[c1, c2],
    )
    return SubmissionArtifactDTO(
        submission_id=uuid.uuid4(),
        assignment_id=rubric.assignment_id,
        assignment_title="Do an Web",
        course_id=uuid.uuid4(),
        course_name="IT4409",
        student_id=uuid.uuid4(),
        student_name="Nguyen Van A",
        student_email="sv1@adlas.edu.vn",
        student_code="SV001",
        version=1,
        versions=[],
        project_title="ADLAS",
        file_url=None,
        git_repo_url="https://github.com/demo/repo.git",
        comments=None,
        self_contribution_pct=85,
        ai_disclosure_data={"tools_used": ["ChatGPT"]},
        submitted_at=now,
        is_late=False,
        late_penalty_applied=0.0,
        status="VIVA_COMPLETED",
        viva_status="COMPLETED",
        viva_started_at=now,
        viva_completed_at=now,
        ai_digest_summary="He thong gom 3 tang Router -> Service -> Repository voi PostgreSQL.",
        digest_type="CODE",
        summarizer_mode="gemini_long_context",
        generation_source="gemini_live",
        questions=[{"id": "q1", "question_text": "Giai thich tang Repository?"}],
        answers={"q1": {"answer_text": "Tang Repository dong goi toan bo truy van SQLAlchemy..."}},
        violation_logs=[],
        rubric=rubric,
    )


@pytest.mark.asyncio
async def test_rubric_proposal_with_citations_and_conflicting_flag(monkeypatch):
    bundle = _sample_bundle()
    c1_id = str(bundle.rubric.criteria[0].id)
    c2_id = str(bundle.rubric.criteria[1].id)

    mock_json = json.dumps({
        "evidence_flag": "CONFLICTING",
        "summary_comment": "Code phuc tap nhung cau tra loi Viva mau thuan voi logic trong bai nop.",
        "criteria_proposals": [
            {
                "criterion_id": c1_id,
                "proposed_points": 4.0,
                "rating_level_label": "Kha",
                "explanation": "To chuc module tot.",
                "citations": [
                    {"source_type": "SUBMISSION", "reference": "Digest", "excerpt": "Router -> Service -> Repository"}
                ],
            },
            {
                "criterion_id": c2_id,
                "proposed_points": 1.5,
                "rating_level_label": "Chua dat",
                "explanation": "Khong giai trinh duoc tang Repository.",
                "citations": [
                    {"source_type": "VIVA", "reference": "q1", "excerpt": "Tang Repository dong goi..."}
                ],
            },
        ],
    })

    gateway = AIGatewayService()
    monkeypatch.setattr(gateway, "_call_gemini_raw", AsyncMock(return_value=mock_json))

    db = AsyncMock()
    repo = AsyncMock()
    repo.is_course_locked.return_value = False
    col = GradebookColumn(
        id=uuid.uuid4(), course_id=bundle.course_id, group_id=uuid.uuid4(), item_type="ASSIGNMENT", title="Do an", is_muted=True
    )
    repo.get_column_by_item.return_value = col
    existing_grade = GradeEntry(
        id=uuid.uuid4(), column_id=col.id, user_id=bundle.student_id, official_score=Decimal("8.5")
    )
    repo.get_grade_entry.return_value = existing_grade

    assess_pub = AsyncMock()
    assess_pub.get_submission_bundle.return_value = bundle

    svc = AIGraderService(db, repo=repo, ai_gateway=gateway, assessment_public=assess_pub)
    proposal = await svc.generate_rubric_proposal(bundle.submission_id, actor_id=uuid.uuid4())

    assert proposal.evidence_flag == EvidenceFlag.CONFLICTING
    assert proposal.proposed_total_score == Decimal("5.5")
    assert len(proposal.criteria_proposals) == 2
    assert proposal.criteria_proposals[0].citations[0].source_type == "SUBMISSION"
    # BR-07: Must NOT overwrite existing instructor official_score!
    assert existing_grade.official_score == Decimal("8.5")


@pytest.mark.asyncio
async def test_ai_degraded_fallback_to_human_review_e12(monkeypatch):
    bundle = _sample_bundle()
    gateway = AIGatewayService()
    monkeypatch.setattr(gateway, "_call_gemini_raw", AsyncMock(return_value=None))

    db = AsyncMock()
    repo = AsyncMock()
    repo.is_course_locked.return_value = False
    col = GradebookColumn(
        id=uuid.uuid4(), course_id=bundle.course_id, group_id=uuid.uuid4(), item_type="ASSIGNMENT", title="Do an", is_muted=True
    )
    repo.get_column_by_item.return_value = col
    repo.get_grade_entry.return_value = None

    assess_pub = AsyncMock()
    assess_pub.get_submission_bundle.return_value = bundle

    svc = AIGraderService(db, repo=repo, ai_gateway=gateway, assessment_public=assess_pub)
    proposal = await svc.generate_rubric_proposal(bundle.submission_id)

    assert proposal.evidence_flag == EvidenceFlag.HUMAN_REVIEW
    assert proposal.generation_source == "deterministic_fallback"
    assert proposal.proposed_total_score is None
