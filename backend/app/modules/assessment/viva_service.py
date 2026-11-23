# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Viva Sandbox engine managing isolated sessions, countdown timers, and integrity audit trails."""

from datetime import datetime, timezone
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.modules.assessment.exceptions import (
    VivaAnswerWordCountException,
    VivaSessionCompletedException,
    VivaSessionNotFoundException,
    VivaTimeoutException,
)
from app.modules.assessment.models import VivaTranscript
from app.modules.assessment.schemas import (
    VivaAnswerSubmitRequest,
    VivaAnswerSubmitResponse,
    VivaQuestionSchema,
    VivaStartResponse,
)


class VivaSandboxService:
    """Service governing Viva Sandbox examination lifecycle, paste locks, and blur logs."""

    async def start_session(
        self,
        db: AsyncSession,
        submission_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> VivaStartResponse:
        """Initialize or resume an active Viva defense session."""
        stmt = (
            select(VivaTranscript)
            .where(VivaTranscript.submission_id == submission_id)
            .options(selectinload(VivaTranscript.submission))
        )
        res = await db.execute(stmt)
        transcript = res.scalar_one_or_none()
        if not transcript:
            raise VivaSessionNotFoundException(str(submission_id))

        if transcript.submission.user_id != user_id:
            raise VivaSessionNotFoundException(str(submission_id))

        if transcript.status in {"COMPLETED", "TIMEOUT"}:
            raise VivaSessionCompletedException()

        now = datetime.now(timezone.utc)
        qa_data = dict(transcript.questions_answers)
        total_questions = qa_data.get("total_questions", 3)
        total_duration_seconds = total_questions * 300  # N x 5 minutes

        if transcript.status == "READY":
            transcript.status = "IN_PROGRESS"
            transcript.started_at = now
            transcript.submission.status = "IN_VIVA"
            await db.commit()

        # Check time-out
        elapsed = (now - transcript.started_at).total_seconds()
        if elapsed > total_duration_seconds:
            transcript.status = "TIMEOUT"
            transcript.completed_at = now
            transcript.submission.status = "VIVA_COMPLETED"
            await db.commit()
            raise VivaTimeoutException()

        curr_idx = qa_data.get("current_index", 1)
        questions = qa_data.get("questions", [])
        active_q_raw = questions[curr_idx - 1] if curr_idx <= len(questions) else questions[0]
        active_question = VivaQuestionSchema(**active_q_raw)

        return VivaStartResponse(
            session_id=transcript.id,
            submission_id=submission_id,
            total_questions=total_questions,
            total_duration_seconds=total_duration_seconds,
            current_question_index=curr_idx,
            question=active_question,
            status=transcript.status,
            violation_logs=transcript.violation_logs or []
        )

    async def submit_answer(
        self,
        db: AsyncSession,
        submission_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: VivaAnswerSubmitRequest
    ) -> VivaAnswerSubmitResponse:
        """Validate word count (>= 50 words) and record typed answer sequentially."""
        stmt = (
            select(VivaTranscript)
            .where(VivaTranscript.submission_id == submission_id)
            .options(selectinload(VivaTranscript.submission))
        )
        res = await db.execute(stmt)
        transcript = res.scalar_one_or_none()
        if not transcript or transcript.submission.user_id != user_id:
            raise VivaSessionNotFoundException(str(submission_id))

        if transcript.status in {"COMPLETED", "TIMEOUT"}:
            raise VivaSessionCompletedException()

        now = datetime.now(timezone.utc)
        qa_data = dict(transcript.questions_answers)
        total_questions = qa_data.get("total_questions", 3)
        total_duration_seconds = total_questions * 300

        # Enforce countdown deadline
        elapsed = (now - transcript.started_at).total_seconds()
        if elapsed > total_duration_seconds:
            transcript.status = "TIMEOUT"
            transcript.completed_at = now
            transcript.submission.status = "VIVA_COMPLETED"
            await db.commit()
            raise VivaTimeoutException()

        # Enforce Minimum 50 words (BR-VIVA / E-1)
        words = payload.answer_text.strip().split()
        if len(words) < 50:
            raise VivaAnswerWordCountException(word_count=len(words), min_words=50)

        # Record answer
        answers = qa_data.get("answers", {})
        answers[payload.question_id] = {
            "answer_text": payload.answer_text,
            "time_spent_seconds": payload.time_spent_seconds,
            "submitted_at": now.isoformat()
        }
        qa_data["answers"] = answers

        curr_idx = qa_data.get("current_index", 1)
        if curr_idx < total_questions:
            qa_data["current_index"] = curr_idx + 1
            transcript.questions_answers = qa_data
            await db.commit()

            questions = qa_data.get("questions", [])
            next_q_raw = questions[curr_idx]
            next_q = VivaQuestionSchema(**next_q_raw)

            return VivaAnswerSubmitResponse(
                session_id=transcript.id,
                is_completed=False,
                next_question=next_q,
                status="IN_PROGRESS",
                message="Answer recorded successfully. Proceed to the next question."
            )
        else:
            # Final Question Answered -> Complete and Seal
            transcript.status = "COMPLETED"
            transcript.completed_at = now
            transcript.questions_answers = qa_data
            transcript.submission.status = "VIVA_COMPLETED"
            await db.commit()

            return VivaAnswerSubmitResponse(
                session_id=transcript.id,
                is_completed=True,
                next_question=None,
                status="COMPLETED",
                message="Viva defense session completed and sealed for grading."
            )

    async def record_security_violation(
        self,
        db: AsyncSession,
        submission_id: uuid.UUID,
        user_id: uuid.UUID,
        violation_type: str,
        details: dict
    ) -> bool:
        """Log integrity violations such as PASTE_ATTEMPT (E-9) or WINDOW_BLUR (E-VIVA-01)."""
        stmt = (
            select(VivaTranscript)
            .where(VivaTranscript.submission_id == submission_id)
            .options(selectinload(VivaTranscript.submission))
        )
        res = await db.execute(stmt)
        transcript = res.scalar_one_or_none()
        if not transcript or transcript.submission.user_id != user_id:
            return False

        logs = list(transcript.violation_logs)
        logs.append({
            "type": violation_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details or {}
        })
        transcript.violation_logs = logs
        await db.commit()
        return True
