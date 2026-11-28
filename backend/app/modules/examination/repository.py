# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Async SQLAlchemy repository restricted strictly to examination.* tables and system.outbox_events."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence
import uuid
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.examination.enums import RegradeStatus, SubmissionStatus
from app.modules.examination.models import (
    Question,
    QuestionBank,
    QuestionFolder,
    Quiz,
    QuizAttemptQuestion,
    QuizQuestion,
    QuizRegrade,
    QuizSubmission,
)
from app.modules.system.models import OutboxEvent


class ExaminationRepository:
    """Data access layer for examination.* plus transactional Outbox event insertion."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Question Folders (TV3 Feature)
    # ------------------------------------------------------------------
    async def create_question_folder(self, folder: QuestionFolder) -> QuestionFolder:
        self.db.add(folder)
        await self.db.flush()
        return folder

    async def get_question_folder_by_id(self, folder_id: uuid.UUID) -> Optional[QuestionFolder]:
        stmt = select(QuestionFolder).where(QuestionFolder.id == folder_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_question_folders_by_course(self, course_id: uuid.UUID) -> List[QuestionFolder]:
        stmt = (
            select(QuestionFolder)
            .where(QuestionFolder.course_id == course_id)
            .order_by(QuestionFolder.created_at.asc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def delete_question_folder(self, folder: QuestionFolder) -> None:
        await self.db.delete(folder)
        await self.db.flush()

    async def list_questions_for_draw_rule(
        self,
        course_id: uuid.UUID,
        folder_id: Optional[uuid.UUID] = None,
        bank_id: Optional[uuid.UUID] = None,
        difficulty: Optional[str] = None,
    ) -> List[Question]:
        stmt = (
            select(Question)
            .join(QuestionBank, QuestionBank.id == Question.bank_id)
            .where(
                QuestionBank.course_id == course_id,
                Question.is_active.is_(True),
            )
        )
        if folder_id is not None:
            stmt = stmt.where(Question.folder_id == folder_id)
        if bank_id is not None:
            stmt = stmt.where(Question.bank_id == bank_id)
        if difficulty is not None:
            stmt = stmt.where(Question.difficulty == difficulty)

        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    # ------------------------------------------------------------------
    # Question Banks
    # ------------------------------------------------------------------
    async def create_question_bank(self, bank: QuestionBank) -> QuestionBank:
        self.db.add(bank)
        await self.db.flush()
        return bank

    async def get_question_bank_by_id(self, bank_id: uuid.UUID) -> Optional[QuestionBank]:
        stmt = select(QuestionBank).where(QuestionBank.id == bank_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_question_banks_by_course(self, course_id: uuid.UUID) -> List[QuestionBank]:
        stmt = (
            select(QuestionBank)
            .where(QuestionBank.course_id == course_id)
            .order_by(QuestionBank.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_active_questions_by_banks(
        self,
        bank_ids: Sequence[uuid.UUID],
    ) -> Dict[uuid.UUID, int]:
        if not bank_ids:
            return {}
        stmt = (
            select(Question.bank_id, func.count(Question.id))
            .where(
                Question.bank_id.in_(bank_ids),
                Question.is_active.is_(True),
            )
            .group_by(Question.bank_id)
        )
        result = await self.db.execute(stmt)
        return {row[0]: int(row[1]) for row in result.all()}

    async def delete_question_bank(self, bank: QuestionBank) -> None:
        await self.db.delete(bank)
        await self.db.flush()

    # ------------------------------------------------------------------
    # Questions (with Snapshot-aware Soft Delete & LO Reference Check)
    # ------------------------------------------------------------------
    async def create_question(self, question: Question) -> Question:
        self.db.add(question)
        await self.db.flush()
        return question

    async def get_question_by_id(
        self,
        question_id: uuid.UUID,
        include_inactive: bool = False,
    ) -> Optional[Question]:
        stmt = select(Question).where(Question.id == question_id)
        if not include_inactive:
            stmt = stmt.where(Question.is_active.is_(True))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_questions_by_course(
        self,
        course_id: uuid.UUID,
        bank_id: Optional[uuid.UUID] = None,
        lo_id: Optional[uuid.UUID] = None,
        bloom_level: Optional[str] = None,
        search_query: Optional[str] = None,
        include_inactive: bool = False,
    ) -> List[Question]:
        stmt = (
            select(Question)
            .join(QuestionBank, QuestionBank.id == Question.bank_id)
            .where(QuestionBank.course_id == course_id)
        )
        if not include_inactive:
            stmt = stmt.where(Question.is_active.is_(True))
        if bank_id is not None:
            stmt = stmt.where(Question.bank_id == bank_id)
        if lo_id is not None:
            stmt = stmt.where(Question.lo_id == lo_id)
        if bloom_level:
            stmt = stmt.where(Question.bloom_level == bloom_level.upper())
        if search_query:
            q = f"%{search_query.strip()}%"
            stmt = stmt.where(Question.question_text.ilike(q))

        stmt = stmt.order_by(Question.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_active_questions_for_matrix(
        self,
        bank_id: uuid.UUID,
        bloom_level: Optional[str] = None,
        lo_id: Optional[uuid.UUID] = None,
    ) -> List[Question]:
        """Fetch active questions matching a quiz matrix cell filter."""
        stmt = select(Question).where(
            Question.bank_id == bank_id,
            Question.is_active.is_(True),
        )
        if bloom_level:
            stmt = stmt.where(Question.bloom_level == bloom_level.upper())
        if lo_id is not None:
            stmt = stmt.where(Question.lo_id == lo_id)
        stmt = stmt.order_by(Question.created_at.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def is_question_snapshotted(self, question_id: uuid.UUID) -> bool:
        """Check whether a question has ever been frozen into examination.quiz_questions."""
        stmt = select(func.count(QuizQuestion.id)).where(
            QuizQuestion.question_id == question_id
        )
        result = await self.db.execute(stmt)
        return int(result.scalar() or 0) > 0

    async def soft_delete_question(self, question: Question) -> Question:
        """Mark question inactive while preserving historical snapshot referential integrity."""
        now = datetime.now(timezone.utc)
        question.is_active = False
        question.deleted_at = now
        question.updated_at = now
        await self.db.flush()
        return question

    async def hard_delete_question(self, question: Question) -> None:
        await self.db.delete(question)
        await self.db.flush()

    async def delete_question_respecting_snapshot(self, question: Question) -> bool:
        """
        Soft-delete if the question was ever snapshotted into quiz_questions;
        otherwise perform a physical delete.
        Returns True if soft-deleted, False if physically deleted.
        """
        if await self.is_question_snapshotted(question.id):
            await self.soft_delete_question(question)
            return True
        await self.hard_delete_question(question)
        return False

    async def is_lo_referenced(self, lo_id: uuid.UUID) -> bool:
        """
        Return True if any active question or frozen quiz snapshot references `lo_id` (BR-LO-01).
        """
        q_stmt = select(func.count(Question.id)).where(
            Question.lo_id == lo_id,
            Question.is_active.is_(True),
        )
        if int((await self.db.execute(q_stmt)).scalar() or 0) > 0:
            return True

        qq_stmt = select(func.count(QuizQuestion.id)).where(QuizQuestion.lo_id == lo_id)
        if int((await self.db.execute(qq_stmt)).scalar() or 0) > 0:
            return True

        return False

    # ------------------------------------------------------------------
    # Quizzes
    # ------------------------------------------------------------------
    async def create_quiz(self, quiz: Quiz) -> Quiz:
        self.db.add(quiz)
        await self.db.flush()
        return quiz

    async def get_quiz_by_id(self, quiz_id: uuid.UUID) -> Optional[Quiz]:
        stmt = select(Quiz).where(Quiz.id == quiz_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_quizzes_by_course(
        self,
        course_id: uuid.UUID,
        status_filter: Optional[str] = None,
    ) -> List[Quiz]:
        stmt = select(Quiz).where(Quiz.course_id == course_id)
        if status_filter:
            stmt = stmt.where(Quiz.status == status_filter.upper())
        stmt = stmt.order_by(Quiz.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_active_ai_locked_submission_for_user(
        self,
        course_id: uuid.UUID,
        user_id: uuid.UUID,
        now: Optional[datetime] = None,
    ) -> Optional[QuizSubmission]:
        """Return an active IN_PROGRESS submission belonging to an AI-locked quiz (E-13)."""
        current_time = now or datetime.now(timezone.utc)
        stmt = (
            select(QuizSubmission)
            .join(Quiz, Quiz.id == QuizSubmission.quiz_id)
            .where(
                Quiz.course_id == course_id,
                Quiz.is_ai_locked.is_(True),
                QuizSubmission.user_id == user_id,
                QuizSubmission.status == SubmissionStatus.IN_PROGRESS.value,
                QuizSubmission.expires_at > current_time,
            )
            .order_by(QuizSubmission.started_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Quiz Questions (Tier-1 Frozen Snapshot)
    # ------------------------------------------------------------------
    async def bulk_create_quiz_questions(
        self,
        quiz_questions: Sequence[QuizQuestion],
    ) -> List[QuizQuestion]:
        items = list(quiz_questions)
        self.db.add_all(items)
        await self.db.flush()
        return items

    async def list_quiz_questions(self, quiz_id: uuid.UUID) -> List[QuizQuestion]:
        stmt = (
            select(QuizQuestion)
            .where(QuizQuestion.quiz_id == quiz_id)
            .order_by(QuizQuestion.question_order.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_quiz_questions(self, quiz_id: uuid.UUID) -> int:
        stmt = select(func.count(QuizQuestion.id)).where(QuizQuestion.quiz_id == quiz_id)
        result = await self.db.execute(stmt)
        return int(result.scalar() or 0)

    async def replace_quiz_questions(
        self,
        quiz_id: uuid.UUID,
        quiz_questions: Sequence[QuizQuestion],
    ) -> List[QuizQuestion]:
        await self.db.execute(delete(QuizQuestion).where(QuizQuestion.quiz_id == quiz_id))
        await self.db.flush()
        return await self.bulk_create_quiz_questions(quiz_questions)

    async def get_quiz_question_by_quiz_and_question_id(
        self,
        quiz_id: uuid.UUID,
        question_id: uuid.UUID,
    ) -> Optional[QuizQuestion]:
        stmt = select(QuizQuestion).where(
            QuizQuestion.quiz_id == quiz_id,
            QuizQuestion.question_id == question_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_quiz_question_by_id(
        self,
        quiz_question_id: uuid.UUID,
    ) -> Optional[QuizQuestion]:
        stmt = select(QuizQuestion).where(QuizQuestion.id == quiz_question_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Quiz Submissions (Attempts & Autosave)
    # ------------------------------------------------------------------
    async def create_submission(self, submission: QuizSubmission) -> QuizSubmission:
        self.db.add(submission)
        await self.db.flush()
        return submission

    async def get_submission_by_id(
        self,
        submission_id: uuid.UUID,
    ) -> Optional[QuizSubmission]:
        stmt = select(QuizSubmission).where(QuizSubmission.id == submission_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_in_progress_submission(
        self,
        quiz_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[QuizSubmission]:
        stmt = (
            select(QuizSubmission)
            .where(
                QuizSubmission.quiz_id == quiz_id,
                QuizSubmission.user_id == user_id,
                QuizSubmission.status == SubmissionStatus.IN_PROGRESS.value,
            )
            .order_by(QuizSubmission.attempt_number.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_submissions_for_user(
        self,
        quiz_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> List[QuizSubmission]:
        stmt = (
            select(QuizSubmission)
            .where(
                QuizSubmission.quiz_id == quiz_id,
                QuizSubmission.user_id == user_id,
            )
            .order_by(QuizSubmission.attempt_number.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_user_attempts(
        self,
        quiz_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> int:
        stmt = select(func.count(QuizSubmission.id)).where(
            QuizSubmission.quiz_id == quiz_id,
            QuizSubmission.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return int(result.scalar() or 0)

    async def list_submitted_submissions_by_quiz(
        self,
        quiz_id: uuid.UUID,
    ) -> List[QuizSubmission]:
        """List all non-in-progress submissions for a quiz (used by ENTIRE_CLASS re-scoring)."""
        stmt = (
            select(QuizSubmission)
            .where(
                QuizSubmission.quiz_id == quiz_id,
                QuizSubmission.status != SubmissionStatus.IN_PROGRESS.value,
            )
            .order_by(QuizSubmission.submitted_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_best_score_for_user(
        self,
        quiz_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[Decimal]:
        """Return highest final_score across all graded attempts of a user in a quiz."""
        stmt = select(func.max(QuizSubmission.final_score)).where(
            QuizSubmission.quiz_id == quiz_id,
            QuizSubmission.user_id == user_id,
            QuizSubmission.final_score.is_not(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def apply_autosave_if_newer(
        self,
        submission_id: uuid.UUID,
        incoming_seq_num: int,
        student_answers: Dict[str, Any],
        flagged_questions: Optional[List[str]] = None,
        tab_blur_delta: int = 0,
        fullscreen_exit_delta: int = 0,
        violation_event: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Atomically persist autosave payload only when `incoming_seq_num > seq_num`.
        Returns True if the row was updated, False if the packet was stale.
        """
        values: Dict[str, Any] = {
            "seq_num": incoming_seq_num,
            "student_answers": student_answers,
            "tab_blur_count": QuizSubmission.tab_blur_count + max(0, tab_blur_delta),
            "fullscreen_exit_count": (
                QuizSubmission.fullscreen_exit_count + max(0, fullscreen_exit_delta)
            ),
        }
        if flagged_questions is not None:
            values["flagged_questions"] = flagged_questions
        if violation_event is not None:
            values["violation_logs"] = QuizSubmission.violation_logs.concat([violation_event])

        stmt = (
            update(QuizSubmission)
            .where(
                QuizSubmission.id == submission_id,
                QuizSubmission.status == SubmissionStatus.IN_PROGRESS.value,
                QuizSubmission.seq_num < incoming_seq_num,
            )
            .values(**values)
            .returning(QuizSubmission.id)
        )
        result = await self.db.execute(stmt)
        updated = result.scalar_one_or_none() is not None
        await self.db.flush()
        return updated

    # ------------------------------------------------------------------
    # Quiz Attempt Questions (Tier-2 Per-student Snapshot)
    # ------------------------------------------------------------------
    async def bulk_create_attempt_questions(
        self,
        attempt_questions: Sequence[QuizAttemptQuestion],
    ) -> List[QuizAttemptQuestion]:
        items = list(attempt_questions)
        self.db.add_all(items)
        await self.db.flush()
        return items

    async def list_attempt_questions(
        self,
        submission_id: uuid.UUID,
    ) -> List[QuizAttemptQuestion]:
        stmt = (
            select(QuizAttemptQuestion)
            .where(QuizAttemptQuestion.submission_id == submission_id)
            .order_by(QuizAttemptQuestion.question_order.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_attempt_question_by_id(
        self,
        attempt_question_id: uuid.UUID,
    ) -> Optional[QuizAttemptQuestion]:
        stmt = select(QuizAttemptQuestion).where(
            QuizAttemptQuestion.id == attempt_question_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_attempt_questions_for_quiz_question(
        self,
        quiz_id: uuid.UUID,
        quiz_question_id: Optional[uuid.UUID] = None,
        question_id: Optional[uuid.UUID] = None,
    ) -> List[QuizAttemptQuestion]:
        """Fetch all student attempt snapshots matching a quiz question for ENTIRE_CLASS regrade."""
        stmt = (
            select(QuizAttemptQuestion)
            .join(QuizSubmission, QuizSubmission.id == QuizAttemptQuestion.submission_id)
            .where(QuizSubmission.quiz_id == quiz_id)
        )
        if quiz_question_id is not None:
            stmt = stmt.where(QuizAttemptQuestion.quiz_question_id == quiz_question_id)
        elif question_id is not None:
            stmt = stmt.where(QuizAttemptQuestion.question_id == question_id)
        else:
            return []

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Quiz Regrades (48h Workflow)
    # ------------------------------------------------------------------
    async def create_regrade(self, regrade: QuizRegrade) -> QuizRegrade:
        self.db.add(regrade)
        await self.db.flush()
        return regrade

    async def get_regrade_by_id(self, regrade_id: uuid.UUID) -> Optional[QuizRegrade]:
        stmt = select(QuizRegrade).where(QuizRegrade.id == regrade_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_regrade_by_submission_and_question(
        self,
        submission_id: uuid.UUID,
        attempt_question_id: Optional[uuid.UUID],
    ) -> Optional[QuizRegrade]:
        stmt = select(QuizRegrade).where(QuizRegrade.submission_id == submission_id)
        if attempt_question_id is None:
            stmt = stmt.where(QuizRegrade.attempt_question_id.is_(None))
        else:
            stmt = stmt.where(QuizRegrade.attempt_question_id == attempt_question_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_regrades_by_submission(
        self,
        submission_id: uuid.UUID,
    ) -> List[QuizRegrade]:
        stmt = (
            select(QuizRegrade)
            .where(QuizRegrade.submission_id == submission_id)
            .order_by(QuizRegrade.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_regrades_by_quiz(
        self,
        quiz_id: uuid.UUID,
        status_filter: Optional[str] = None,
    ) -> List[QuizRegrade]:
        stmt = (
            select(QuizRegrade)
            .join(QuizSubmission, QuizSubmission.id == QuizRegrade.submission_id)
            .where(QuizSubmission.quiz_id == quiz_id)
        )
        if status_filter:
            stmt = stmt.where(QuizRegrade.status == status_filter.upper())
        stmt = stmt.order_by(QuizRegrade.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_pending_regrades_for_quiz_question(
        self,
        quiz_id: uuid.UUID,
        quiz_question_id: Optional[uuid.UUID] = None,
        question_id: Optional[uuid.UUID] = None,
    ) -> List[QuizRegrade]:
        """List all PENDING regrade requests targeting the same question in a quiz."""
        stmt = (
            select(QuizRegrade)
            .join(QuizSubmission, QuizSubmission.id == QuizRegrade.submission_id)
            .join(
                QuizAttemptQuestion,
                QuizAttemptQuestion.id == QuizRegrade.attempt_question_id,
            )
            .where(
                QuizSubmission.quiz_id == quiz_id,
                QuizRegrade.status == RegradeStatus.PENDING.value,
            )
        )
        if quiz_question_id is not None:
            stmt = stmt.where(QuizAttemptQuestion.quiz_question_id == quiz_question_id)
        elif question_id is not None:
            stmt = stmt.where(QuizAttemptQuestion.question_id == question_id)
        else:
            return []

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Transactional Outbox Events
    # ------------------------------------------------------------------
    async def enqueue_outbox_event(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: uuid.UUID,
        payload: Dict[str, Any],
    ) -> OutboxEvent:
        """Persist an OutboxEvent in system.outbox_events within the active transaction."""
        event = OutboxEvent(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            status="PENDING",
        )
        self.db.add(event)
        await self.db.flush()
        return event
