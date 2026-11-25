# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Business logic service for Examination Context (T2-P-M4-01 & T2-P-M4-02)."""

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import secrets
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.course.enums import BloomLevel, ContextualRole
from app.modules.course.public_api import CoursePublicService
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
    ExamClosedException,
    ExaminationForbiddenException,
    ExaminationNotFoundException,
    ExaminationStateException,
    ExaminationValidationException,
    InsufficientQuestionsException,
    InvalidPasscodeException,
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
from app.modules.examination.repository import ExaminationRepository
from app.modules.examination.schemas import (
    ActiveSessionResponse,
    AttemptQuestionResponse,
    AttemptResultResponse,
    AttemptStartRequest,
    AttemptStartResponse,
    AutosaveRequest,
    AutosaveResponse,
    PasscodeRegenerateResponse,
    PublishGradesResponse,
    QuestionBankCreate,
    QuestionBankResponse,
    QuestionCreate,
    QuestionDeleteResponse,
    QuestionOptionSchema,
    QuestionResponse,
    QuestionUpdate,
    QuizCreate,
    QuizDetailResponse,
    QuizMatrixRuleSchema,
    QuizQuestionSnapshotResponse,
    QuizSettingsUpdate,
    QuizSummaryResponse,
    RegradeCreateRequest,
    RegradeReviewRequest,
    RegradeReviewResponse,
    RegradeSummaryResponse,
    ResultQuestionAnalysis,
    SubmitAttemptRequest,
    SubmitAttemptResponse,
    _validate_question_options,
)
from app.modules.examination.scoring import (
    compute_quiz_score_scale_10,
    score_question_from_snapshot,
)
from app.modules.examination.security_rules import (
    assert_ip_allowed,
    assert_within_grace_period,
    compute_effective_deadline,
    generate_passcode,
    validate_cidr_expression,
    validate_exam_window,
)
from app.modules.examination.snapshot import (
    MatrixRule,
    build_attempt_question_snapshots,
    build_quiz_question_snapshots,
    normalize_options_snapshot,
    sanitize_options_for_student,
    select_questions_by_matrix,
)
from app.modules.system.models import User

REGRADE_WINDOW_HOURS = 48


@dataclass(frozen=True)
class GradeReleaseWindow:
    """Resolved visibility and 48-hour regrade deadline for a quiz submission (BR-REG-02)."""

    grades_visible: bool
    release_timestamp: Optional[datetime]
    regrade_deadline: Optional[datetime]
    can_request_regrade: bool


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def resolve_grade_release_window(
    policy: str,
    submitted_at: Optional[datetime],
    available_until: datetime,
    grades_published_at: Optional[datetime],
    now: Optional[datetime] = None,
) -> GradeReleaseWindow:
    """
    Resolve grade visibility and the 48-hour regrade deadline per `grade_release_policy`:
    - IMMEDIATE   -> submitted_at
    - AFTER_CLOSE -> available_until
    - MANUAL      -> grades_published_at (must be non-null)
    """
    current = _ensure_utc(now or datetime.now(timezone.utc))
    release_ts: Optional[datetime] = None

    if policy == GradeReleasePolicy.IMMEDIATE.value:
        release_ts = _ensure_utc(submitted_at) if submitted_at is not None else None
    elif policy == GradeReleasePolicy.AFTER_CLOSE.value:
        release_ts = _ensure_utc(available_until)
    elif policy == GradeReleasePolicy.MANUAL.value:
        release_ts = (
            _ensure_utc(grades_published_at) if grades_published_at is not None else None
        )

    if release_ts is None:
        return GradeReleaseWindow(
            grades_visible=False,
            release_timestamp=None,
            regrade_deadline=None,
            can_request_regrade=False,
        )

    grades_visible = current >= release_ts
    regrade_deadline = release_ts + timedelta(hours=REGRADE_WINDOW_HOURS)
    can_request = grades_visible and current <= regrade_deadline
    return GradeReleaseWindow(
        grades_visible=grades_visible,
        release_timestamp=release_ts,
        regrade_deadline=regrade_deadline,
        can_request_regrade=can_request,
    )


def _normalize_selected_keys(raw_answer: Any) -> List[str]:
    if raw_answer is None:
        return []
    if isinstance(raw_answer, str):
        cleaned = raw_answer.strip().upper()
        return [cleaned] if cleaned else []
    if isinstance(raw_answer, Iterable):
        return [str(x).strip().upper() for x in raw_answer if str(x).strip()]
    return []


def _apply_regrade_key_update(
    options_snapshot: Sequence[Dict[str, Any]],
    correct_option_ids: Optional[Sequence[str]],
    award_full_question_credit: bool,
) -> List[Dict[str, Any]]:
    """
    Produce a new options_snapshot list with updated `is_correct` flags while preserving
    each student's shuffled order and display keys A-B-C-D.
    Matches against each option's stable `id` (or `key` fallback).
    """
    updated = deepcopy(list(options_snapshot))
    if award_full_question_credit:
        for opt in updated:
            opt["is_correct"] = True
        return updated

    target_ids = {str(x).strip() for x in (correct_option_ids or []) if str(x).strip()}
    for opt in updated:
        opt_id = str(opt.get("id") or "").strip()
        opt_key = str(opt.get("key") or "").strip()
        opt["is_correct"] = (opt_id in target_ids) or (opt_key in target_ids)
    return updated


def _to_attempt_question_response(aq: QuizAttemptQuestion) -> AttemptQuestionResponse:
    return AttemptQuestionResponse(
        id=aq.id,
        question_order=aq.question_order,
        question_type=QuestionType(aq.question_type),
        question_text=aq.question_text,
        options_snapshot=sanitize_options_for_student(aq.options_snapshot or []),
        default_points=aq.default_points,
    )


def _to_regrade_summary(regrade: QuizRegrade) -> RegradeSummaryResponse:
    return RegradeSummaryResponse(
        id=regrade.id,
        submission_id=regrade.submission_id,
        attempt_question_id=regrade.attempt_question_id,
        student_reason=regrade.student_reason,
        evidence_url=regrade.evidence_url,
        regrade_scope=RegradeScope(regrade.regrade_scope),
        status=RegradeStatus(regrade.status),
        old_score=regrade.old_score,
        new_score=regrade.new_score,
        reviewer_feedback=regrade.reviewer_feedback,
        reviewed_by=regrade.reviewed_by,
        reviewed_at=regrade.reviewed_at,
        created_at=regrade.created_at,
    )


def _is_system_admin(actor: User) -> bool:
    return (getattr(actor, "system_role", "") or "").upper() == "ADMIN"


def _serialize_options(options: List[QuestionOptionSchema]) -> List[Dict[str, Any]]:
    raw = [
        {
            "id": opt.id or opt.key,
            "key": opt.key,
            "text": opt.text,
            "is_correct": opt.is_correct,
        }
        for opt in options
    ]
    return normalize_options_snapshot(raw)


def _validate_security_and_attempts(
    security_mode: SecurityMode,
    max_attempts: int,
) -> None:
    if max_attempts < 1:
        raise ExaminationValidationException(
            detail="So luot lam bai toi da phai lon hon hoac bang 1.",
            field="max_attempts",
        )
    if security_mode != SecurityMode.PRACTICE and max_attempts > 1:
        raise ExaminationValidationException(
            detail="Che do thi that (CONTROLLED / REMOTE_PROCTORED) chi cho phep toi da 1 luot thi.",
            field="max_attempts",
        )


def _to_question_response(q: Question) -> QuestionResponse:
    return QuestionResponse(
        id=q.id,
        bank_id=q.bank_id,
        lo_id=q.lo_id,
        bloom_level=BloomLevel(q.bloom_level),
        question_text=q.question_text,
        question_type=QuestionType(q.question_type),
        default_points=q.default_points,
        options=list(q.options or []),
        explanation=q.explanation,
        is_active=q.is_active,
        deleted_at=q.deleted_at,
        created_at=q.created_at,
        updated_at=q.updated_at,
    )


def _to_quiz_summary(
    quiz: Quiz,
    question_count: int,
    include_sensitive: bool,
) -> QuizSummaryResponse:
    return QuizSummaryResponse(
        id=quiz.id,
        course_id=quiz.course_id,
        title=quiz.title,
        status=QuizStatus(quiz.status),
        time_limit_mins=quiz.time_limit_mins,
        available_from=quiz.available_from,
        available_until=quiz.available_until,
        security_mode=SecurityMode(quiz.security_mode),
        max_attempts=quiz.max_attempts,
        grade_release_policy=GradeReleasePolicy(quiz.grade_release_policy),
        grades_published_at=quiz.grades_published_at,
        is_ai_locked=quiz.is_ai_locked,
        has_passcode=bool(quiz.passcode),
        passcode=quiz.passcode if include_sensitive else None,
        ip_filter_range=quiz.ip_filter_range if include_sensitive else None,
        shuffle_questions=quiz.shuffle_questions,
        shuffle_options=quiz.shuffle_options,
        snapshot_mode=quiz.snapshot_mode,
        question_count=question_count,
        created_at=quiz.created_at,
        updated_at=quiz.updated_at,
    )


def _to_quiz_question_response(
    qq: QuizQuestion,
    include_answers: bool,
) -> QuizQuestionSnapshotResponse:
    options = (
        list(qq.options_snapshot or [])
        if include_answers
        else sanitize_options_for_student(qq.options_snapshot or [])
    )
    return QuizQuestionSnapshotResponse(
        id=qq.id,
        question_id=qq.question_id,
        lo_id=qq.lo_id,
        question_order=qq.question_order,
        question_type=QuestionType(qq.question_type),
        question_text_snapshot=qq.question_text_snapshot,
        options_snapshot=options,
        explanation_snapshot=qq.explanation_snapshot if include_answers else None,
        default_points=qq.default_points,
    )


class ExaminationService:
    """Service layer for Question Banks, Questions, Quiz Snapshots & Room Security."""

    def __init__(
        self,
        db: AsyncSession,
        repo: Optional[ExaminationRepository] = None,
        course_public: Optional[CoursePublicService] = None,
    ):
        self.db = db
        self.repo = repo or ExaminationRepository(db)
        self.course_public = course_public or CoursePublicService(db)

    # ------------------------------------------------------------------
    # Cross-module Authorization Helpers (strictly via CoursePublicService)
    # ------------------------------------------------------------------
    async def _assert_instructor(self, course_id: uuid.UUID, actor: User) -> ContextualRole:
        role = await self.course_public.assert_course_role(
            course_id=course_id,
            user_id=actor.id,
            allowed_roles=(ContextualRole.INSTRUCTOR, ContextualRole.TA),
            is_admin=_is_system_admin(actor),
        )
        return role or ContextualRole.INSTRUCTOR

    async def _assert_course_member(
        self,
        course_id: uuid.UUID,
        actor: User,
    ) -> ContextualRole:
        role = await self.course_public.assert_course_role(
            course_id=course_id,
            user_id=actor.id,
            allowed_roles=(
                ContextualRole.INSTRUCTOR,
                ContextualRole.TA,
                ContextualRole.STUDENT,
            ),
            is_admin=_is_system_admin(actor),
        )
        return role or ContextualRole.STUDENT

    async def _validate_lo_in_course(
        self,
        course_id: uuid.UUID,
        lo_id: Optional[uuid.UUID],
    ) -> None:
        if lo_id is None:
            return
        los = await self.course_public.get_learning_objectives(course_id)
        if not any(lo.id == lo_id for lo in los):
            raise ExaminationValidationException(
                detail="Chuan dau ra (LO) khong ton tai trong mon hoc nay.",
                field="lo_id",
            )

    # ------------------------------------------------------------------
    # Question Banks (T2-P-M4-01)
    # ------------------------------------------------------------------
    async def list_question_banks(
        self,
        course_id: uuid.UUID,
        actor: User,
    ) -> List[QuestionBankResponse]:
        await self._assert_instructor(course_id, actor)
        banks = await self.repo.list_question_banks_by_course(course_id)
        counts = await self.repo.count_active_questions_by_banks([b.id for b in banks])
        return [
            QuestionBankResponse(
                id=b.id,
                course_id=b.course_id,
                category_name=b.category_name,
                question_count=counts.get(b.id, 0),
                created_at=b.created_at,
            )
            for b in banks
        ]

    async def create_question_bank(
        self,
        course_id: uuid.UUID,
        payload: QuestionBankCreate,
        actor: User,
    ) -> QuestionBankResponse:
        await self._assert_instructor(course_id, actor)
        bank = QuestionBank(
            course_id=course_id,
            category_name=payload.category_name,
        )
        await self.repo.create_question_bank(bank)
        return QuestionBankResponse(
            id=bank.id,
            course_id=bank.course_id,
            category_name=bank.category_name,
            question_count=0,
            created_at=bank.created_at,
        )

    async def delete_question_bank(
        self,
        bank_id: uuid.UUID,
        actor: User,
    ) -> None:
        bank = await self.repo.get_question_bank_by_id(bank_id)
        if bank is None:
            raise ExaminationNotFoundException("Khong tim thay danh muc ngan hang cau hoi.")
        await self._assert_instructor(bank.course_id, actor)
        await self.repo.delete_question_bank(bank)

    # ------------------------------------------------------------------
    # Questions (T2-P-M4-01)
    # ------------------------------------------------------------------
    async def list_questions(
        self,
        course_id: uuid.UUID,
        actor: User,
        bank_id: Optional[uuid.UUID] = None,
        lo_id: Optional[uuid.UUID] = None,
        bloom_level: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> List[QuestionResponse]:
        await self._assert_instructor(course_id, actor)
        questions = await self.repo.list_questions_by_course(
            course_id=course_id,
            bank_id=bank_id,
            lo_id=lo_id,
            bloom_level=bloom_level,
            search_query=search_query,
            include_inactive=False,
        )
        return [_to_question_response(q) for q in questions]

    async def create_question(
        self,
        course_id: uuid.UUID,
        payload: QuestionCreate,
        actor: User,
    ) -> QuestionResponse:
        await self._assert_instructor(course_id, actor)
        bank = await self.repo.get_question_bank_by_id(payload.bank_id)
        if bank is None or bank.course_id != course_id:
            raise ExaminationNotFoundException(
                "Danh muc ngan hang cau hoi khong ton tai trong mon hoc nay."
            )

        await self._validate_lo_in_course(course_id, payload.lo_id)

        now = datetime.now(timezone.utc)
        question = Question(
            bank_id=payload.bank_id,
            lo_id=payload.lo_id,
            bloom_level=payload.bloom_level.value,
            question_text=payload.question_text,
            question_type=payload.question_type.value,
            default_points=payload.default_points,
            options=_serialize_options(payload.options),
            explanation=payload.explanation,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        await self.repo.create_question(question)
        return _to_question_response(question)

    async def update_question(
        self,
        question_id: uuid.UUID,
        payload: QuestionUpdate,
        actor: User,
    ) -> QuestionResponse:
        question = await self.repo.get_question_by_id(question_id, include_inactive=False)
        if question is None:
            raise ExaminationNotFoundException("Khong tim thay cau hoi.")

        current_bank = await self.repo.get_question_bank_by_id(question.bank_id)
        if current_bank is None:
            raise ExaminationNotFoundException("Khong tim thay danh muc ngan hang cau hoi.")
        await self._assert_instructor(current_bank.course_id, actor)

        if payload.bank_id is not None and payload.bank_id != question.bank_id:
            target_bank = await self.repo.get_question_bank_by_id(payload.bank_id)
            if target_bank is None or target_bank.course_id != current_bank.course_id:
                raise ExaminationNotFoundException(
                    "Danh muc ngan hang dich khong thuoc cung mon hoc."
                )
            question.bank_id = payload.bank_id

        if payload.lo_id is not None:
            await self._validate_lo_in_course(current_bank.course_id, payload.lo_id)
            question.lo_id = payload.lo_id

        effective_type = payload.question_type or QuestionType(question.question_type)
        if payload.options is not None:
            try:
                _validate_question_options(effective_type, payload.options)
            except ValueError as exc:
                raise ExaminationValidationException(str(exc), field="options") from exc
            question.options = _serialize_options(payload.options)
        elif payload.question_type is not None:
            existing_opts = [
                QuestionOptionSchema(
                    id=str(o.get("id") or o.get("key") or ""),
                    key=str(o.get("key") or ""),
                    text=str(o.get("text") or ""),
                    is_correct=bool(o.get("is_correct", False)),
                )
                for o in (question.options or [])
            ]
            try:
                _validate_question_options(effective_type, existing_opts)
            except ValueError as exc:
                raise ExaminationValidationException(str(exc), field="question_type") from exc

        if payload.bloom_level is not None:
            question.bloom_level = payload.bloom_level.value
        if payload.question_text is not None:
            question.question_text = payload.question_text
        if payload.question_type is not None:
            question.question_type = payload.question_type.value
        if payload.default_points is not None:
            question.default_points = payload.default_points
        if payload.explanation is not None:
            question.explanation = payload.explanation

        question.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return _to_question_response(question)

    async def delete_question(
        self,
        question_id: uuid.UUID,
        actor: User,
    ) -> QuestionDeleteResponse:
        """
        Delete a question while preserving Tier-1 Snapshot referential integrity:
        Soft-deletes (`is_active = False`, `deleted_at = NOW()`) if ever snapshotted into
        `examination.quiz_questions`; physically deletes otherwise.
        """
        question = await self.repo.get_question_by_id(question_id, include_inactive=False)
        if question is None:
            raise ExaminationNotFoundException("Khong tim thay cau hoi.")

        bank = await self.repo.get_question_bank_by_id(question.bank_id)
        if bank is None:
            raise ExaminationNotFoundException("Khong tim thay danh muc ngan hang cau hoi.")
        await self._assert_instructor(bank.course_id, actor)

        soft_deleted = await self.repo.delete_question_respecting_snapshot(question)
        msg = (
            "Cau hoi da tung duoc chup Snapshot vao de thi nen da duoc xoa mem (an khoi ngan hang)."
            if soft_deleted
            else "Da xoa vinh vien cau hoi khoi ngan hang."
        )
        return QuestionDeleteResponse(
            question_id=question_id,
            soft_deleted=soft_deleted,
            message=msg,
        )

    # ------------------------------------------------------------------
    # Quizzes, Tier-1 Snapshots & Security Room Settings (T2-P-M4-01..02)
    # ------------------------------------------------------------------
    async def _draw_questions_from_matrix(
        self,
        course_id: uuid.UUID,
        matrix_rules_schema: List[QuizMatrixRuleSchema],
    ) -> List[Question]:
        rules: List[MatrixRule] = []
        pools: List[List[Question]] = []
        for item in matrix_rules_schema:
            bank = await self.repo.get_question_bank_by_id(item.bank_id)
            if bank is None or bank.course_id != course_id:
                raise ExaminationNotFoundException(
                    "Danh muc ngan hang trong ma tran de thi khong thuoc mon hoc nay."
                )
            bloom_val = item.bloom_level.value if item.bloom_level else None
            pool = await self.repo.list_active_questions_for_matrix(
                bank_id=item.bank_id,
                bloom_level=bloom_val,
                lo_id=item.lo_id,
            )
            rules.append(
                MatrixRule(
                    bank_id=item.bank_id,
                    count=item.count,
                    bloom_level=bloom_val,
                    lo_id=item.lo_id,
                )
            )
            pools.append(pool)

        return select_questions_by_matrix(rules, pools)

    async def _draw_questions_by_ids(
        self,
        course_id: uuid.UUID,
        question_ids: List[uuid.UUID],
    ) -> List[Question]:
        selected: List[Question] = []
        seen = set()
        for qid in question_ids:
            if qid in seen:
                continue
            q = await self.repo.get_question_by_id(qid, include_inactive=False)
            if q is None:
                raise InsufficientQuestionsException(
                    detail=f"Cau hoi {qid} khong ton tai hoac da bi xoa.",
                    requested=len(question_ids),
                    available=len(selected),
                )
            bank = await self.repo.get_question_bank_by_id(q.bank_id)
            if bank is None or bank.course_id != course_id:
                raise ExaminationForbiddenException(
                    "Khong the chon cau hoi thuoc mon hoc khac."
                )
            seen.add(qid)
            selected.append(q)
        return selected

    async def list_quizzes(
        self,
        course_id: uuid.UUID,
        actor: User,
    ) -> List[QuizSummaryResponse]:
        role = await self._assert_course_member(course_id, actor)
        is_instructor = role in (ContextualRole.INSTRUCTOR, ContextualRole.TA) or _is_system_admin(actor)

        quizzes = await self.repo.list_quizzes_by_course(course_id)
        results: List[QuizSummaryResponse] = []
        for quiz in quizzes:
            if not is_instructor and quiz.status == QuizStatus.DRAFT.value:
                continue
            q_count = await self.repo.count_quiz_questions(quiz.id)
            results.append(
                _to_quiz_summary(
                    quiz=quiz,
                    question_count=q_count,
                    include_sensitive=is_instructor,
                )
            )
        return results

    async def create_quiz(
        self,
        course_id: uuid.UUID,
        payload: QuizCreate,
        actor: User,
    ) -> QuizDetailResponse:
        await self._assert_instructor(course_id, actor)

        validate_exam_window(
            payload.available_from,
            payload.available_until,
            payload.time_limit_mins,
        )
        _validate_security_and_attempts(payload.security_mode, payload.max_attempts)
        normalized_cidr = validate_cidr_expression(payload.ip_filter_range)

        selected_questions: List[Question] = []
        if payload.matrix_config:
            selected_questions = await self._draw_questions_from_matrix(
                course_id,
                payload.matrix_config,
            )
        elif payload.question_ids:
            selected_questions = await self._draw_questions_by_ids(
                course_id,
                payload.question_ids,
            )

        matrix_json = [
            {
                "bank_id": str(rule.bank_id),
                "bloom_level": rule.bloom_level.value if rule.bloom_level else None,
                "lo_id": str(rule.lo_id) if rule.lo_id else None,
                "count": rule.count,
            }
            for rule in payload.matrix_config
        ]

        now = datetime.now(timezone.utc)
        passcode_clean = payload.passcode.strip() if payload.passcode else None
        quiz = Quiz(
            course_id=course_id,
            title=payload.title,
            time_limit_mins=payload.time_limit_mins,
            available_from=payload.available_from,
            available_until=payload.available_until,
            passcode=passcode_clean or None,
            ip_filter_range=normalized_cidr,
            grade_release_policy=payload.grade_release_policy.value,
            is_ai_locked=payload.is_ai_locked,
            status=QuizStatus.DRAFT.value,
            security_mode=payload.security_mode.value,
            max_attempts=payload.max_attempts,
            shuffle_questions=payload.shuffle_questions,
            shuffle_options=payload.shuffle_options,
            snapshot_mode=payload.snapshot_mode,
            matrix_config=matrix_json,
            created_by=actor.id,
            created_at=now,
            updated_at=now,
        )
        await self.repo.create_quiz(quiz)

        snapshots: List[QuizQuestion] = []
        if selected_questions:
            snapshots = build_quiz_question_snapshots(selected_questions, quiz.id)
            await self.repo.bulk_create_quiz_questions(snapshots)

        summary = _to_quiz_summary(quiz, len(snapshots), include_sensitive=True)
        return QuizDetailResponse(
            **summary.model_dump(),
            matrix_config=list(quiz.matrix_config or []),
            questions=[
                _to_quiz_question_response(qq, include_answers=True) for qq in snapshots
            ],
        )

    async def get_quiz_detail(
        self,
        quiz_id: uuid.UUID,
        actor: User,
    ) -> QuizDetailResponse:
        quiz = await self.repo.get_quiz_by_id(quiz_id)
        if quiz is None:
            raise ExaminationNotFoundException("Khong tim thay ky thi.")

        role = await self._assert_course_member(quiz.course_id, actor)
        is_instructor = role in (ContextualRole.INSTRUCTOR, ContextualRole.TA) or _is_system_admin(actor)

        if not is_instructor and quiz.status == QuizStatus.DRAFT.value:
            raise ExaminationForbiddenException("Ky thi chua duoc xuat ban.")

        snapshots = await self.repo.list_quiz_questions(quiz.id)
        summary = _to_quiz_summary(quiz, len(snapshots), include_sensitive=is_instructor)

        return QuizDetailResponse(
            **summary.model_dump(),
            matrix_config=list(quiz.matrix_config or []) if is_instructor else [],
            questions=[
                _to_quiz_question_response(qq, include_answers=is_instructor)
                for qq in snapshots
            ],
        )

    async def update_quiz_settings(
        self,
        quiz_id: uuid.UUID,
        payload: QuizSettingsUpdate,
        actor: User,
    ) -> QuizDetailResponse:
        quiz = await self.repo.get_quiz_by_id(quiz_id)
        if quiz is None:
            raise ExaminationNotFoundException("Khong tim thay ky thi.")

        await self._assert_instructor(quiz.course_id, actor)

        validate_exam_window(
            payload.available_from,
            payload.available_until,
            payload.time_limit_mins,
        )
        _validate_security_and_attempts(payload.security_mode, payload.max_attempts)
        normalized_cidr = validate_cidr_expression(payload.ip_filter_range)

        if payload.title is not None:
            quiz.title = payload.title.strip()
        quiz.time_limit_mins = payload.time_limit_mins
        quiz.available_from = payload.available_from
        quiz.available_until = payload.available_until
        quiz.passcode = payload.passcode.strip() if payload.passcode and payload.passcode.strip() else None
        quiz.ip_filter_range = normalized_cidr
        quiz.security_mode = payload.security_mode.value
        quiz.max_attempts = payload.max_attempts
        quiz.grade_release_policy = payload.grade_release_policy.value
        quiz.is_ai_locked = payload.is_ai_locked
        quiz.shuffle_questions = payload.shuffle_questions
        quiz.shuffle_options = payload.shuffle_options
        quiz.updated_at = datetime.now(timezone.utc)

        await self.db.flush()
        snapshots = await self.repo.list_quiz_questions(quiz.id)
        summary = _to_quiz_summary(quiz, len(snapshots), include_sensitive=True)
        return QuizDetailResponse(
            **summary.model_dump(),
            matrix_config=list(quiz.matrix_config or []),
            questions=[
                _to_quiz_question_response(qq, include_answers=True) for qq in snapshots
            ],
        )

    async def publish_quiz(
        self,
        quiz_id: uuid.UUID,
        actor: User,
    ) -> QuizDetailResponse:
        quiz = await self.repo.get_quiz_by_id(quiz_id)
        if quiz is None:
            raise ExaminationNotFoundException("Khong tim thay ky thi.")

        await self._assert_instructor(quiz.course_id, actor)

        if quiz.status == QuizStatus.CLOSED.value:
            raise ExaminationStateException("Khong the xuat ban lai ky thi da dong.")

        validate_exam_window(
            quiz.available_from,
            quiz.available_until,
            quiz.time_limit_mins,
        )

        snapshots = await self.repo.list_quiz_questions(quiz.id)
        if not snapshots and quiz.matrix_config:
            matrix_rules = [
                QuizMatrixRuleSchema(
                    bank_id=uuid.UUID(str(item["bank_id"])),
                    bloom_level=BloomLevel(item["bloom_level"])
                    if item.get("bloom_level")
                    else None,
                    lo_id=uuid.UUID(str(item["lo_id"])) if item.get("lo_id") else None,
                    count=int(item["count"]),
                )
                for item in quiz.matrix_config
            ]
            selected = await self._draw_questions_from_matrix(quiz.course_id, matrix_rules)
            snapshots = build_quiz_question_snapshots(selected, quiz.id)
            await self.repo.bulk_create_quiz_questions(snapshots)

        if not snapshots:
            raise InsufficientQuestionsException(
                detail="De thi phai co it nhat 1 cau hoi da dong bang Snapshot truoc khi xuat ban.",
                requested=1,
                available=0,
            )

        quiz.status = QuizStatus.PUBLISHED.value
        quiz.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        summary = _to_quiz_summary(quiz, len(snapshots), include_sensitive=True)
        return QuizDetailResponse(
            **summary.model_dump(),
            matrix_config=list(quiz.matrix_config or []),
            questions=[
                _to_quiz_question_response(qq, include_answers=True) for qq in snapshots
            ],
        )

    async def regenerate_passcode(
        self,
        quiz_id: uuid.UUID,
        actor: User,
    ) -> PasscodeRegenerateResponse:
        """Subflow A-1 (T2-P-M4-02): Emergency 6-character passcode regeneration."""
        quiz = await self.repo.get_quiz_by_id(quiz_id)
        if quiz is None:
            raise ExaminationNotFoundException("Khong tim thay ky thi.")

        await self._assert_instructor(quiz.course_id, actor)

        new_code = generate_passcode()
        quiz.passcode = new_code
        quiz.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        return PasscodeRegenerateResponse(quiz_id=quiz.id, passcode=new_code)

    async def publish_grades(
        self,
        quiz_id: uuid.UUID,
        actor: User,
    ) -> PublishGradesResponse:
        """Manually publish exam grades and start the 48h regrade window (BR-REG-02)."""
        quiz = await self.repo.get_quiz_by_id(quiz_id)
        if quiz is None:
            raise ExaminationNotFoundException("Khong tim thay ky thi.")

        await self._assert_instructor(quiz.course_id, actor)

        now = datetime.now(timezone.utc)
        quiz.grades_published_at = now
        quiz.updated_at = now
        await self.db.flush()

        return PublishGradesResponse(quiz_id=quiz.id, grades_published_at=now)

    # ------------------------------------------------------------------
    # Exam Taking, Resume Exam, Autosave & Scoring (T2-P-M4-03)
    # ------------------------------------------------------------------
    def _evaluate_submission(
        self,
        attempt_questions: Sequence[QuizAttemptQuestion],
        student_answers: Dict[str, Any],
    ) -> Tuple[Decimal, List[ResultQuestionAnalysis], List[Dict[str, Any]]]:
        earned_list: List[Decimal] = []
        max_list: List[Decimal] = []
        analyses: List[ResultQuestionAnalysis] = []
        outcomes: List[Dict[str, Any]] = []

        for aq in attempt_questions:
            raw_ans = student_answers.get(str(aq.id))
            selected_keys = _normalize_selected_keys(raw_ans)
            options_snapshot = list(aq.options_snapshot or [])
            correct_keys = [
                str(o.get("key") or o.get("id") or "").strip().upper()
                for o in options_snapshot
                if bool(o.get("is_correct"))
            ]
            earned = score_question_from_snapshot(
                question_type=aq.question_type,
                options_snapshot=options_snapshot,
                selected_keys=selected_keys,
                default_points=aq.default_points,
            )
            earned_list.append(earned)
            max_list.append(aq.default_points)
            is_full = earned >= aq.default_points and aq.default_points > Decimal("0")

            analyses.append(
                ResultQuestionAnalysis(
                    attempt_question_id=aq.id,
                    question_order=aq.question_order,
                    question_type=QuestionType(aq.question_type),
                    question_text=aq.question_text,
                    default_points=aq.default_points,
                    earned_points=earned,
                    is_correct=is_full,
                    selected_keys=selected_keys,
                    correct_keys=correct_keys,
                    options_snapshot=options_snapshot,
                    explanation_snapshot=aq.explanation_snapshot,
                )
            )
            outcomes.append(
                {
                    "attempt_question_id": str(aq.id),
                    "question_id": str(aq.question_id) if aq.question_id else None,
                    "lo_id": str(aq.lo_id) if aq.lo_id else None,
                    "earned_points": float(earned),
                    "max_points": float(aq.default_points),
                    "is_correct": is_full,
                }
            )

        scale_10_score = compute_quiz_score_scale_10(earned_list, max_list)
        return scale_10_score, analyses, outcomes

    async def start_attempt(
        self,
        quiz_id: uuid.UUID,
        payload: AttemptStartRequest,
        actor: User,
        client_ip: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> AttemptStartResponse:
        """
        Idempotent exam entry (T2-P-M4-03):
        - Enforces course membership, PUBLISHED status, exam window, IP CIDR (E-SEC-03),
          and room passcode (E-SEC-02).
        - Resumes an active IN_PROGRESS attempt if not yet expired (`resumed = True`).
        - Otherwise enforces `max_attempts`, freezes Tier-2 shuffled snapshot (`BR-EXAM-02`),
          and computes server-locked `expires_at` (`BR-08`).
        """
        quiz = await self.repo.get_quiz_by_id(quiz_id)
        if quiz is None:
            raise ExaminationNotFoundException("Khong tim thay ky thi.")

        await self._assert_course_member(quiz.course_id, actor)

        if quiz.status != QuizStatus.PUBLISHED.value:
            raise ExamClosedException("Ky thi hien khong mo cho phep lam bai.")

        current_time = _ensure_utc(now or datetime.now(timezone.utc))
        avail_from = _ensure_utc(quiz.available_from)
        avail_until = _ensure_utc(quiz.available_until)
        if current_time < avail_from or current_time >= avail_until:
            raise ExamClosedException("Ngoai khung gio mo de thi cho phep.")

        assert_ip_allowed(client_ip, quiz.ip_filter_range)

        if quiz.passcode:
            provided = (payload.passcode or "").strip()
            if not provided or not secrets.compare_digest(provided, quiz.passcode):
                raise InvalidPasscodeException()

        # Check for an existing IN_PROGRESS submission (Idempotent Resume Exam)
        existing = await self.repo.get_in_progress_submission(quiz.id, actor.id)
        if existing is not None:
            exp_utc = (
                _ensure_utc(existing.expires_at)
                if existing.expires_at is not None
                else avail_until
            )
            if current_time < exp_utc:
                attempt_qs = await self.repo.list_attempt_questions(existing.id)
                remaining = max(0, int((exp_utc - current_time).total_seconds()))
                return AttemptStartResponse(
                    submission_id=existing.id,
                    quiz_id=quiz.id,
                    attempt_number=existing.attempt_number,
                    resumed=True,
                    status=SubmissionStatus(existing.status),
                    started_at=existing.started_at,
                    expires_at=exp_utc,
                    remaining_seconds=remaining,
                    seq_num=existing.seq_num,
                    student_answers=dict(existing.student_answers or {}),
                    flagged_questions=list(existing.flagged_questions or []),
                    security_mode=SecurityMode(quiz.security_mode),
                    is_ai_locked=quiz.is_ai_locked,
                    questions=[_to_attempt_question_response(aq) for aq in attempt_qs],
                )
            # Previous in-progress attempt expired -> auto-grade it before opening a new one
            old_qs = await self.repo.list_attempt_questions(existing.id)
            old_score, _, _ = self._evaluate_submission(
                old_qs, dict(existing.student_answers or {})
            )
            existing.submitted_at = exp_utc
            existing.auto_score = old_score
            existing.final_score = old_score
            existing.status = SubmissionStatus.TIMED_OUT.value
            await self.db.flush()

        # Check attempt quota against max_attempts
        used_attempts = await self.repo.count_user_attempts(quiz.id, actor.id)
        if used_attempts >= quiz.max_attempts:
            raise ExaminationStateException(
                f"Ban da su dung het {quiz.max_attempts} luot lam bai cho phep."
            )

        tier1_questions = await self.repo.list_quiz_questions(quiz.id)
        if not tier1_questions:
            raise InsufficientQuestionsException(
                detail="De thi chua co cau hoi Snapshot de bat dau lam bai.",
                requested=1,
                available=0,
            )

        expires_at = compute_effective_deadline(
            started_at=current_time,
            time_limit_mins=quiz.time_limit_mins,
            available_until=avail_until,
        )

        submission = QuizSubmission(
            quiz_id=quiz.id,
            user_id=actor.id,
            attempt_number=used_attempts + 1,
            started_at=current_time,
            expires_at=expires_at,
            seq_num=0,
            student_answers={},
            flagged_questions=[],
            client_ip=client_ip,
            tab_blur_count=0,
            fullscreen_exit_count=0,
            violation_logs=[],
            status=SubmissionStatus.IN_PROGRESS.value,
        )
        await self.repo.create_submission(submission)

        tier2_questions = build_attempt_question_snapshots(
            quiz_questions=tier1_questions,
            submission_id=submission.id,
            shuffle_questions=quiz.shuffle_questions,
            shuffle_options=quiz.shuffle_options,
        )
        await self.repo.bulk_create_attempt_questions(tier2_questions)

        remaining = max(0, int((expires_at - current_time).total_seconds()))
        return AttemptStartResponse(
            submission_id=submission.id,
            quiz_id=quiz.id,
            attempt_number=submission.attempt_number,
            resumed=False,
            status=SubmissionStatus(submission.status),
            started_at=submission.started_at,
            expires_at=expires_at,
            remaining_seconds=remaining,
            seq_num=submission.seq_num,
            student_answers={},
            flagged_questions=[],
            security_mode=SecurityMode(quiz.security_mode),
            is_ai_locked=quiz.is_ai_locked,
            questions=[_to_attempt_question_response(aq) for aq in tier2_questions],
        )

    async def autosave_attempt(
        self,
        submission_id: uuid.UUID,
        payload: AutosaveRequest,
        actor: User,
        now: Optional[datetime] = None,
    ) -> AutosaveResponse:
        """Monotonic `seq_num` autosave ingestion with 5-minute grace period (BR-AUTOSAVE-02)."""
        submission = await self.repo.get_submission_by_id(submission_id)
        if submission is None:
            raise ExaminationNotFoundException("Khong tim thay phien lam bai.")
        if submission.user_id != actor.id:
            raise ExaminationForbiddenException("Ban khong phai chu so huu phien lam bai nay.")
        if submission.status != SubmissionStatus.IN_PROGRESS.value:
            raise ExamClosedException("Phien lam bai da duoc nop hoac ket thuc.")

        current_time = _ensure_utc(now or datetime.now(timezone.utc))
        if submission.expires_at is not None:
            assert_within_grace_period(current_time, submission.expires_at)

        accepted = await self.repo.apply_autosave_if_newer(
            submission_id=submission.id,
            incoming_seq_num=payload.seq_num,
            student_answers=payload.answers,
            flagged_questions=payload.flagged_questions,
            tab_blur_delta=payload.tab_blur_delta,
            fullscreen_exit_delta=payload.fullscreen_exit_delta,
            violation_event=payload.violation_event,
        )

        refreshed = await self.repo.get_submission_by_id(submission.id)
        assert refreshed is not None
        if accepted:
            await self.db.refresh(refreshed)

        exp_utc = (
            _ensure_utc(refreshed.expires_at)
            if refreshed.expires_at is not None
            else current_time
        )
        remaining = max(0, int((exp_utc - current_time).total_seconds()))
        return AutosaveResponse(
            submission_id=refreshed.id,
            accepted=accepted,
            seq_num=refreshed.seq_num,
            remaining_seconds=remaining,
            tab_blur_count=refreshed.tab_blur_count,
            fullscreen_exit_count=refreshed.fullscreen_exit_count,
        )

    async def submit_attempt(
        self,
        submission_id: uuid.UUID,
        payload: Optional[SubmitAttemptRequest],
        actor: User,
        now: Optional[datetime] = None,
    ) -> SubmitAttemptResponse:
        """Finalize attempt, auto-score with scoring.py (BR-13), and emit Outbox event."""
        submission = await self.repo.get_submission_by_id(submission_id)
        if submission is None:
            raise ExaminationNotFoundException("Khong tim thay phien lam bai.")
        if submission.user_id != actor.id:
            raise ExaminationForbiddenException("Ban khong phai chu so huu phien lam bai nay.")
        if submission.status != SubmissionStatus.IN_PROGRESS.value:
            raise ExaminationStateException("Bai thi nay da duoc nop truoc do.")

        quiz = await self.repo.get_quiz_by_id(submission.quiz_id)
        if quiz is None:
            raise ExaminationNotFoundException("Khong tim thay ky thi.")

        current_time = _ensure_utc(now or datetime.now(timezone.utc))
        if submission.expires_at is not None:
            assert_within_grace_period(current_time, submission.expires_at)

        if payload is not None:
            if payload.answers is not None:
                submission.student_answers = payload.answers
            if payload.flagged_questions is not None:
                submission.flagged_questions = payload.flagged_questions

        attempt_qs = await self.repo.list_attempt_questions(submission.id)
        score, _, outcomes = self._evaluate_submission(
            attempt_qs, dict(submission.student_answers or {})
        )

        submission.submitted_at = current_time
        submission.auto_score = score
        submission.final_score = score
        submission.status = SubmissionStatus.AUTO_GRADED.value
        await self.db.flush()

        best_score = await self.repo.get_best_score_for_user(quiz.id, actor.id)
        await self.repo.enqueue_outbox_event(
            event_type="examination.quiz_completed",
            aggregate_type="QuizSubmission",
            aggregate_id=submission.id,
            payload={
                "course_id": str(quiz.course_id),
                "quiz_id": str(quiz.id),
                "submission_id": str(submission.id),
                "user_id": str(actor.id),
                "attempt_number": submission.attempt_number,
                "auto_score": float(score),
                "final_score": float(score),
                "best_score": float(best_score if best_score is not None else score),
                "submitted_at": current_time.isoformat(),
                "question_outcomes": outcomes,
            },
        )

        release_info = resolve_grade_release_window(
            policy=quiz.grade_release_policy,
            submitted_at=submission.submitted_at,
            available_until=quiz.available_until,
            grades_published_at=quiz.grades_published_at,
            now=current_time,
        )
        return SubmitAttemptResponse(
            submission_id=submission.id,
            quiz_id=quiz.id,
            status=SubmissionStatus(submission.status),
            submitted_at=current_time,
            grades_visible=release_info.grades_visible,
            auto_score=submission.auto_score if release_info.grades_visible else None,
            final_score=submission.final_score if release_info.grades_visible else None,
        )

    async def get_active_session(
        self,
        quiz_id: uuid.UUID,
        actor: User,
        now: Optional[datetime] = None,
    ) -> ActiveSessionResponse:
        """Return whether the current user has an active IN_PROGRESS session on `quiz_id` (E-13)."""
        quiz = await self.repo.get_quiz_by_id(quiz_id)
        if quiz is None:
            raise ExaminationNotFoundException("Khong tim thay ky thi.")

        await self._assert_course_member(quiz.course_id, actor)
        current_time = _ensure_utc(now or datetime.now(timezone.utc))

        sub = await self.repo.get_in_progress_submission(quiz.id, actor.id)
        if sub is None:
            return ActiveSessionResponse(
                has_active_session=False,
                is_ai_locked=False,
                quiz_id=quiz.id,
            )

        exp_utc = (
            _ensure_utc(sub.expires_at)
            if sub.expires_at is not None
            else _ensure_utc(quiz.available_until)
        )
        if current_time >= exp_utc:
            return ActiveSessionResponse(
                has_active_session=False,
                is_ai_locked=False,
                quiz_id=quiz.id,
            )

        locked = bool(
            quiz.is_ai_locked
            and quiz.security_mode in (
                SecurityMode.CONTROLLED.value,
                SecurityMode.REMOTE_PROCTORED.value,
            )
        )
        return ActiveSessionResponse(
            has_active_session=True,
            is_ai_locked=locked,
            quiz_id=quiz.id,
            submission_id=sub.id,
            expires_at=exp_utc,
        )

    # ------------------------------------------------------------------
    # Results & 48-Hour Regrade Workflow (T2-P-M4-04)
    # ------------------------------------------------------------------
    async def get_attempt_result(
        self,
        submission_id: uuid.UUID,
        actor: User,
        now: Optional[datetime] = None,
    ) -> AttemptResultResponse:
        """Return exam result and per-question analysis respecting `grade_release_policy`."""
        submission = await self.repo.get_submission_by_id(submission_id)
        if submission is None:
            raise ExaminationNotFoundException("Khong tim thay bai lam.")

        quiz = await self.repo.get_quiz_by_id(submission.quiz_id)
        if quiz is None:
            raise ExaminationNotFoundException("Khong tim thay ky thi.")

        role = await self._assert_course_member(quiz.course_id, actor)
        is_instructor = (
            role in (ContextualRole.INSTRUCTOR, ContextualRole.TA)
            or _is_system_admin(actor)
        )
        if not is_instructor and submission.user_id != actor.id:
            raise ExaminationForbiddenException("Ban khong co quyen xem ket qua bai thi nay.")

        if submission.status == SubmissionStatus.IN_PROGRESS.value:
            raise ExaminationStateException("Bai thi dang trong qua trinh lam, chua co ket qua.")

        current_time = _ensure_utc(now or datetime.now(timezone.utc))
        release_info = resolve_grade_release_window(
            policy=quiz.grade_release_policy,
            submitted_at=submission.submitted_at,
            available_until=quiz.available_until,
            grades_published_at=quiz.grades_published_at,
            now=current_time,
        )
        show_details = is_instructor or release_info.grades_visible

        questions_analysis: List[ResultQuestionAnalysis] = []
        if show_details:
            attempt_qs = await self.repo.list_attempt_questions(submission.id)
            _, questions_analysis, _ = self._evaluate_submission(
                attempt_qs, dict(submission.student_answers or {})
            )

        regrades = await self.repo.list_regrades_by_submission(submission.id)
        return AttemptResultResponse(
            submission_id=submission.id,
            quiz_id=quiz.id,
            quiz_title=quiz.title,
            status=SubmissionStatus(submission.status),
            submitted_at=submission.submitted_at,
            grade_release_policy=GradeReleasePolicy(quiz.grade_release_policy),
            grades_visible=show_details,
            release_timestamp=release_info.release_timestamp,
            regrade_deadline=release_info.regrade_deadline,
            can_request_regrade=release_info.can_request_regrade,
            auto_score=submission.auto_score if show_details else None,
            final_score=submission.final_score if show_details else None,
            questions=questions_analysis,
            regrades=[_to_regrade_summary(r) for r in regrades],
        )

    async def create_regrade_request(
        self,
        submission_id: uuid.UUID,
        payload: RegradeCreateRequest,
        actor: User,
        now: Optional[datetime] = None,
    ) -> RegradeSummaryResponse:
        """Create a per-question regrade request within 48h of grade release (E-REG-01)."""
        submission = await self.repo.get_submission_by_id(submission_id)
        if submission is None:
            raise ExaminationNotFoundException("Khong tim thay bai lam.")
        if submission.user_id != actor.id:
            raise ExaminationForbiddenException("Chi thi sinh nop bai moi duoc gui don phuc khao.")
        if submission.status == SubmissionStatus.IN_PROGRESS.value:
            raise ExaminationStateException("Bai thi chua duoc nop, khong the phuc khao.")

        quiz = await self.repo.get_quiz_by_id(submission.quiz_id)
        if quiz is None:
            raise ExaminationNotFoundException("Khong tim thay ky thi.")

        current_time = _ensure_utc(now or datetime.now(timezone.utc))
        release_info = resolve_grade_release_window(
            policy=quiz.grade_release_policy,
            submitted_at=submission.submitted_at,
            available_until=quiz.available_until,
            grades_published_at=quiz.grades_published_at,
            now=current_time,
        )
        if not release_info.grades_visible or release_info.regrade_deadline is None:
            raise ExaminationStateException(
                "Diem thi chua duoc cong bo, chua the gui don phuc khao."
            )
        if current_time > release_info.regrade_deadline:
            raise RegradeWindowExpiredException()

        aq = await self.repo.get_attempt_question_by_id(payload.attempt_question_id)
        if aq is None or aq.submission_id != submission.id:
            raise ExaminationNotFoundException(
                "Cau hoi can phuc khao khong thuoc bai lam nay."
            )

        existing = await self.repo.get_regrade_by_submission_and_question(
            submission.id,
            payload.attempt_question_id,
        )
        if existing is not None:
            raise ExaminationStateException(
                "Ban da gui don phuc khao cho cau hoi nay trong bai thi."
            )

        old_score = (
            submission.final_score
            if submission.final_score is not None
            else (submission.auto_score or Decimal("0.0"))
        )
        regrade = QuizRegrade(
            submission_id=submission.id,
            attempt_question_id=payload.attempt_question_id,
            student_reason=payload.student_reason,
            evidence_url=payload.evidence_url,
            regrade_scope=RegradeScope.SINGLE_STUDENT.value,
            status=RegradeStatus.PENDING.value,
            old_score=old_score,
            created_at=current_time,
        )
        await self.repo.create_regrade(regrade)
        submission.status = SubmissionStatus.REGRADE_PENDING.value
        await self.db.flush()

        return _to_regrade_summary(regrade)

    async def list_quiz_regrades(
        self,
        quiz_id: uuid.UUID,
        actor: User,
        status_filter: Optional[str] = None,
    ) -> List[RegradeSummaryResponse]:
        quiz = await self.repo.get_quiz_by_id(quiz_id)
        if quiz is None:
            raise ExaminationNotFoundException("Khong tim thay ky thi.")
        await self._assert_instructor(quiz.course_id, actor)
        regrades = await self.repo.list_regrades_by_quiz(quiz.id, status_filter=status_filter)
        return [_to_regrade_summary(r) for r in regrades]

    async def review_regrade_request(
        self,
        regrade_id: uuid.UUID,
        payload: RegradeReviewRequest,
        actor: User,
        now: Optional[datetime] = None,
    ) -> RegradeReviewResponse:
        """
        Review a regrade request (T2-P-M4-04):
        - Rejects cleanly without altering scores.
        - Approves `SINGLE_STUDENT` by adjusting the target student's score and emitting Outbox.
        - Approves `ENTIRE_CLASS` atomically in 1 transaction:
          1. Updates answer key on `examination.quiz_questions`.
          2. Updates answer key on ALL `examination.quiz_attempt_questions` of that quiz question.
          3. Re-scores ALL submitted `examination.quiz_submissions` of the quiz.
          4. Auto-closes sibling PENDING regrades on the same question.
          5. Emits Outbox Event `examination.quiz_regraded`.
        """
        regrade = await self.repo.get_regrade_by_id(regrade_id)
        if regrade is None:
            raise ExaminationNotFoundException("Khong tim thay don phuc khao.")
        if regrade.status != RegradeStatus.PENDING.value:
            raise ExaminationStateException("Don phuc khao nay da duoc xu ly truoc do.")

        submission = await self.repo.get_submission_by_id(regrade.submission_id)
        if submission is None:
            raise ExaminationNotFoundException("Khong tim thay bai lam lien ket.")
        quiz = await self.repo.get_quiz_by_id(submission.quiz_id)
        if quiz is None:
            raise ExaminationNotFoundException("Khong tim thay ky thi.")

        await self._assert_instructor(quiz.course_id, actor)
        current_time = _ensure_utc(now or datetime.now(timezone.utc))

        # Case 1: Rejected
        if not payload.approved:
            regrade.status = RegradeStatus.REJECTED.value
            regrade.reviewer_feedback = payload.reviewer_feedback
            regrade.reviewed_by = actor.id
            regrade.reviewed_at = current_time
            await self.db.flush()

            sub_regrades = await self.repo.list_regrades_by_submission(submission.id)
            if not any(r.status == RegradeStatus.PENDING.value for r in sub_regrades):
                submission.status = SubmissionStatus.REGRADE_RESOLVED.value
                await self.db.flush()

            return RegradeReviewResponse(
                regrade=_to_regrade_summary(regrade),
                affected_submissions_count=0,
                closed_pending_regrades_count=0,
            )

        # Case 2: Approved — SINGLE_STUDENT
        if payload.regrade_scope == RegradeScope.SINGLE_STUDENT:
            if payload.new_score is None:
                raise ExaminationValidationException(
                    detail="Vui long cung cap diem so moi (new_score) khi duyet phuc khao ca nhan.",
                    field="new_score",
                )
            old_score = submission.final_score or submission.auto_score or Decimal("0.0")
            regrade.regrade_scope = RegradeScope.SINGLE_STUDENT.value
            regrade.status = RegradeStatus.APPROVED.value
            regrade.new_score = payload.new_score
            regrade.reviewer_feedback = payload.reviewer_feedback
            regrade.reviewed_by = actor.id
            regrade.reviewed_at = current_time
            submission.final_score = payload.new_score
            await self.db.flush()

            sub_regrades = await self.repo.list_regrades_by_submission(submission.id)
            if not any(r.status == RegradeStatus.PENDING.value for r in sub_regrades):
                submission.status = SubmissionStatus.REGRADE_RESOLVED.value
                await self.db.flush()

            sub_qs = await self.repo.list_attempt_questions(submission.id)
            _, _, sub_outcomes = self._evaluate_submission(
                sub_qs, dict(submission.student_answers or {})
            )
            await self.repo.enqueue_outbox_event(
                event_type="examination.quiz_regraded",
                aggregate_type="QuizRegrade",
                aggregate_id=regrade.id,
                payload={
                    "course_id": str(quiz.course_id),
                    "quiz_id": str(quiz.id),
                    "regrade_id": str(regrade.id),
                    "regrade_scope": RegradeScope.SINGLE_STUDENT.value,
                    "affected_submissions": [
                        {
                            "submission_id": str(submission.id),
                            "user_id": str(submission.user_id),
                            "old_score": float(old_score),
                            "new_score": float(payload.new_score),
                            "question_outcomes": sub_outcomes,
                        }
                    ],
                },
            )
            return RegradeReviewResponse(
                regrade=_to_regrade_summary(regrade),
                affected_submissions_count=1,
                closed_pending_regrades_count=0,
            )

        # Case 3: Approved — ENTIRE_CLASS (atomic re-scoring across all class submissions)
        if not payload.award_full_question_credit and not payload.correct_option_ids:
            raise ExaminationValidationException(
                detail=(
                    "Khi duyet cham lai toan lop (ENTIRE_CLASS), can cung cap "
                    "correct_option_ids hoac bat award_full_question_credit."
                ),
                field="correct_option_ids",
            )

        if regrade.attempt_question_id is None:
            raise ExaminationValidationException(
                detail="Don phuc khao khong gan voi cau hoi cu the de cham lai toan lop.",
                field="attempt_question_id",
            )

        target_aq = await self.repo.get_attempt_question_by_id(regrade.attempt_question_id)
        if target_aq is None:
            raise ExaminationNotFoundException("Khong tim thay ban chup cau hoi de cham lai.")

        # Step 3.1: Update Tier-1 examination.quiz_questions answer key
        tier1_qq: Optional[QuizQuestion] = None
        if target_aq.quiz_question_id is not None:
            tier1_qq = await self.repo.get_quiz_question_by_id(target_aq.quiz_question_id)
        elif target_aq.question_id is not None:
            tier1_qq = await self.repo.get_quiz_question_by_quiz_and_question_id(
                quiz.id,
                target_aq.question_id,
            )
        if tier1_qq is not None:
            tier1_qq.options_snapshot = _apply_regrade_key_update(
                tier1_qq.options_snapshot or [],
                payload.correct_option_ids,
                payload.award_full_question_credit,
            )

        # Step 3.2: Update ALL Tier-2 examination.quiz_attempt_questions of that quiz question
        class_attempt_qs = await self.repo.list_attempt_questions_for_quiz_question(
            quiz_id=quiz.id,
            quiz_question_id=target_aq.quiz_question_id,
            question_id=target_aq.question_id,
        )
        for aq in class_attempt_qs:
            aq.options_snapshot = _apply_regrade_key_update(
                aq.options_snapshot or [],
                payload.correct_option_ids,
                payload.award_full_question_credit,
            )
        await self.db.flush()

        # Step 3.3: Re-score ALL submitted quiz_submissions of this quiz
        class_submissions = await self.repo.list_submitted_submissions_by_quiz(quiz.id)
        affected_payload: List[Dict[str, Any]] = []
        new_score_by_sub: Dict[uuid.UUID, Decimal] = {}

        for sub in class_submissions:
            prev_score = sub.final_score if sub.final_score is not None else (sub.auto_score or Decimal("0.0"))
            sub_qs = await self.repo.list_attempt_questions(sub.id)
            recomputed, _, sub_outcomes = self._evaluate_submission(
                sub_qs, dict(sub.student_answers or {})
            )
            sub.final_score = recomputed
            new_score_by_sub[sub.id] = recomputed
            affected_payload.append(
                {
                    "submission_id": str(sub.id),
                    "user_id": str(sub.user_id),
                    "old_score": float(prev_score),
                    "new_score": float(recomputed),
                    "question_outcomes": sub_outcomes,
                }
            )

        # Step 3.4: Close primary regrade + all sibling PENDING regrades on the same question
        sibling_pending = await self.repo.list_pending_regrades_for_quiz_question(
            quiz_id=quiz.id,
            quiz_question_id=target_aq.quiz_question_id,
            question_id=target_aq.question_id,
        )
        regrade.regrade_scope = RegradeScope.ENTIRE_CLASS.value
        regrade.status = RegradeStatus.APPROVED.value
        regrade.new_score = new_score_by_sub.get(submission.id, submission.final_score)
        regrade.reviewer_feedback = payload.reviewer_feedback
        regrade.reviewed_by = actor.id
        regrade.reviewed_at = current_time

        closed_siblings = 0
        affected_sub_ids = {submission.id}
        for other in sibling_pending:
            if other.id == regrade.id:
                continue
            other.regrade_scope = RegradeScope.ENTIRE_CLASS.value
            other.status = RegradeStatus.APPROVED.value
            other.new_score = new_score_by_sub.get(other.submission_id)
            other.reviewer_feedback = payload.reviewer_feedback
            other.reviewed_by = actor.id
            other.reviewed_at = current_time
            affected_sub_ids.add(other.submission_id)
            closed_siblings += 1

        await self.db.flush()

        for sub in class_submissions:
            if sub.id in affected_sub_ids:
                sub_regrades = await self.repo.list_regrades_by_submission(sub.id)
                if not any(r.status == RegradeStatus.PENDING.value for r in sub_regrades):
                    sub.status = SubmissionStatus.REGRADE_RESOLVED.value
        await self.db.flush()

        # Step 3.5: Emit Outbox Event examination.quiz_regraded
        await self.repo.enqueue_outbox_event(
            event_type="examination.quiz_regraded",
            aggregate_type="QuizRegrade",
            aggregate_id=regrade.id,
            payload={
                "course_id": str(quiz.course_id),
                "quiz_id": str(quiz.id),
                "regrade_id": str(regrade.id),
                "regrade_scope": RegradeScope.ENTIRE_CLASS.value,
                "affected_submissions": affected_payload,
            },
        )

        return RegradeReviewResponse(
            regrade=_to_regrade_summary(regrade),
            affected_submissions_count=len(class_submissions),
            closed_pending_regrades_count=closed_siblings,
        )

    # Helper exposed for unit testing / Lượt 3B reuse
    @staticmethod
    def get_role_visibility_flags(role: ContextualRole, is_admin: bool = False) -> Tuple[bool, bool]:
        is_instructor = is_admin or role in (ContextualRole.INSTRUCTOR, ContextualRole.TA)
        return is_instructor, not is_instructor
