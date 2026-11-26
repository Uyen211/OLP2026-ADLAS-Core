# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Pure unit tests for Phase 3 Assignment Authoring, Rubric Builder and Integrity Pledge."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest
from pydantic import ValidationError
from app.modules.assessment.authoring_schemas import (
    AssignmentCreateRequest,
    AssignmentUpdateRequest,
    MasteryLevelSchema,
    PledgeSignRequest,
    RubricCriterionSchema,
    RubricSaveRequest,
)
from app.modules.assessment.authoring_service import (
    EVENT_ASSIGNMENT_PUBLISHED,
    AssignmentAuthoringService,
    validate_schedule,
)
from app.modules.assessment.exceptions import (
    AssessmentNotFoundException,
    AssignmentHasSubmissionsException,
    AssignmentNotOpenException,
    IntegrityPledgeNotSignedException,
    InvalidAssignmentScheduleException,
    InvalidRubricLearningObjectiveException,
    InvalidRubricTotalPointsException,
    MaxAttemptsExceededException,
    RubricFrozenException,
)
from app.modules.assessment.models import Assignment, IntegrityPledge, Rubric, RubricCriteria
from app.modules.assessment.pledge_service import PLEDGE_TERMS, PledgeService, validate_pledge_payload
from app.modules.assessment.rubric_service import EVENT_RUBRIC_SAVED, RubricService
from app.modules.assessment.schemas import AIDisclosureSchema, SubmissionCreateRequest
from app.modules.assessment.service import AssessmentSubmissionService
from app.modules.course.enums import BloomLevel, ContextualRole
from app.modules.course.public_api import CoursePublicService, LODTO


def _make_user(system_role: str = "USER") -> MagicMock:
    return MagicMock(id=uuid.uuid4(), system_role=system_role)


def _four_levels(max_pts: Decimal) -> list[MasteryLevelSchema]:
    q = Decimal("0.1")
    return [
        MasteryLevelSchema(level="EXCELLENT", label="Xuất sắc", description="Hoàn hảo", points=max_pts.quantize(q)),
        MasteryLevelSchema(
            level="GOOD", label="Khá / Giỏi", description="Tốt", points=(max_pts * Decimal("0.8")).quantize(q)
        ),
        MasteryLevelSchema(
            level="PROFICIENT", label="Đạt chuẩn", description="Đạt", points=(max_pts * Decimal("0.5")).quantize(q)
        ),
        MasteryLevelSchema(level="INSUFFICIENT", label="Chưa đạt", description="Chưa đạt", points=Decimal("0.0")),
    ]


def _make_assignment(**overrides) -> Assignment:
    now = datetime.now(timezone.utc)
    defaults = dict(
        id=uuid.uuid4(),
        course_id=uuid.uuid4(),
        title="Bài tập Lập trình Hướng đối tượng",
        instructions="Hoàn thành ứng dụng quản lý thư viện.",
        submission_type="FILE_UPLOAD",
        allowed_extensions=".zip,.pdf",
        max_file_size_mb=50,
        is_group_assignment=False,
        is_transfer_task=False,
        available_from=now - timedelta(days=1),
        due_date=now + timedelta(days=3),
        until_date=now + timedelta(days=5),
        late_penalty_percent=Decimal("5.0"),
        is_viva_required=True,
        viva_question_count=3,
        ai_policy_level="YELLOW",
        is_published=False,
        max_points=Decimal("10.0"),
        max_attempts=None,
    )
    defaults.update(overrides)
    return Assignment(**defaults)


# ----------------------------------------------------------------------
# T2-P-M3-01: Assignment Authoring & Schedule Rules
# ----------------------------------------------------------------------
def test_assignment_title_length_validation():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        AssignmentCreateRequest(title="Abc", instructions="Valid", due_date=now + timedelta(days=1))
    with pytest.raises(ValidationError):
        AssignmentCreateRequest(title="A" * 151, instructions="Valid", due_date=now + timedelta(days=1))
    req = AssignmentCreateRequest(
        title="Bài tập số 1: Cấu trúc dữ liệu",
        instructions="Cài đặt cây nhị phân tìm kiếm.",
        due_date=now + timedelta(days=2),
    )
    assert req.publish is False


def test_validate_schedule_enforces_e_asn_01():
    now = datetime.now(timezone.utc)
    # until_date < due_date -> E-ASN-01
    with pytest.raises(InvalidAssignmentScheduleException) as exc:
        validate_schedule(now, now + timedelta(days=3), now + timedelta(days=2))
    assert exc.value.detail["code"] == "E-ASN-01"

    # due_date < available_from -> E-ASN-01
    with pytest.raises(InvalidAssignmentScheduleException) as exc2:
        validate_schedule(now + timedelta(days=2), now + timedelta(days=1), now + timedelta(days=4))
    assert exc2.value.detail["code"] == "E-ASN-01"

    # Equal boundary timestamps are valid
    validate_schedule(now, now, now)


@pytest.mark.asyncio
async def test_create_draft_and_publish_emits_outbox_event():
    db = AsyncMock()
    repo = AsyncMock()
    course_svc = AsyncMock(spec=CoursePublicService)
    course_svc.assert_course_role.return_value = ContextualRole.INSTRUCTOR
    user = _make_user()
    course_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    svc = AssignmentAuthoringService(db=db, repo=repo, course_service=course_svc)
    draft_req = AssignmentCreateRequest(
        title="Đồ án giữa kỳ Hệ điều hành",
        instructions="Viết shell cơ bản.",
        due_date=now + timedelta(days=7),
        until_date=now + timedelta(days=9),
        publish=False,
    )
    draft_res = await svc.create_assignment(course_id, user, draft_req)
    assert draft_res.is_published is False
    repo.add_outbox_event.assert_not_awaited()

    # Now publish the draft -> emits assessment.assignment_published
    stored = _make_assignment(id=draft_res.id, course_id=course_id, is_published=False)
    repo.get_assignment.return_value = stored

    async def _set_pub(a, flag):
        a.is_published = flag
        return a

    repo.set_published.side_effect = _set_pub
    pub_res = await svc.publish_assignment(stored.id, user)
    assert pub_res.is_published is True
    repo.add_outbox_event.assert_awaited_once()
    assert repo.add_outbox_event.call_args[0][0] == EVENT_ASSIGNMENT_PUBLISHED

    # Idempotent publish does not emit a duplicate event
    repo.add_outbox_event.reset_mock()
    await svc.publish_assignment(stored.id, user)
    repo.add_outbox_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_and_delete_assignment_guards():
    db = AsyncMock()
    repo = AsyncMock()
    course_svc = AsyncMock(spec=CoursePublicService)
    course_svc.assert_course_role.return_value = ContextualRole.INSTRUCTOR
    user = _make_user()
    assignment = _make_assignment()
    repo.get_assignment.return_value = assignment

    svc = AssignmentAuthoringService(db=db, repo=repo, course_service=course_svc)

    # Invalid schedule on update raises E-ASN-01
    with pytest.raises(InvalidAssignmentScheduleException):
        await svc.update_assignment(
            assignment.id,
            user,
            AssignmentUpdateRequest(until_date=assignment.due_date - timedelta(hours=1)),
        )

    # Delete blocked when submissions exist
    repo.count_submissions.return_value = 2
    with pytest.raises(AssignmentHasSubmissionsException) as exc:
        await svc.delete_assignment(assignment.id, user)
    assert exc.value.status_code == 409

    # Delete succeeds when 0 submissions
    repo.count_submissions.return_value = 0
    repo.delete_assignment_if_no_submissions.return_value = True
    res = await svc.delete_assignment(assignment.id, user)
    assert res.deleted is True


@pytest.mark.asyncio
async def test_student_hidden_draft_and_submission_window_and_max_attempts():
    service = AssessmentSubmissionService()
    now = datetime.now(timezone.utc)

    # 1. Draft assignment is hidden from STUDENT in get_assignment_detail
    draft = _make_assignment(is_published=False)
    draft.submissions = []
    draft.rubric = None
    db_detail = AsyncMock()
    r1, r2 = MagicMock(), MagicMock()
    r1.scalar_one_or_none.return_value = draft
    r2.scalar_one_or_none.return_value = "STUDENT"
    db_detail.execute.side_effect = [r1, r2]
    with pytest.raises(AssessmentNotFoundException):
        await service.get_assignment_detail(
            db=db_detail, assignment_id=draft.id, user_id=uuid.uuid4(), current_user=_make_user()
        )

    # 2. E-ASN-02: submission before available_from
    future_assignment = _make_assignment(
        is_published=True,
        available_from=now + timedelta(hours=2),
        due_date=now + timedelta(days=2),
        until_date=now + timedelta(days=3),
    )
    db_open = AsyncMock()
    res_open = MagicMock()
    res_open.scalar_one_or_none.return_value = future_assignment
    db_open.execute.return_value = res_open
    payload = SubmissionCreateRequest(
        file_url="http://storage/sub.zip",
        ai_disclosure=AIDisclosureSchema(
            self_contribution_pct=100,
            tools_used=[],
            usage_description="Tôi tự thực hiện toàn bộ mã nguồn và kiểm thử bài tập.",
        ),
    )
    with pytest.raises(AssignmentNotOpenException) as exc_open:
        await service.create_submission(
            db=db_open, assignment_id=future_assignment.id, user_id=uuid.uuid4(), payload=payload
        )
    assert exc_open.value.detail["code"] == "E-ASN-02"

    # 3. E-ASN-03: max_attempts exceeded
    limited = _make_assignment(is_published=True, max_attempts=2)
    db_att = AsyncMock()
    ra1, ra2 = MagicMock(), MagicMock()
    ra1.scalar_one_or_none.return_value = limited
    ra2.scalar_one_or_none.return_value = 2  # already submitted v2
    db_att.execute.side_effect = [ra1, ra2]
    with pytest.raises(MaxAttemptsExceededException) as exc_att:
        await service.create_submission(
            db=db_att, assignment_id=limited.id, user_id=uuid.uuid4(), payload=payload
        )
    assert exc_att.value.detail["code"] == "E-ASN-03"


# ----------------------------------------------------------------------
# T2-P-M3-02: Rubric 4 Mastery Levels, Exact Decimal 10.0, Freeze Guard
# ----------------------------------------------------------------------
def test_rubric_requires_four_distinct_mastery_levels():
    with pytest.raises(ValidationError):
        RubricCriterionSchema(
            title="Tiêu chí 1",
            max_points=Decimal("5.0"),
            rating_levels=_four_levels(Decimal("5.0"))[:3],
        )
    dup_levels = _four_levels(Decimal("5.0"))
    dup_levels[3] = MasteryLevelSchema(level="EXCELLENT", description="Dup", points=Decimal("0.0"))
    with pytest.raises(ValidationError):
        RubricCriterionSchema(title="Tiêu chí 1", max_points=Decimal("5.0"), rating_levels=dup_levels)


@pytest.mark.asyncio
async def test_rubric_decimal_total_and_lo_check_and_freeze_guard():
    db = AsyncMock()
    repo = AsyncMock()
    course_svc = AsyncMock(spec=CoursePublicService)
    course_svc.assert_course_role.return_value = ContextualRole.INSTRUCTOR
    user = _make_user()
    assignment = _make_assignment(is_published=True)
    lo_id = uuid.uuid4()
    course_svc.get_learning_objectives.return_value = [
        LODTO(
            id=lo_id,
            course_id=assignment.course_id,
            code="LO1",
            description="Phân tích yêu cầu",
            bloom_level=BloomLevel.ANALYZE,
            order_index=1,
        )
    ]
    repo.get_assignment.return_value = assignment
    repo.get_rubric_with_criteria.return_value = None
    repo.count_submissions.return_value = 0

    svc = RubricService(db=db, repo=repo, course_service=course_svc)

    # 1. Total != 10.0 (e.g. 9.0) -> E-RUB-01
    bad_total = RubricSaveRequest(
        title="Rubric thiếu điểm",
        criteria=[
            RubricCriterionSchema(title="C1", max_points=Decimal("4.5"), rating_levels=_four_levels(Decimal("4.5"))),
            RubricCriterionSchema(title="C2", max_points=Decimal("4.5"), rating_levels=_four_levels(Decimal("4.5"))),
        ],
    )
    with pytest.raises(InvalidRubricTotalPointsException) as exc_tot:
        await svc.save_rubric(assignment.id, user, bad_total)
    assert exc_tot.value.detail["code"] == "E-RUB-01"

    # 2. LO from another course -> E-RUB-03
    foreign_lo = uuid.uuid4()
    bad_lo = RubricSaveRequest(
        title="Rubric sai LO",
        criteria=[
            RubricCriterionSchema(
                title="C1", lo_id=foreign_lo, max_points=Decimal("10.0"), rating_levels=_four_levels(Decimal("10.0"))
            )
        ],
    )
    with pytest.raises(InvalidRubricLearningObjectiveException) as exc_lo:
        await svc.save_rubric(assignment.id, user, bad_lo)
    assert exc_lo.value.detail["code"] == "E-RUB-03"

    # 3. Exact Decimal sum 3.3 + 3.3 + 3.4 == 10.0 succeeds & emits Outbox event
    saved_rubric = Rubric(
        id=uuid.uuid4(),
        assignment_id=assignment.id,
        title="Rubric chuẩn",
        total_points=Decimal("10.0"),
        is_frozen=False,
        version=1,
        criteria=[
            RubricCriteria(
                id=uuid.uuid4(),
                title="C1",
                lo_id=lo_id,
                max_points=Decimal("3.3"),
                rating_levels=[],
                order_index=1,
            )
        ],
    )
    repo.replace_rubric.return_value = saved_rubric
    repo.get_rubric_with_criteria.side_effect = [None, saved_rubric]

    good_req = RubricSaveRequest(
        title="Rubric chuẩn",
        criteria=[
            RubricCriterionSchema(
                title="C1", lo_id=lo_id, max_points=Decimal("3.3"), rating_levels=_four_levels(Decimal("3.3"))
            ),
            RubricCriterionSchema(
                title="C2", lo_id=lo_id, max_points=Decimal("3.3"), rating_levels=_four_levels(Decimal("3.3"))
            ),
            RubricCriterionSchema(
                title="C3", lo_id=lo_id, max_points=Decimal("3.4"), rating_levels=_four_levels(Decimal("3.4"))
            ),
        ],
    )
    res = await svc.save_rubric(assignment.id, user, good_req)
    assert res.exists is True
    assert res.total_points == 10.0
    repo.add_outbox_event.assert_awaited_once()
    assert repo.add_outbox_event.call_args[0][0] == EVENT_RUBRIC_SAVED

    # 4. Frozen rubric or submission_count > 0 -> E-RUB-02
    frozen_rubric = Rubric(
        id=saved_rubric.id,
        assignment_id=assignment.id,
        title="Rubric chuẩn",
        total_points=Decimal("10.0"),
        is_frozen=True,
        version=1,
        criteria=[],
    )
    repo.get_rubric_with_criteria.side_effect = None
    repo.get_rubric_with_criteria.return_value = frozen_rubric
    repo.count_submissions.return_value = 1
    with pytest.raises(RubricFrozenException) as exc_frz:
        await svc.save_rubric(assignment.id, user, good_req)
    assert exc_frz.value.detail["code"] == "E-RUB-02"
    assert exc_frz.value.status_code == 409


# ----------------------------------------------------------------------
# T2-P-M3-03: Academic Integrity Pledge & GREEN/YELLOW/RED AI Policies
# ----------------------------------------------------------------------
def test_pledge_ai_policy_validation_green_yellow_red():
    # Unchecked checkbox always raises E-PLG-01
    with pytest.raises(IntegrityPledgeNotSignedException) as exc:
        validate_pledge_payload("GREEN", PledgeSignRequest(accepted=False))
    assert exc.value.detail["code"] == "E-PLG-01"
    assert exc.value.status_code == 422

    # GREEN allows AI tools even without long description
    validate_pledge_payload(
        "GREEN",
        PledgeSignRequest(accepted=True, self_contribution_pct=70, tools_used=["ChatGPT"], usage_description=""),
    )

    # YELLOW blocks short description when AI tools are used
    with pytest.raises(IntegrityPledgeNotSignedException):
        validate_pledge_payload(
            "YELLOW",
            PledgeSignRequest(
                accepted=True, self_contribution_pct=80, tools_used=["Claude"], usage_description="Too short"
            ),
        )
    # YELLOW passes when description >= 20 chars
    validate_pledge_payload(
        "YELLOW",
        PledgeSignRequest(
            accepted=True,
            self_contribution_pct=80,
            tools_used=["Claude"],
            usage_description="Sử dụng Claude để rà soát lỗi chính tả và gợi ý cấu trúc báo cáo.",
        ),
    )

    # RED strictly forbids any AI tool or self_contribution_pct < 100
    with pytest.raises(IntegrityPledgeNotSignedException):
        validate_pledge_payload(
            "RED",
            PledgeSignRequest(accepted=True, self_contribution_pct=100, tools_used=["Copilot"]),
        )
    with pytest.raises(IntegrityPledgeNotSignedException):
        validate_pledge_payload(
            "RED",
            PledgeSignRequest(accepted=True, self_contribution_pct=90, tools_used=[]),
        )
    # RED passes only with 0 tools and 100% self contribution
    validate_pledge_payload(
        "RED",
        PledgeSignRequest(accepted=True, self_contribution_pct=100, tools_used=[]),
    )


@pytest.mark.asyncio
async def test_pledge_service_status_and_append_only_sign():
    db = AsyncMock()
    repo = AsyncMock()
    course_svc = AsyncMock(spec=CoursePublicService)
    course_svc.assert_course_role.return_value = ContextualRole.STUDENT
    user = _make_user()
    assignment = _make_assignment(is_published=True, ai_policy_level="RED")
    repo.get_assignment.return_value = assignment
    repo.get_latest_pledge.return_value = None

    svc = PledgeService(db=db, repo=repo, course_service=course_svc)
    status_before = await svc.get_status(assignment.id, user)
    assert status_before.signed is False
    assert len(status_before.terms) == len(PLEDGE_TERMS) == 3

    async def _add_pledge(p: IntegrityPledge):
        p.signed_at = datetime.now(timezone.utc)
        return p

    repo.add_pledge.side_effect = _add_pledge
    signed = await svc.sign(
        assignment.id,
        user,
        PledgeSignRequest(accepted=True, self_contribution_pct=100, tools_used=[]),
        client_ip="127.0.0.1",
        user_agent="pytest-agent",
    )
    assert signed.signed is True
    assert signed.self_contribution_pct == 100
    repo.add_pledge.assert_awaited_once()
    saved_obj = repo.add_pledge.call_args[0][0]
    assert saved_obj.client_ip == "127.0.0.1"
    assert saved_obj.ai_policy_level == "RED"
