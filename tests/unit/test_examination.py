# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Unit tests for Examination pure domain engines and admin rules (T2-P-M4-01 & T2-P-M4-02)."""

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import random
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest
from app.modules.course.enums import BloomLevel, ContextualRole
from app.modules.examination.enums import (
    GradeReleasePolicy,
    QuestionType,
    QuizStatus,
    RegradeScope,
    RegradeStatus,
    SecurityMode,
    SubmissionStatus,
)
from app.modules.examination.exceptions import (
    ExamAiLockedException,
    ExamClosedException,
    ExaminationForbiddenException,
    ExaminationValidationException,
    InsufficientQuestionsException,
    InvalidExamWindowException,
    IpNotAllowedException,
    RegradeWindowExpiredException,
)
from app.modules.examination.models import (
    Question,
    QuestionBank,
    Quiz,
    QuizAttemptQuestion,
    QuizQuestion,
    QuizRegrade,
    QuizSubmission,
)
from app.modules.examination.public_api import ExaminationPublicService
from app.modules.examination.schemas import (
    AttemptStartRequest,
    AutosaveRequest,
    QuizCreate,
    QuizMatrixRuleSchema,
    QuizSettingsUpdate,
    RegradeCreateRequest,
    RegradeReviewRequest,
)
from app.modules.examination.scoring import (
    compute_quiz_score_scale_10,
    score_multi_select,
    score_question_from_snapshot,
    score_single_choice,
)
from app.modules.examination.security_rules import (
    PASSCODE_ALPHABET,
    assert_ip_allowed,
    assert_within_grace_period,
    compute_effective_deadline,
    generate_passcode,
    is_within_grace_period,
    validate_cidr_expression,
    validate_exam_window,
    validate_ip_in_cidr,
)
from app.modules.examination.service import (
    ExaminationService,
    resolve_grade_release_window,
)
from app.modules.examination.snapshot import (
    MatrixRule,
    build_attempt_question_snapshots,
    build_quiz_question_snapshots,
    sanitize_options_for_student,
    select_questions_by_matrix,
    shuffle_options_snapshot,
)


def _make_question(
    bank_id: uuid.UUID,
    text: str = "2 + 2 = ?",
    bloom: str = "UNDERSTAND",
    qtype: str = "MULTIPLE_CHOICE",
    points: Decimal = Decimal("1.00"),
) -> Question:
    now = datetime.now(timezone.utc)
    return Question(
        id=uuid.uuid4(),
        bank_id=bank_id,
        lo_id=None,
        bloom_level=bloom,
        question_text=text,
        question_type=qtype,
        default_points=points,
        options=[
            {"id": "opt1", "key": "A", "text": "3", "is_correct": False},
            {"id": "opt2", "key": "B", "text": "4", "is_correct": True},
            {"id": "opt3", "key": "C", "text": "5", "is_correct": False},
            {"id": "opt4", "key": "D", "text": "6", "is_correct": False},
        ],
        explanation="2 + 2 equals 4.",
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def _make_user(system_role: str = "USER") -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), system_role=system_role)


# ============================================================================
# 1. Scoring Engine Tests (BR-EXAM-MULTI & BR-13)
# ============================================================================
class TestScoringEngine:
    def test_single_choice_correct_and_incorrect(self):
        assert score_single_choice("B", ["B"], Decimal("2.00")) == Decimal("2.00")
        assert score_single_choice(["B"], ["B"], Decimal("2.00")) == Decimal("2.00")
        assert score_single_choice("A", ["B"], Decimal("2.00")) == Decimal("0")
        assert score_single_choice(["A", "B"], ["B"], Decimal("2.00")) == Decimal("0")
        assert score_single_choice(None, ["B"], Decimal("2.00")) == Decimal("0")

    def test_multi_select_exact_all_correct(self):
        # k=2 (A, B), m=2 (C, D), selected={A, B} -> r=2, w=0 -> 2.0 * (2/2 - 0/2) = 2.0
        pts = score_multi_select(["A", "B"], ["A", "B"], ["A", "B", "C", "D"], Decimal("2.0"))
        assert pts == Decimal("2.0")

    def test_multi_select_selecting_all_options_yields_zero(self):
        # BR-EXAM-MULTI anti-guessing invariant: r=k, w=m => (k/k - m/m) = 0
        pts = score_multi_select(
            ["A", "B", "C", "D"],
            ["A", "B"],
            ["A", "B", "C", "D"],
            Decimal("2.0"),
        )
        assert pts == Decimal("0")

    def test_multi_select_partial_and_penalty_floor_zero(self):
        # k=2 (A, B), m=2 (C, D), selected={A} -> r=1, w=0 -> 2.0 * (1/2 - 0) = 1.0
        assert score_multi_select(["A"], ["A", "B"], ["A", "B", "C", "D"], Decimal("2.0")) == Decimal("1.0")
        # selected={A, C} -> r=1, w=1 -> 2.0 * (1/2 - 1/2) = 0
        assert score_multi_select(["A", "C"], ["A", "B"], ["A", "B", "C", "D"], Decimal("2.0")) == Decimal("0")
        # selected={C, D} -> r=0, w=2 -> clamped at 0 (never negative)
        assert score_multi_select(["C", "D"], ["A", "B"], ["A", "B", "C", "D"], Decimal("2.0")) == Decimal("0")
        # k=2, m=3 (5 options), selected={A, B, C} -> 3.0 * (2/2 - 1/3) = 2.0
        assert score_multi_select(
            ["A", "B", "C"],
            ["A", "B"],
            ["A", "B", "C", "D", "E"],
            Decimal("3.0"),
        ) == Decimal("2.0")

    def test_score_question_from_snapshot(self):
        snapshot_opts = [
            {"id": "1", "key": "A", "text": "x", "is_correct": True},
            {"id": "2", "key": "B", "text": "y", "is_correct": True},
            {"id": "3", "key": "C", "text": "z", "is_correct": False},
            {"id": "4", "key": "D", "text": "w", "is_correct": False},
        ]
        assert score_question_from_snapshot(
            QuestionType.MULTI_SELECT.value,
            snapshot_opts,
            ["A"],
            Decimal("2.0"),
        ) == Decimal("1.0")

    def test_scale_10_round_half_up_br13(self):
        # 17 / 20 * 10 = 8.5 -> 8.5
        assert compute_quiz_score_scale_10([Decimal("17")], [Decimal("20")]) == Decimal("8.5")
        # 2.55 / 10 * 10 = 2.55 -> ROUND_HALF_UP => 2.6 (Python banker's rounding would give 2.6, check 2.45 -> 2.5!)
        assert compute_quiz_score_scale_10([Decimal("2.45")], [Decimal("10")]) == Decimal("2.5")
        assert compute_quiz_score_scale_10([Decimal("2.55")], [Decimal("10")]) == Decimal("2.6")
        assert compute_quiz_score_scale_10([], []) == Decimal("0.0")


# ============================================================================
# 2. Security & Timing Rules Tests (BR-08, BR-AUTOSAVE-02, E-SEC-01..03)
# ============================================================================
class TestSecurityRules:
    def test_validate_exam_window_valid_and_e_sec_01(self):
        t0 = datetime(2026, 11, 25, 8, 0, tzinfo=timezone.utc)
        validate_exam_window(t0, t0 + timedelta(minutes=45), 45)
        validate_exam_window(t0, t0 + timedelta(minutes=90), 45)

        with pytest.raises(InvalidExamWindowException) as exc:
            validate_exam_window(t0, t0 + timedelta(minutes=30), 45)
        assert exc.value.detail["code"] == "E-SEC-01"

        with pytest.raises(InvalidExamWindowException):
            validate_exam_window(t0, t0, 45)

    def test_compute_effective_deadline_br08_late_shrinkage(self):
        until = datetime(2026, 11, 25, 9, 0, tzinfo=timezone.utc)
        # Early start: full 45 mins
        early = datetime(2026, 11, 25, 8, 0, tzinfo=timezone.utc)
        assert compute_effective_deadline(early, 45, until) == early + timedelta(minutes=45)

        # Late entry at 8:40 -> shrunk to 9:00 (only 20 mins)
        late = datetime(2026, 11, 25, 8, 40, tzinfo=timezone.utc)
        assert compute_effective_deadline(late, 45, until) == until

        # Past close -> E-EXAM-CLOSED
        with pytest.raises(ExamClosedException) as exc:
            compute_effective_deadline(until, 45, until)
        assert exc.value.detail["code"] == "E-EXAM-CLOSED"

    def test_grace_period_5_minutes_br_autosave_02(self):
        exp = datetime(2026, 11, 25, 9, 0, tzinfo=timezone.utc)
        assert is_within_grace_period(exp + timedelta(minutes=5), exp) is True
        assert is_within_grace_period(exp + timedelta(minutes=5, seconds=1), exp) is False

        with pytest.raises(ExamClosedException) as exc:
            assert_within_grace_period(exp + timedelta(minutes=6), exp)
        assert exc.value.detail["code"] == "E-EXAM-CLOSED"

    def test_cidr_validation_and_ip_matching_e_sec_03(self):
        assert validate_cidr_expression("10.20.0.0/16, 192.168.1.50") == "10.20.0.0/16, 192.168.1.50/32"
        assert validate_ip_in_cidr("10.20.5.12", "10.20.0.0/16") is True
        assert validate_ip_in_cidr("172.16.0.1", "10.20.0.0/16") is False
        assert validate_ip_in_cidr("172.16.0.1", None) is True

        with pytest.raises(IpNotAllowedException) as exc:
            assert_ip_allowed("172.16.0.1", "10.20.0.0/16")
        assert exc.value.detail["code"] == "E-SEC-03"

        with pytest.raises(ExaminationValidationException):
            validate_cidr_expression("not-an-ip-cidr")

    def test_generate_passcode_6_chars_alphabet(self):
        code = generate_passcode()
        assert len(code) == 6
        assert all(ch in PASSCODE_ALPHABET for ch in code)


# ============================================================================
# 3. Snapshot & Cryptographic Shuffle Tests (BR-EXAM-01, BR-EXAM-02, E-EXAM-03)
# ============================================================================
class TestSnapshotEngine:
    def test_matrix_selection_and_e_exam_03(self):
        bank_id = uuid.uuid4()
        pool = [_make_question(bank_id, text=f"Q{i}") for i in range(5)]
        rule = MatrixRule(bank_id=bank_id, count=3, bloom_level="UNDERSTAND")

        picked = select_questions_by_matrix([rule], [pool], rng=random.Random(42))
        assert len(picked) == 3
        assert len({q.id for q in picked}) == 3

        # Requesting more than available raises E-EXAM-03
        too_many = MatrixRule(bank_id=bank_id, count=6)
        with pytest.raises(InsufficientQuestionsException) as exc:
            select_questions_by_matrix([too_many], [pool])
        assert exc.value.detail["code"] == "E-EXAM-03"
        assert exc.value.detail["requested"] == 6
        assert exc.value.detail["available"] == 5

    def test_tier1_snapshot_immutability_after_bank_mutation(self):
        bank_id = uuid.uuid4()
        quiz_id = uuid.uuid4()
        q = _make_question(bank_id, text="Original question text")

        snapshots = build_quiz_question_snapshots([q], quiz_id=quiz_id)
        assert len(snapshots) == 1

        # Mutate source question in bank after freezing snapshot
        q.question_text = "Mutated question text"
        q.options[1]["is_correct"] = False
        q.options[0]["is_correct"] = True

        # Frozen Tier-1 snapshot MUST remain completely unchanged (BR-EXAM-01)
        assert snapshots[0].question_text_snapshot == "Original question text"
        assert snapshots[0].options_snapshot[1]["is_correct"] is True
        assert snapshots[0].options_snapshot[0]["is_correct"] is False

    def test_tier2_attempt_shuffle_and_sanitization(self):
        bank_id = uuid.uuid4()
        quiz_id = uuid.uuid4()
        questions = [_make_question(bank_id, text=f"Question {i}") for i in range(6)]
        tier1 = build_quiz_question_snapshots(questions, quiz_id=quiz_id)

        tier2_a = build_attempt_question_snapshots(
            tier1,
            submission_id=uuid.uuid4(),
            shuffle_questions=True,
            shuffle_options=True,
            rng=random.Random(1),
        )
        tier2_b = build_attempt_question_snapshots(
            tier1,
            submission_id=uuid.uuid4(),
            shuffle_questions=True,
            shuffle_options=True,
            rng=random.Random(99),
        )
        assert [q.question_order for q in tier2_a] == [1, 2, 3, 4, 5, 6]
        assert [q.question_id for q in tier2_a] != [q.question_id for q in tier2_b]

        # Display keys reassigned cleanly to A, B, C, D after shuffle
        shuffled = shuffle_options_snapshot(tier1[0].options_snapshot, True, rng=random.Random(7))
        assert [o["key"] for o in shuffled] == ["A", "B", "C", "D"]
        assert sum(1 for o in shuffled if o["is_correct"]) == 1

        # Sanitization strips is_correct completely
        sanitized = sanitize_options_for_student(shuffled)
        assert all("is_correct" not in o for o in sanitized)


# ============================================================================
# 4. Admin Service Rules Tests (Soft Delete, Student Answer Hiding, Settings)
# ============================================================================
class TestExaminationAdminServiceRules:
    def test_soft_delete_vs_hard_delete_based_on_snapshot(self):
        course_id = uuid.uuid4()
        bank_id = uuid.uuid4()
        actor = _make_user()
        q = _make_question(bank_id)
        bank = QuestionBank(id=bank_id, course_id=course_id, category_name="Ch 1")

        db = MagicMock()
        db.flush = AsyncMock()
        repo = MagicMock()
        repo.get_question_by_id = AsyncMock(return_value=q)
        repo.get_question_bank_by_id = AsyncMock(return_value=bank)
        repo.delete_question_respecting_snapshot = AsyncMock(return_value=True)

        course_public = MagicMock()
        course_public.assert_course_role = AsyncMock(return_value=ContextualRole.INSTRUCTOR)

        svc = ExaminationService(db=db, repo=repo, course_public=course_public)
        res = asyncio.run(svc.delete_question(q.id, actor))
        assert res.soft_deleted is True
        assert res.question_id == q.id

    def test_student_get_quiz_detail_hides_answers_and_passcode(self):
        course_id = uuid.uuid4()
        quiz_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        quiz = Quiz(
            id=quiz_id,
            course_id=course_id,
            title="Midterm Exam",
            time_limit_mins=45,
            available_from=now,
            available_until=now + timedelta(hours=2),
            passcode="AB12CD",
            ip_filter_range="10.0.0.0/8",
            grade_release_policy=GradeReleasePolicy.MANUAL.value,
            is_ai_locked=True,
            status=QuizStatus.PUBLISHED.value,
            security_mode=SecurityMode.CONTROLLED.value,
            max_attempts=1,
            shuffle_questions=True,
            shuffle_options=True,
            snapshot_mode=True,
            matrix_config=[],
            created_at=now,
            updated_at=now,
        )
        qq = QuizQuestion(
            id=uuid.uuid4(),
            quiz_id=quiz_id,
            question_id=uuid.uuid4(),
            question_order=1,
            question_type=QuestionType.MULTIPLE_CHOICE.value,
            question_text_snapshot="Capital of Vietnam?",
            options_snapshot=[
                {"id": "1", "key": "A", "text": "Hanoi", "is_correct": True},
                {"id": "2", "key": "B", "text": "Hue", "is_correct": False},
            ],
            explanation_snapshot="Hanoi is the capital.",
            default_points=Decimal("1.00"),
            created_at=now,
        )

        db = MagicMock()
        repo = MagicMock()
        repo.get_quiz_by_id = AsyncMock(return_value=quiz)
        repo.list_quiz_questions = AsyncMock(return_value=[qq])
        course_public = MagicMock()
        course_public.assert_course_role = AsyncMock(return_value=ContextualRole.STUDENT)

        svc = ExaminationService(db=db, repo=repo, course_public=course_public)
        detail = asyncio.run(svc.get_quiz_detail(quiz_id, _make_user()))

        assert detail.has_passcode is True
        assert detail.passcode is None
        assert detail.ip_filter_range is None
        assert detail.questions[0].explanation_snapshot is None
        assert all("is_correct" not in opt for opt in detail.questions[0].options_snapshot)

        # Student cannot view DRAFT quiz
        quiz.status = QuizStatus.DRAFT.value
        with pytest.raises(ExaminationForbiddenException):
            asyncio.run(svc.get_quiz_detail(quiz_id, _make_user()))

    def test_update_quiz_settings_rejects_e_sec_01_and_invalid_attempts(self):
        course_id = uuid.uuid4()
        quiz_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        quiz = Quiz(
            id=quiz_id,
            course_id=course_id,
            title="Quiz 1",
            time_limit_mins=45,
            available_from=now,
            available_until=now + timedelta(hours=2),
            status=QuizStatus.DRAFT.value,
            security_mode=SecurityMode.CONTROLLED.value,
            max_attempts=1,
            grade_release_policy=GradeReleasePolicy.AFTER_CLOSE.value,
            is_ai_locked=True,
            shuffle_questions=True,
            shuffle_options=True,
            snapshot_mode=True,
            matrix_config=[],
            created_at=now,
            updated_at=now,
        )

        db = MagicMock()
        db.flush = AsyncMock()
        repo = MagicMock()
        repo.get_quiz_by_id = AsyncMock(return_value=quiz)
        course_public = MagicMock()
        course_public.assert_course_role = AsyncMock(return_value=ContextualRole.INSTRUCTOR)
        svc = ExaminationService(db=db, repo=repo, course_public=course_public)

        # Window shorter than time_limit_mins -> E-SEC-01
        bad_window = QuizSettingsUpdate(
            time_limit_mins=60,
            available_from=now,
            available_until=now + timedelta(minutes=30),
        )
        with pytest.raises(InvalidExamWindowException) as exc:
            asyncio.run(svc.update_quiz_settings(quiz_id, bad_window, _make_user()))
        assert exc.value.detail["code"] == "E-SEC-01"

        # CONTROLLED mode with max_attempts > 1 -> E-2 validation error
        bad_attempts = QuizSettingsUpdate(
            time_limit_mins=30,
            available_from=now,
            available_until=now + timedelta(hours=1),
            security_mode=SecurityMode.CONTROLLED,
            max_attempts=3,
        )
        with pytest.raises(ExaminationValidationException):
            asyncio.run(svc.update_quiz_settings(quiz_id, bad_attempts, _make_user()))

    def test_create_quiz_matrix_raises_e_exam_03_when_insufficient(self):
        course_id = uuid.uuid4()
        bank_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        db = MagicMock()
        repo = MagicMock()
        repo.get_question_bank_by_id = AsyncMock(
            return_value=QuestionBank(id=bank_id, course_id=course_id, category_name="Ch 1")
        )
        repo.list_active_questions_for_matrix = AsyncMock(
            return_value=[_make_question(bank_id)]
        )
        course_public = MagicMock()
        course_public.assert_course_role = AsyncMock(return_value=ContextualRole.INSTRUCTOR)

        svc = ExaminationService(db=db, repo=repo, course_public=course_public)
        payload = QuizCreate(
            title="Insufficient Bank Quiz",
            time_limit_mins=30,
            available_from=now,
            available_until=now + timedelta(hours=1),
            matrix_config=[
                QuizMatrixRuleSchema(
                    bank_id=bank_id,
                    bloom_level=BloomLevel.UNDERSTAND,
                    count=5,
                )
            ],
        )
        with pytest.raises(InsufficientQuestionsException) as exc:
            asyncio.run(svc.create_quiz(course_id, payload, _make_user()))
        assert exc.value.detail["code"] == "E-EXAM-03"


# ============================================================================
# 5. Exam Session, Resume, Autosave seq_num, Grade Release, 48h & ENTIRE_CLASS
# ============================================================================
class TestExamTakingAndRegradeRules:
    def test_resume_exam_returns_existing_in_progress_session(self):
        course_id = uuid.uuid4()
        quiz_id = uuid.uuid4()
        student = _make_user()
        now = datetime(2026, 11, 25, 10, 0, tzinfo=timezone.utc)

        quiz = Quiz(
            id=quiz_id,
            course_id=course_id,
            title="Live Exam",
            time_limit_mins=45,
            available_from=now - timedelta(minutes=10),
            available_until=now + timedelta(hours=1),
            passcode="XYZ123",
            grade_release_policy=GradeReleasePolicy.IMMEDIATE.value,
            is_ai_locked=True,
            status=QuizStatus.PUBLISHED.value,
            security_mode=SecurityMode.CONTROLLED.value,
            max_attempts=1,
            shuffle_questions=True,
            shuffle_options=True,
            snapshot_mode=True,
            matrix_config=[],
            created_at=now,
            updated_at=now,
        )
        sub_id = uuid.uuid4()
        aq_id = uuid.uuid4()
        existing_sub = QuizSubmission(
            id=sub_id,
            quiz_id=quiz_id,
            user_id=student.id,
            attempt_number=1,
            started_at=now - timedelta(minutes=5),
            expires_at=now + timedelta(minutes=40),
            seq_num=7,
            student_answers={str(aq_id): "A"},
            flagged_questions=[str(aq_id)],
            status=SubmissionStatus.IN_PROGRESS.value,
        )
        aq = QuizAttemptQuestion(
            id=aq_id,
            submission_id=sub_id,
            question_order=1,
            question_type=QuestionType.MULTIPLE_CHOICE.value,
            question_text="Resume Q1",
            options_snapshot=[
                {"id": "1", "key": "A", "text": "Yes", "is_correct": True},
                {"id": "2", "key": "B", "text": "No", "is_correct": False},
            ],
            default_points=Decimal("1.00"),
        )

        db = MagicMock()
        repo = MagicMock()
        repo.get_quiz_by_id = AsyncMock(return_value=quiz)
        repo.get_in_progress_submission = AsyncMock(return_value=existing_sub)
        repo.list_attempt_questions = AsyncMock(return_value=[aq])
        course_public = MagicMock()
        course_public.assert_course_role = AsyncMock(return_value=ContextualRole.STUDENT)

        svc = ExaminationService(db=db, repo=repo, course_public=course_public)
        res = asyncio.run(
            svc.start_attempt(
                quiz_id=quiz_id,
                payload=AttemptStartRequest(passcode="XYZ123"),
                actor=student,
                now=now,
            )
        )
        assert res.resumed is True
        assert res.submission_id == sub_id
        assert res.seq_num == 7
        assert res.remaining_seconds == 2400
        assert res.student_answers == {str(aq_id): "A"}
        assert all("is_correct" not in o for o in res.questions[0].options_snapshot)

    def test_autosave_monotonic_seq_num_and_5_minute_grace_period(self):
        student = _make_user()
        now = datetime(2026, 11, 25, 10, 0, tzinfo=timezone.utc)
        sub = QuizSubmission(
            id=uuid.uuid4(),
            quiz_id=uuid.uuid4(),
            user_id=student.id,
            attempt_number=1,
            started_at=now - timedelta(minutes=45),
            expires_at=now,
            seq_num=5,
            student_answers={"q1": "A"},
            flagged_questions=[],
            tab_blur_count=0,
            fullscreen_exit_count=0,
            violation_logs=[],
            status=SubmissionStatus.IN_PROGRESS.value,
        )

        db = MagicMock()
        db.refresh = AsyncMock()
        repo = MagicMock()
        repo.get_submission_by_id = AsyncMock(return_value=sub)
        repo.apply_autosave_if_newer = AsyncMock(return_value=False)

        svc = ExaminationService(db=db, repo=repo, course_public=MagicMock())

        # Stale seq_num=4 within 5-minute grace period -> accepted=False, preserves seq_num=5
        stale_res = asyncio.run(
            svc.autosave_attempt(
                submission_id=sub.id,
                payload=AutosaveRequest(seq_num=4, answers={"q1": "B"}),
                actor=student,
                now=now + timedelta(minutes=3),
            )
        )
        assert stale_res.accepted is False
        assert stale_res.seq_num == 5

        # Past 5-minute grace period -> E-EXAM-CLOSED
        with pytest.raises(ExamClosedException) as exc:
            asyncio.run(
                svc.autosave_attempt(
                    submission_id=sub.id,
                    payload=AutosaveRequest(seq_num=6, answers={"q1": "C"}),
                    actor=student,
                    now=now + timedelta(minutes=5, seconds=1),
                )
            )
        assert exc.value.detail["code"] == "E-EXAM-CLOSED"

    def test_three_grade_release_policies_and_48h_regrade_window(self):
        t_submit = datetime(2026, 11, 25, 9, 0, tzinfo=timezone.utc)
        t_close = datetime(2026, 11, 25, 11, 0, tzinfo=timezone.utc)
        t_pub = datetime(2026, 11, 26, 8, 0, tzinfo=timezone.utc)

        # 1. IMMEDIATE -> visible right at submit, deadline = submit + 48h
        w_imm = resolve_grade_release_window(
            GradeReleasePolicy.IMMEDIATE.value,
            submitted_at=t_submit,
            available_until=t_close,
            grades_published_at=None,
            now=t_submit + timedelta(hours=1),
        )
        assert w_imm.grades_visible is True
        assert w_imm.can_request_regrade is True
        assert w_imm.regrade_deadline == t_submit + timedelta(hours=48)

        # 2. AFTER_CLOSE -> hidden before available_until, visible after
        w_before_close = resolve_grade_release_window(
            GradeReleasePolicy.AFTER_CLOSE.value,
            submitted_at=t_submit,
            available_until=t_close,
            grades_published_at=None,
            now=t_close - timedelta(minutes=10),
        )
        assert w_before_close.grades_visible is False
        assert w_before_close.can_request_regrade is False

        w_after_close = resolve_grade_release_window(
            GradeReleasePolicy.AFTER_CLOSE.value,
            submitted_at=t_submit,
            available_until=t_close,
            grades_published_at=None,
            now=t_close + timedelta(hours=2),
        )
        assert w_after_close.grades_visible is True
        assert w_after_close.regrade_deadline == t_close + timedelta(hours=48)

        # 3. MANUAL -> hidden while grades_published_at is None; expires after 48h from grades_published_at
        w_manual_wait = resolve_grade_release_window(
            GradeReleasePolicy.MANUAL.value,
            submitted_at=t_submit,
            available_until=t_close,
            grades_published_at=None,
            now=t_pub,
        )
        assert w_manual_wait.grades_visible is False

        w_manual_expired = resolve_grade_release_window(
            GradeReleasePolicy.MANUAL.value,
            submitted_at=t_submit,
            available_until=t_close,
            grades_published_at=t_pub,
            now=t_pub + timedelta(hours=48, seconds=1),
        )
        assert w_manual_expired.grades_visible is True
        assert w_manual_expired.can_request_regrade is False

    def test_create_regrade_after_48h_raises_e_reg_01(self):
        student = _make_user()
        t_pub = datetime(2026, 11, 25, 8, 0, tzinfo=timezone.utc)
        quiz = Quiz(
            id=uuid.uuid4(),
            course_id=uuid.uuid4(),
            title="Manual Quiz",
            time_limit_mins=30,
            available_from=t_pub - timedelta(hours=2),
            available_until=t_pub - timedelta(hours=1),
            grade_release_policy=GradeReleasePolicy.MANUAL.value,
            grades_published_at=t_pub,
            status=QuizStatus.PUBLISHED.value,
            security_mode=SecurityMode.CONTROLLED.value,
            max_attempts=1,
            is_ai_locked=True,
            shuffle_questions=True,
            shuffle_options=True,
            snapshot_mode=True,
            matrix_config=[],
            created_at=t_pub,
            updated_at=t_pub,
        )
        sub = QuizSubmission(
            id=uuid.uuid4(),
            quiz_id=quiz.id,
            user_id=student.id,
            attempt_number=1,
            started_at=t_pub - timedelta(hours=2),
            submitted_at=t_pub - timedelta(hours=1, minutes=30),
            auto_score=Decimal("7.0"),
            final_score=Decimal("7.0"),
            status=SubmissionStatus.AUTO_GRADED.value,
        )

        repo = MagicMock()
        repo.get_submission_by_id = AsyncMock(return_value=sub)
        repo.get_quiz_by_id = AsyncMock(return_value=quiz)
        svc = ExaminationService(db=MagicMock(), repo=repo, course_public=MagicMock())

        with pytest.raises(RegradeWindowExpiredException) as exc:
            asyncio.run(
                svc.create_regrade_request(
                    submission_id=sub.id,
                    payload=RegradeCreateRequest(
                        attempt_question_id=uuid.uuid4(),
                        student_reason="Ly do phuc khao hop le co tren 30 ky tu de kiem tra han 48h.",
                    ),
                    actor=student,
                    now=t_pub + timedelta(hours=48, minutes=1),
                )
            )
        assert exc.value.detail["code"] == "E-REG-01"

    def test_entire_class_regrade_updates_tier1_tier2_rescores_all_and_emits_outbox(self):
        course_id = uuid.uuid4()
        quiz_id = uuid.uuid4()
        qq_id = uuid.uuid4()
        q_id = uuid.uuid4()
        instructor = _make_user()
        now = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)

        quiz = Quiz(
            id=quiz_id,
            course_id=course_id,
            title="Midterm",
            time_limit_mins=30,
            available_from=now - timedelta(hours=3),
            available_until=now - timedelta(hours=2),
            grade_release_policy=GradeReleasePolicy.IMMEDIATE.value,
            status=QuizStatus.PUBLISHED.value,
            security_mode=SecurityMode.CONTROLLED.value,
            max_attempts=1,
            is_ai_locked=True,
            shuffle_questions=True,
            shuffle_options=True,
            snapshot_mode=True,
            matrix_config=[],
            created_at=now,
            updated_at=now,
        )
        tier1_qq = QuizQuestion(
            id=qq_id,
            quiz_id=quiz_id,
            question_id=q_id,
            question_order=1,
            question_type=QuestionType.MULTIPLE_CHOICE.value,
            question_text_snapshot="Binary search complexity?",
            options_snapshot=[
                {"id": "opt_wrong", "key": "A", "text": "O(n)", "is_correct": True},
                {"id": "opt_right", "key": "B", "text": "O(log n)", "is_correct": False},
            ],
            default_points=Decimal("1.00"),
            created_at=now,
        )

        # Two students with different shuffled keys for opt_right (SV1 has B, SV2 has A)
        sub1_id, sub2_id = uuid.uuid4(), uuid.uuid4()
        aq1_id, aq2_id = uuid.uuid4(), uuid.uuid4()
        sub1 = QuizSubmission(
            id=sub1_id,
            quiz_id=quiz_id,
            user_id=uuid.uuid4(),
            attempt_number=1,
            student_answers={str(aq1_id): "B"},
            auto_score=Decimal("0.0"),
            final_score=Decimal("0.0"),
            status=SubmissionStatus.REGRADE_PENDING.value,
        )
        sub2 = QuizSubmission(
            id=sub2_id,
            quiz_id=quiz_id,
            user_id=uuid.uuid4(),
            attempt_number=1,
            student_answers={str(aq2_id): "A"},
            auto_score=Decimal("0.0"),
            final_score=Decimal("0.0"),
            status=SubmissionStatus.REGRADE_PENDING.value,
        )
        aq1 = QuizAttemptQuestion(
            id=aq1_id,
            submission_id=sub1_id,
            quiz_question_id=qq_id,
            question_id=q_id,
            question_order=1,
            question_type=QuestionType.MULTIPLE_CHOICE.value,
            question_text="Binary search complexity?",
            options_snapshot=[
                {"id": "opt_wrong", "key": "A", "text": "O(n)", "is_correct": True},
                {"id": "opt_right", "key": "B", "text": "O(log n)", "is_correct": False},
            ],
            default_points=Decimal("1.00"),
        )
        aq2 = QuizAttemptQuestion(
            id=aq2_id,
            submission_id=sub2_id,
            quiz_question_id=qq_id,
            question_id=q_id,
            question_order=1,
            question_type=QuestionType.MULTIPLE_CHOICE.value,
            question_text="Binary search complexity?",
            options_snapshot=[
                {"id": "opt_right", "key": "A", "text": "O(log n)", "is_correct": False},
                {"id": "opt_wrong", "key": "B", "text": "O(n)", "is_correct": True},
            ],
            default_points=Decimal("1.00"),
        )

        reg1 = QuizRegrade(
            id=uuid.uuid4(),
            submission_id=sub1_id,
            attempt_question_id=aq1_id,
            student_reason="Dap an chuan phai la O(log n), khong phai O(n).",
            regrade_scope=RegradeScope.SINGLE_STUDENT.value,
            status=RegradeStatus.PENDING.value,
            old_score=Decimal("0.0"),
            created_at=now,
        )
        reg2 = QuizRegrade(
            id=uuid.uuid4(),
            submission_id=sub2_id,
            attempt_question_id=aq2_id,
            student_reason="Em cung chon O(log n) nhung bi cham sai.",
            regrade_scope=RegradeScope.SINGLE_STUDENT.value,
            status=RegradeStatus.PENDING.value,
            old_score=Decimal("0.0"),
            created_at=now,
        )

        db = MagicMock()
        db.flush = AsyncMock()
        repo = MagicMock()
        repo.get_regrade_by_id = AsyncMock(return_value=reg1)
        repo.get_submission_by_id = AsyncMock(return_value=sub1)
        repo.get_quiz_by_id = AsyncMock(return_value=quiz)
        repo.get_attempt_question_by_id = AsyncMock(return_value=aq1)
        repo.get_quiz_question_by_id = AsyncMock(return_value=tier1_qq)
        repo.list_attempt_questions_for_quiz_question = AsyncMock(return_value=[aq1, aq2])
        repo.list_submitted_submissions_by_quiz = AsyncMock(return_value=[sub1, sub2])
        repo.list_attempt_questions = AsyncMock(
            side_effect=lambda sid: [aq1] if sid == sub1_id else [aq2]
        )
        repo.list_pending_regrades_for_quiz_question = AsyncMock(return_value=[reg1, reg2])
        repo.list_regrades_by_submission = AsyncMock(
            side_effect=lambda sid: [reg1] if sid == sub1_id else [reg2]
        )
        repo.enqueue_outbox_event = AsyncMock()

        course_public = MagicMock()
        course_public.assert_course_role = AsyncMock(return_value=ContextualRole.INSTRUCTOR)

        svc = ExaminationService(db=db, repo=repo, course_public=course_public)
        res = asyncio.run(
            svc.review_regrade_request(
                regrade_id=reg1.id,
                payload=RegradeReviewRequest(
                    approved=True,
                    regrade_scope=RegradeScope.ENTIRE_CLASS,
                    correct_option_ids=["opt_right"],
                    reviewer_feedback="Dap an dung la O(log n), cham lai toan lop.",
                ),
                actor=instructor,
                now=now,
            )
        )

        assert res.affected_submissions_count == 2
        assert res.closed_pending_regrades_count == 1
        assert sub1.final_score == Decimal("10.0")
        assert sub2.final_score == Decimal("10.0")
        assert reg2.status == RegradeStatus.APPROVED.value
        assert [o["id"] for o in tier1_qq.options_snapshot if o["is_correct"]] == ["opt_right"]
        # Both students' shuffled display keys preserved while is_correct updated accurately
        assert [o["key"] for o in aq1.options_snapshot if o["is_correct"]] == ["B"]
        assert [o["key"] for o in aq2.options_snapshot if o["is_correct"]] == ["A"]
        repo.enqueue_outbox_event.assert_awaited_once()
        assert repo.enqueue_outbox_event.call_args.kwargs["event_type"] == "examination.quiz_regraded"

    def test_public_api_blocks_ai_tutor_during_controlled_exam_e13(self):
        course_id = uuid.uuid4()
        quiz_id = uuid.uuid4()
        user_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        sub = QuizSubmission(
            id=uuid.uuid4(),
            quiz_id=quiz_id,
            user_id=user_id,
            expires_at=now + timedelta(minutes=20),
            status=SubmissionStatus.IN_PROGRESS.value,
        )
        quiz = Quiz(
            id=quiz_id,
            course_id=course_id,
            title="Controlled Exam",
            security_mode=SecurityMode.CONTROLLED.value,
            is_ai_locked=True,
        )
        repo = MagicMock()
        repo.get_active_ai_locked_submission_for_user = AsyncMock(return_value=sub)
        repo.get_quiz_by_id = AsyncMock(return_value=quiz)

        pub = ExaminationPublicService(db=MagicMock(), repo=repo)
        with pytest.raises(ExamAiLockedException) as exc:
            asyncio.run(pub.assert_ai_tutor_allowed(course_id, user_id, now=now))
        assert exc.value.detail["code"] == "E-13"
