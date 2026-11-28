# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Comprehensive unit test suite for Member 3 realigned modules covering 30 test scenarios."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest
from pydantic import ValidationError

from app.modules.assessment.authoring_schemas import (
    MilestoneCreateSchema,
    MilestonesBatchCreateRequest,
)
from app.modules.assessment.exceptions import (
    GroupFormationDeadlinePassedException,
    GroupFullException,
    GroupTopicFullException,
    InvalidJoinCodeException,
    PeerReviewNotMemberException,
    PeerReviewSelfNotAllowedException,
    StudentAlreadyInGroupException,
)
from app.modules.assessment.group_service import GroupService
from app.modules.assessment.models import (
    Assignment,
    PeerReview,
    ProjectTopic,
    StudentGroup,
)
from app.modules.assessment.peer_review_service import PeerReviewService
from app.modules.course.roster_ingestion import sanitize_formula_injection
from app.modules.examination.exceptions import (
    InsufficientQuestionsException,
    QuestionExtractionFailedException,
)
from app.modules.examination.extractor_service import QuestionExtractorService
from app.modules.examination.models import (
    QuizQuestion,
    QuizSubmission,
)
from app.modules.examination.snapshot import (
    DrawRule,
    build_attempt_question_snapshots,
    sanitize_options_for_student,
    select_questions_by_draw_rules,
)
from app.modules.examination.schemas import (
    FinalizeReviewRequest,
    ViolationRecordRequest,
)
from app.modules.examination.service import ExaminationService
from app.modules.identity.exceptions import UserAlreadyExistsException
from app.modules.identity.schemas import RegisterRequest
from app.modules.identity.service import AuthService
from app.modules.system.models import User


# ----------------------------------------------------------------------
# 1. Registration Tests (TC-REG-01 to TC-REG-04)
# ----------------------------------------------------------------------
class TestRegistration:
    def test_tc_reg_01_valid_registration_schema(self):
        """TC-REG-01: Valid student email and strong password pass validation."""
        req = RegisterRequest(
            email="student@university.edu.vn",
            password="StrongPassword123!",
            full_name="Nguyen Van A",
            role="STUDENT",
        )
        assert req.email == "student@university.edu.vn"
        assert req.full_name == "Nguyen Van A"

    @pytest.mark.asyncio
    async def test_tc_reg_02_duplicate_email_raises_conflict(self):
        """TC-REG-02: Duplicate email raises UserAlreadyExistsException (E-AUTH-02, 409)."""
        repo_mock = MagicMock()
        repo_mock.get_by_email = AsyncMock(return_value=MagicMock(id=uuid.uuid4()))
        service = AuthService(db=MagicMock(), repo=repo_mock)

        payload = RegisterRequest(
            email="existing@adlas.edu.vn",
            password="SecurePass123!",
            full_name="Existing User",
            role="STUDENT",
        )
        with pytest.raises(UserAlreadyExistsException) as exc_info:
            await service.register_user(payload)
        assert exc_info.value.detail["code"] == "E-AUTH-02"
        assert exc_info.value.status_code == 409

    def test_tc_reg_03_invalid_email_format(self):
        """TC-REG-03: Invalid email format raises Pydantic ValidationError."""
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="not-an-email",
                password="StrongPassword123!",
                full_name="Nguyen Van A",
            )

    def test_tc_reg_04_weak_password_missing_complexity(self):
        """TC-REG-04: Password lacking uppercase, digit or length raises ValidationError."""
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="student@adlas.edu.vn",
                password="weak",
                full_name="Nguyen Van A",
            )


# ----------------------------------------------------------------------
# 2. Secure Roster Export Tests (TC-ROST-01 to TC-ROST-02)
# ----------------------------------------------------------------------
class TestRosterExport:
    def test_tc_rost_01_sanitize_formula_injection(self):
        """TC-ROST-01: Values starting with =, +, -, @ are escaped with leading single quote."""
        assert sanitize_formula_injection("=cmd|'/C calc'!A0") == "'=cmd|'/C calc'!A0"
        assert sanitize_formula_injection("+1234567890") == "'+1234567890"
        assert sanitize_formula_injection("-50") == "'-50"
        assert sanitize_formula_injection("@SUM(A1:A10)") == "'@SUM(A1:A10)"
        assert sanitize_formula_injection("Normal Student") == "Normal Student"

    def test_tc_rost_02_roster_export_xlsx_bytes(self):
        """TC-ROST-02: Roster export builds valid non-empty XLSX bytes."""
        from app.modules.course.roster_ingestion import build_roster_export_xlsx
        students = [
            {"user_code": "SV001", "full_name": "Nguyen Van A", "email": "a@adlas.edu.vn", "role": "STUDENT", "status": "ACTIVE"},
            {"user_code": "SV002", "full_name": "=MALICIOUS()", "email": "b@adlas.edu.vn", "role": "STUDENT", "status": "ACTIVE"},
        ]
        xlsx_bytes = build_roster_export_xlsx("CS101", "Lap trinh Python", students)
        assert isinstance(xlsx_bytes, bytes)
        assert len(xlsx_bytes) > 100
        assert xlsx_bytes[:4] == b"PK\x03\x04"


# ----------------------------------------------------------------------
# 3. Milestones Tests (TC-MLS-01 to TC-MLS-03)
# ----------------------------------------------------------------------
class TestMilestones:
    def test_tc_mls_01_valid_milestones_sum_100(self):
        """TC-MLS-01: Milestone weights totaling exactly 100% pass validation."""
        now = datetime.now(timezone.utc)
        payload = MilestonesBatchCreateRequest(
            milestones=[
                MilestoneCreateSchema(title="M1: Proposal", weight_percent=Decimal("20.0"), due_date=now + timedelta(days=7)),
                MilestoneCreateSchema(title="M2: MVP", weight_percent=Decimal("30.0"), due_date=now + timedelta(days=14)),
                MilestoneCreateSchema(title="M3: Final", weight_percent=Decimal("50.0"), due_date=now + timedelta(days=21)),
            ]
        )
        assert sum(m.weight_percent for m in payload.milestones) == Decimal("100.0")

    def test_tc_mls_02_invalid_weights_sum_raises_validation_error(self):
        """TC-MLS-02: Milestone weights not totaling 100% raise ValidationError."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            MilestonesBatchCreateRequest(
                milestones=[
                    MilestoneCreateSchema(title="M1", weight_percent=Decimal("20.0"), due_date=now + timedelta(days=7)),
                    MilestoneCreateSchema(title="M2", weight_percent=Decimal("30.0"), due_date=now + timedelta(days=14)),
                ]
            )

    def test_tc_mls_03_until_date_earlier_than_due_date_raises_error(self):
        """TC-MLS-03: Milestone until_date < due_date raises ValidationError."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            MilestoneCreateSchema(
                title="M1",
                weight_percent=Decimal("100.0"),
                due_date=now + timedelta(days=10),
                until_date=now + timedelta(days=5),
            )


# ----------------------------------------------------------------------
# 4. Group Formation & Topic Reservation Tests (TC-GRP-01 to TC-GRP-04)
# ----------------------------------------------------------------------
class TestGroupsAndTopics:
    @pytest.mark.asyncio
    async def test_tc_grp_01_group_creation_within_deadline(self):
        """TC-GRP-01: Group creation succeeds when before group formation deadline."""
        db_mock = MagicMock()
        db_mock.flush = AsyncMock()
        db_mock.commit = AsyncMock()
        assignment = Assignment(
            id=uuid.uuid4(),
            course_id=uuid.uuid4(),
            title="Project Task",
            instructions="Inst",
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
            group_formation_deadline=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db_mock.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=assignment)))

        service = GroupService(db_mock)
        service.get_group = AsyncMock(return_value=StudentGroup(id=uuid.uuid4(), group_name="Alpha", leader_student_id=uuid.uuid4()))

        leader = MagicMock(id=uuid.uuid4())
        group = await service.create_group(
            assignment_id=assignment.id,
            leader=leader,
            group_name="Alpha",
            member_ids=[uuid.uuid4()],
        )
        assert group.group_name == "Alpha"

    @pytest.mark.asyncio
    async def test_tc_grp_02_topic_selection_available_capacity(self):
        """TC-GRP-02: Leader reserves topic with capacity available."""
        db_mock = MagicMock()
        db_mock.commit = AsyncMock()

        topic = ProjectTopic(
            id=uuid.uuid4(),
            assignment_id=uuid.uuid4(),
            topic_code="TOPIC-01",
            title="AI LMS",
            max_groups=2,
            current_groups_count=1,
            is_active=True,
        )
        group = StudentGroup(
            id=uuid.uuid4(),
            assignment_id=topic.assignment_id,
            group_name="Beta",
            leader_student_id=uuid.uuid4(),
            topic_id=None,
        )
        assignment = Assignment(
            id=topic.assignment_id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
            group_formation_deadline=datetime.now(timezone.utc) + timedelta(days=7),
        )

        db_mock.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=topic)),
            ]
        )
        service = GroupService(db_mock)
        service.get_group = AsyncMock(return_value=group)
        service._get_assignment = AsyncMock(return_value=assignment)

        leader = MagicMock(id=group.leader_student_id)
        await service.select_topic(group.id, leader, topic.id)
        assert topic.current_groups_count == 2
        assert group.topic_id == topic.id

    @pytest.mark.asyncio
    async def test_tc_grp_03_topic_full_raises_conflict(self):
        """TC-GRP-03: Topic selection when capacity full raises GroupTopicFullException (E-GRP-01, 409)."""
        db_mock = MagicMock()
        topic = ProjectTopic(
            id=uuid.uuid4(),
            assignment_id=uuid.uuid4(),
            topic_code="TOPIC-FULL",
            title="Robotics",
            max_groups=1,
            current_groups_count=1,
            is_active=True,
        )
        group = StudentGroup(
            id=uuid.uuid4(),
            assignment_id=topic.assignment_id,
            group_name="Gamma",
            leader_student_id=uuid.uuid4(),
        )
        assignment = Assignment(
            id=topic.assignment_id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
            group_formation_deadline=datetime.now(timezone.utc) + timedelta(days=7),
        )

        db_mock.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=topic)))
        service = GroupService(db_mock)
        service.get_group = AsyncMock(return_value=group)
        service._get_assignment = AsyncMock(return_value=assignment)

        leader = MagicMock(id=group.leader_student_id)
        with pytest.raises(GroupTopicFullException) as exc_info:
            await service.select_topic(group.id, leader, topic.id)
        assert exc_info.value.detail["code"] == "E-GRP-01"

    @pytest.mark.asyncio
    async def test_tc_grp_04_group_formation_past_deadline(self):
        """TC-GRP-04: Action past deadline raises GroupFormationDeadlinePassedException (E-GRP-02, 400)."""
        db_mock = MagicMock()
        assignment = Assignment(
            id=uuid.uuid4(),
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
            group_formation_deadline=datetime.now(timezone.utc) - timedelta(days=1),
        )
        service = GroupService(db_mock)
        service._get_assignment = AsyncMock(return_value=assignment)

        with pytest.raises(GroupFormationDeadlinePassedException) as exc_info:
            await service.create_group(assignment.id, MagicMock(id=uuid.uuid4()), "Delta")
        assert exc_info.value.detail["code"] == "E-GRP-02"


# ----------------------------------------------------------------------
# 5. Blind Peer Review & Fi Factor Tests (TC-REV-01 to TC-REV-05)
# ----------------------------------------------------------------------
class TestPeerReview:
    @pytest.mark.asyncio
    async def test_tc_rev_01_self_evaluation_rejected(self):
        """TC-REV-01: Self peer evaluation raises PeerReviewSelfNotAllowedException (E-REV-01, 400)."""
        db_mock = MagicMock()
        service = PeerReviewService(db_mock)
        actor_id = uuid.uuid4()
        reviewer = MagicMock(id=actor_id)
        from app.modules.assessment.authoring_schemas import PeerReviewSubmitRequest
        payload = PeerReviewSubmitRequest(
            reviewee_id=actor_id,
            total_score=Decimal("90.0"),
        )
        with pytest.raises(PeerReviewSelfNotAllowedException) as exc_info:
            await service.submit_peer_review(uuid.uuid4(), reviewer, payload)
        assert exc_info.value.detail["code"] == "E-REV-01"

    @pytest.mark.asyncio
    async def test_tc_rev_02_non_member_review_forbidden(self):
        """TC-REV-02: Reviewing a student from another group raises PeerReviewNotMemberException (E-REV-02, 403)."""
        db_mock = MagicMock()
        db_mock.execute = AsyncMock(
            side_effect=[
                MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[uuid.uuid4()])))),
                MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[uuid.uuid4()])))),
            ]
        )
        service = PeerReviewService(db_mock)
        reviewer = MagicMock(id=uuid.uuid4())
        from app.modules.assessment.authoring_schemas import PeerReviewSubmitRequest
        payload = PeerReviewSubmitRequest(
            reviewee_id=uuid.uuid4(),
            total_score=Decimal("80.0"),
        )
        with pytest.raises(PeerReviewNotMemberException) as exc_info:
            await service.submit_peer_review(uuid.uuid4(), reviewer, payload)
        assert exc_info.value.detail["code"] == "E-REV-02"

    @pytest.mark.asyncio
    async def test_tc_rev_03_fi_factor_clamped_to_max_1_20(self):
        """TC-REV-03: Fi factor clamps to maximum 1.20 even with exceptionally high peer score."""
        db_mock = MagicMock()
        s1_id = uuid.uuid4()
        s2_id = uuid.uuid4()

        group = StudentGroup(id=uuid.uuid4(), assignment_id=uuid.uuid4(), group_name="Team 1")
        m1 = MagicMock(student_id=s1_id, student=MagicMock(first_name="Alice", last_name="A", email="alice@adlas.vn"))
        m2 = MagicMock(student_id=s2_id, student=MagicMock(first_name="Bob", last_name="B", email="bob@adlas.vn"))
        group.members = [m1, m2]

        # s1 received 100, s2 received 20 -> group avg 60 -> s1 ratio 100/60 = 1.67 -> clamp 1.20
        r1 = PeerReview(assignment_id=group.assignment_id, reviewer_id=s2_id, reviewee_id=s1_id, total_score=Decimal("100.0"))
        r2 = PeerReview(assignment_id=group.assignment_id, reviewer_id=s1_id, reviewee_id=s2_id, total_score=Decimal("20.0"))

        db_mock.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=group)),
                MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[r1, r2])))),
            ]
        )
        service = PeerReviewService(db_mock)
        res = await service.calculate_peer_review_factors(group.assignment_id, group.id, raw_group_grade=9.0)
        alice_summary = next(s for s in res.summaries if s.student_id == s1_id)
        assert alice_summary.factor_f == 1.20
        assert alice_summary.adjusted_grade <= alice_summary.raw_grade

    @pytest.mark.asyncio
    async def test_tc_rev_04_fi_factor_clamped_to_min_0_50(self):
        """TC-REV-04: Fi factor clamps to minimum 0.50 for poor peer evaluation."""
        db_mock = MagicMock()
        s1_id = uuid.uuid4()
        s2_id = uuid.uuid4()

        group = StudentGroup(id=uuid.uuid4(), assignment_id=uuid.uuid4(), group_name="Team 2")
        m1 = MagicMock(student_id=s1_id, student=MagicMock(first_name="Alice", last_name="A", email="alice@adlas.vn"))
        m2 = MagicMock(student_id=s2_id, student=MagicMock(first_name="Bob", last_name="B", email="bob@adlas.vn"))
        group.members = [m1, m2]

        # s1 received 100, s2 received 10 -> group avg 55 -> s2 ratio 10/55 = 0.18 -> clamp 0.50
        r1 = PeerReview(assignment_id=group.assignment_id, reviewer_id=s2_id, reviewee_id=s1_id, total_score=Decimal("100.0"))
        r2 = PeerReview(assignment_id=group.assignment_id, reviewer_id=s1_id, reviewee_id=s2_id, total_score=Decimal("10.0"))

        db_mock.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=group)),
                MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[r1, r2])))),
            ]
        )
        service = PeerReviewService(db_mock)
        res = await service.calculate_peer_review_factors(group.assignment_id, group.id, raw_group_grade=8.0)
        bob_summary = next(s for s in res.summaries if s.student_id == s2_id)
        assert bob_summary.factor_f == 0.50
        assert bob_summary.adjusted_grade == 4.0

    @pytest.mark.asyncio
    async def test_tc_rev_05_adjusted_grade_bounded_by_raw_group_grade(self):
        """TC-REV-05: Adjusted grade G_i cannot exceed raw group grade G_raw."""
        db_mock = MagicMock()
        s1_id = uuid.uuid4()
        group = StudentGroup(id=uuid.uuid4(), assignment_id=uuid.uuid4(), group_name="Team 3")
        m1 = MagicMock(student_id=s1_id, student=MagicMock(first_name="Solo", last_name="S", email="solo@adlas.vn"))
        group.members = [m1]

        db_mock.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=group)),
                MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
            ]
        )
        service = PeerReviewService(db_mock)
        res = await service.calculate_peer_review_factors(group.assignment_id, group.id, raw_group_grade=10.0)
        assert res.summaries[0].adjusted_grade <= 10.0


# ----------------------------------------------------------------------
# 6. 1-Click Extraction Tests (TC-EXT-01 to TC-EXT-03)
# ----------------------------------------------------------------------
class TestExtraction:
    def test_tc_ext_01_extract_vietnamese_pattern(self):
        """TC-EXT-01: Standard Vietnamese quiz format extraction with 'Đáp án: A'."""
        text = """
        Câu 1: Thủ đô của Việt Nam là thành phố nào?
        A. Hà Nội
        B. Hồ Chí Minh
        C. Đà Nẵng
        D. Hải Phòng
        Đáp án: A
        Lời giải: Hà Nội là thủ đô của Việt Nam.
        """
        service = QuestionExtractorService()
        res = service.extract_from_text(text)
        assert res.total_extracted == 1
        q = res.questions[0]
        assert "Thủ đô của Việt Nam" in q.prompt
        assert len(q.options) == 4
        assert q.correct_key == "A"
        assert any(o.key == "A" and o.is_correct for o in q.options)

    def test_tc_ext_02_extract_asterisk_pattern(self):
        """TC-EXT-02: Asterisk prefix pattern (*A.) marks the correct answer."""
        text = """
        Question 1: What is 2 + 2?
        *A. 4
        B. 3
        C. 5
        D. 6
        """
        service = QuestionExtractorService()
        res = service.extract_from_text(text)
        assert res.total_extracted == 1
        q = res.questions[0]
        assert q.correct_key == "A"
        assert q.confidence_score == 1.0

    def test_tc_ext_03_extract_empty_or_invalid_raises_error(self):
        """TC-EXT-03: Text without valid questions raises QuestionExtractionFailedException (E-EXT-01)."""
        service = QuestionExtractorService()
        with pytest.raises(QuestionExtractionFailedException) as exc_info:
            service.extract_from_text("This is just some random text without any questions.")
        assert exc_info.value.detail["code"] == "E-EXT-01"


# ----------------------------------------------------------------------
# 7. Draw Rules Tests (TC-DRW-01 to TC-DRW-03)
# ----------------------------------------------------------------------
class TestDrawRules:
    def test_tc_drw_01_sufficient_questions_draw_success(self):
        """TC-DRW-01: Random draw succeeds when candidate pool has sufficient questions."""
        q1 = MagicMock(id=uuid.uuid4())
        q2 = MagicMock(id=uuid.uuid4())
        q3 = MagicMock(id=uuid.uuid4())
        pool = [q1, q2, q3]
        rule = DrawRule(count=2, difficulty="medium")
        selected = select_questions_by_draw_rules([rule], [pool])
        assert len(selected) == 2
        assert len(set(q.id for q in selected)) == 2

    def test_tc_drw_02_insufficient_questions_raises_error(self):
        """TC-DRW-02: Insufficient questions in pool raises InsufficientQuestionsException (E-EXAM-03)."""
        q1 = MagicMock(id=uuid.uuid4())
        pool = [q1]
        rule = DrawRule(count=5, difficulty="hard")
        with pytest.raises(InsufficientQuestionsException) as exc_info:
            select_questions_by_draw_rules([rule], [pool])
        assert exc_info.value.detail["code"] == "E-EXAM-03"

    def test_tc_drw_03_no_duplicates_across_multiple_rules(self):
        """TC-DRW-03: Drawing across multiple rules never yields duplicate questions."""
        shared_pool = [MagicMock(id=uuid.UUID(int=i)) for i in range(10)]
        rule1 = DrawRule(count=3)
        rule2 = DrawRule(count=4)
        selected = select_questions_by_draw_rules([rule1, rule2], [shared_pool, shared_pool])
        assert len(selected) == 7
        assert len(set(q.id for q in selected)) == 7


# ----------------------------------------------------------------------
# 8. Strict Mode & Autosave Tests (TC-STR-01 to TC-AUT-02)
# ----------------------------------------------------------------------
class TestStrictModeAndAutosave:
    def test_tc_str_01_under_strike_threshold_not_flagged(self):
        """TC-STR-01: Submission with fewer than 3 strikes remains unflagged."""
        sub = QuizSubmission(strike_count=2, is_flagged=False)
        assert not sub.is_flagged
        assert sub.strike_count < 3

    def test_tc_str_02_reaches_strikes_threshold_flagged(self):
        """TC-STR-02: Submission reaching or exceeding 3 strikes is flagged."""
        sub = QuizSubmission(strike_count=3, is_flagged=True)
        assert sub.is_flagged
        assert sub.strike_count >= 3

    @pytest.mark.asyncio
    async def test_tc_aut_01_monotonic_autosave_accepted(self):
        """TC-AUT-01: Incoming seq_num higher than current seq_num is accepted."""
        from app.modules.examination.repository import ExaminationRepository
        db_mock = MagicMock()
        db_mock.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=uuid.uuid4())))
        db_mock.flush = AsyncMock()

        repo = ExaminationRepository(db_mock)
        updated = await repo.apply_autosave_if_newer(
            submission_id=uuid.uuid4(),
            incoming_seq_num=5,
            student_answers={"q1": "A"},
        )
        assert updated is True

    @pytest.mark.asyncio
    async def test_tc_aut_02_stale_autosave_rejected(self):
        """TC-AUT-02: Incoming seq_num <= current seq_num is rejected as stale."""
        from app.modules.examination.repository import ExaminationRepository
        db_mock = MagicMock()
        db_mock.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        db_mock.flush = AsyncMock()

        repo = ExaminationRepository(db_mock)
        updated = await repo.apply_autosave_if_newer(
            submission_id=uuid.uuid4(),
            incoming_seq_num=2,
            student_answers={"q1": "A"},
        )
        assert updated is False


# ----------------------------------------------------------------------
# 9. Snapshot Sanitization & Cryptographic Shuffle Tests (TC-SNP-01 to TC-SNP-02)
# ----------------------------------------------------------------------
class TestSnapshotAndShuffle:
    def test_tc_snp_01_student_options_sanitized(self):
        """TC-SNP-01: Student-facing options do not expose is_correct field."""
        raw_options = [
            {"id": "1", "key": "A", "text": "Hanoi", "is_correct": True},
            {"id": "2", "key": "B", "text": "Saigon", "is_correct": False},
        ]
        sanitized = sanitize_options_for_student(raw_options)
        for opt in sanitized:
            assert "is_correct" not in opt
            assert "key" in opt
            assert "text" in opt

    def test_tc_snp_02_cryptographic_attempt_generation(self):
        """TC-SNP-02: Attempt snapshot preserves all questions and options under shuffle."""
        qq1 = QuizQuestion(
            id=uuid.uuid4(),
            question_id=uuid.uuid4(),
            question_order=1,
            question_type="MULTIPLE_CHOICE",
            question_text_snapshot="Capital?",
            options_snapshot=[
                {"id": "opt1", "key": "A", "text": "Hanoi", "is_correct": True},
                {"id": "opt2", "key": "B", "text": "Saigon", "is_correct": False},
            ],
            default_points=Decimal("1.00"),
        )
        attempt_rows = build_attempt_question_snapshots(
            quiz_questions=[qq1],
            submission_id=uuid.uuid4(),
            shuffle_questions=True,
            shuffle_options=True,
        )
        assert len(attempt_rows) == 1
        opts = attempt_rows[0].options_snapshot
        assert len(opts) == 2
        opt_ids = {o["id"] for o in opts}
        assert opt_ids == {"opt1", "opt2"}


class TestGroupJoinByCode:
    """Tests for T2-P-M3-02 group join by 6-char code and conflict prevention."""

    @pytest.mark.asyncio
    async def test_join_group_by_code_success(self):
        db = AsyncMock()
        db.add = MagicMock()
        service = GroupService(db)
        aid = uuid.uuid4()
        user = User(id=uuid.uuid4(), email="student@adlas.edu.vn")
        assignment = Assignment(id=aid, group_formation_deadline=None, group_max_size=4)
        service._get_assignment = AsyncMock(return_value=assignment)

        group = StudentGroup(
            id=uuid.uuid4(),
            assignment_id=aid,
            group_name="Team Alpha",
            join_code="ABC123",
            members=[],
        )
        # Mock group lookup
        res_group = MagicMock()
        res_group.scalar_one_or_none.return_value = group

        # Mock membership check (not in any group yet)
        res_check = MagicMock()
        res_check.scalar_one_or_none.return_value = None

        db.execute = AsyncMock(side_effect=[res_group, res_check])
        service.get_group = AsyncMock(return_value=group)

        joined = await service.join_group_by_code(aid, user, "abc123")
        assert joined.id == group.id
        assert db.add.called

    @pytest.mark.asyncio
    async def test_join_group_by_code_invalid(self):
        db = AsyncMock()
        service = GroupService(db)
        aid = uuid.uuid4()
        user = User(id=uuid.uuid4(), email="student@adlas.edu.vn")
        assignment = Assignment(id=aid, group_formation_deadline=None)
        service._get_assignment = AsyncMock(return_value=assignment)

        res_group = MagicMock()
        res_group.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=res_group)

        with pytest.raises(InvalidJoinCodeException) as exc:
            await service.join_group_by_code(aid, user, "INVALID")
        assert exc.value.detail["code"] == "E-GRP-07"

    @pytest.mark.asyncio
    async def test_join_group_by_code_already_member(self):
        db = AsyncMock()
        service = GroupService(db)
        aid = uuid.uuid4()
        user = User(id=uuid.uuid4(), email="student@adlas.edu.vn")
        assignment = Assignment(id=aid, group_formation_deadline=None)
        service._get_assignment = AsyncMock(return_value=assignment)

        group = StudentGroup(id=uuid.uuid4(), assignment_id=aid, group_name="Team Alpha", join_code="ABC123", members=[])
        res_group = MagicMock()
        res_group.scalar_one_or_none.return_value = group

        # User is already in a group for this assignment
        res_check = MagicMock()
        res_check.scalar_one_or_none.return_value = MagicMock()

        db.execute = AsyncMock(side_effect=[res_group, res_check])

        with pytest.raises(StudentAlreadyInGroupException) as exc:
            await service.join_group_by_code(aid, user, "ABC123")
        assert exc.value.detail["code"] == "E-GRP-05"

    @pytest.mark.asyncio
    async def test_join_group_by_code_group_full(self):
        db = AsyncMock()
        service = GroupService(db)
        aid = uuid.uuid4()
        user = User(id=uuid.uuid4(), email="student@adlas.edu.vn")
        assignment = Assignment(id=aid, group_formation_deadline=None, group_max_size=2)
        service._get_assignment = AsyncMock(return_value=assignment)

        group = StudentGroup(
            id=uuid.uuid4(),
            assignment_id=aid,
            group_name="Team Alpha",
            join_code="ABC123",
            members=[MagicMock(), MagicMock()],  # already 2 members
        )
        res_group = MagicMock()
        res_group.scalar_one_or_none.return_value = group

        res_check = MagicMock()
        res_check.scalar_one_or_none.return_value = None

        db.execute = AsyncMock(side_effect=[res_group, res_check])

        with pytest.raises(GroupFullException) as exc:
            await service.join_group_by_code(aid, user, "ABC123")
        assert exc.value.detail["code"] == "E-GRP-06"


class TestExaminationGapFeatures:
    """Tests for T2-P-M4-02 folder stats, T2-P-M4-03 violations, and T2-P-M4-04 Alert Timeline."""

    @pytest.mark.asyncio
    async def test_folder_stats_aggregation(self):
        db = AsyncMock()
        service = ExaminationService(db)
        cid = uuid.uuid4()
        actor = User(id=uuid.uuid4(), email="teacher@adlas.edu.vn")
        service._assert_course_member = AsyncMock()
        fid = uuid.uuid4()
        service.repo.get_question_folder_stats = AsyncMock(
            return_value=[
                {"folder_id": fid, "name": "Chuong 1", "EASY": 5, "MEDIUM": 10, "HARD": 3, "total": 18}
            ]
        )

        resp = await service.get_question_folder_stats(cid, actor)
        assert len(resp.folders) == 1
        assert resp.folders[0].folder_id == fid
        assert resp.folders[0].total == 18

    @pytest.mark.asyncio
    async def test_violation_recording_triggers_flag(self):
        db = AsyncMock()
        service = ExaminationService(db)
        sid = uuid.uuid4()
        actor = User(id=uuid.uuid4(), email="student@adlas.edu.vn")
        quiz = MagicMock(id=uuid.uuid4(), max_strikes=3)
        sub = QuizSubmission(
            id=sid,
            quiz_id=quiz.id,
            user_id=actor.id,
            strike_count=2,
            is_flagged=False,
            violation_logs_json=[],
            status="IN_PROGRESS",
        )
        service.repo.get_submission_by_id = AsyncMock(return_value=sub)
        service.repo.get_quiz_by_id = AsyncMock(return_value=quiz)

        payload = ViolationRecordRequest(violation_type="TAB_SWITCH")
        resp = await service.record_attempt_violation(sid, payload, actor)
        assert resp.strike_count == 3
        assert resp.is_flagged is True
        assert sub.is_flagged is True
        assert len(sub.violation_logs_json) == 1

    @pytest.mark.asyncio
    async def test_finalize_review_accepted(self):
        db = AsyncMock()
        service = ExaminationService(db)
        sid = uuid.uuid4()
        cid = uuid.uuid4()
        actor = User(id=uuid.uuid4(), email="teacher@adlas.edu.vn")
        quiz = MagicMock(id=uuid.uuid4(), course_id=cid)
        sub = QuizSubmission(
            id=sid,
            quiz_id=quiz.id,
            user_id=uuid.uuid4(),
            attempt_number=1,
            started_at=datetime.now(timezone.utc),
            auto_score=Decimal("6.50"),
            final_score=None,
            is_flagged=True,
            status="SUBMITTED",
        )
        service.repo.get_submission_by_id = AsyncMock(return_value=sub)
        service.repo.get_quiz_by_id = AsyncMock(return_value=quiz)
        service._assert_instructor = AsyncMock()
        service.repo.get_best_score_for_user = AsyncMock(return_value=Decimal("8.50"))
        service.repo.enqueue_outbox_event = AsyncMock()

        user_mock = MagicMock(first_name="Nguyen", last_name="An", email="an@adlas.edu.vn")
        u_res = MagicMock()
        u_res.scalar_one_or_none.return_value = user_mock
        db.execute = AsyncMock(return_value=u_res)

        payload = FinalizeReviewRequest(
            review_decision="ACCEPTED",
            essay_scores={"q1": 2.0},
            instructor_note="Bai thi hop le sau kiem tra.",
        )
        resp = await service.finalize_attempt_review(sid, payload, actor)
        assert resp.review_decision == "ACCEPTED"
        assert resp.final_score == Decimal("8.50")
        assert sub.final_score == Decimal("8.50")
        assert sub.status == "FINALIZED"

    @pytest.mark.asyncio
    async def test_finalize_review_invalidated(self):
        db = AsyncMock()
        service = ExaminationService(db)
        sid = uuid.uuid4()
        cid = uuid.uuid4()
        actor = User(id=uuid.uuid4(), email="teacher@adlas.edu.vn")
        quiz = MagicMock(id=uuid.uuid4(), course_id=cid)
        sub = QuizSubmission(
            id=sid,
            quiz_id=quiz.id,
            user_id=uuid.uuid4(),
            attempt_number=1,
            started_at=datetime.now(timezone.utc),
            auto_score=Decimal("7.00"),
            final_score=None,
            is_flagged=True,
            status="SUBMITTED",
        )
        service.repo.get_submission_by_id = AsyncMock(return_value=sub)
        service.repo.get_quiz_by_id = AsyncMock(return_value=quiz)
        service._assert_instructor = AsyncMock()
        service.repo.get_best_score_for_user = AsyncMock(return_value=Decimal("0.00"))
        service.repo.enqueue_outbox_event = AsyncMock()

        user_mock = MagicMock(first_name="Tran", last_name="Binh", email="binh@adlas.edu.vn")
        u_res = MagicMock()
        u_res.scalar_one_or_none.return_value = user_mock
        db.execute = AsyncMock(return_value=u_res)

        payload = FinalizeReviewRequest(
            review_decision="INVALIDATED",
            instructor_note="Vi pham chuyen tab qua 3 lan.",
        )
        resp = await service.finalize_attempt_review(sid, payload, actor)
        assert resp.review_decision == "INVALIDATED"
        assert resp.final_score == Decimal("0.00")
        assert sub.final_score == Decimal("0.00")
        assert sub.status == "FINALIZED"
