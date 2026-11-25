# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Public service contract exposed by Examination Context for TV1 (Gradebook) and TV2 (AI Tutor)."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.examination.enums import SecurityMode
from app.modules.examination.exceptions import ExamAiLockedException
from app.modules.examination.repository import ExaminationRepository


@dataclass(frozen=True)
class ActiveExamSessionDTO:
    """Read-only active exam session status used by Learning/AI Tutor to enforce E-13."""

    has_active_session: bool
    is_ai_locked: bool
    quiz_id: Optional[uuid.UUID] = None
    submission_id: Optional[uuid.UUID] = None
    expires_at: Optional[datetime] = None


class ExaminationPublicService:
    """Public cross-module interface without exposing examination.* ORM internals."""

    def __init__(
        self,
        db: AsyncSession,
        repo: Optional[ExaminationRepository] = None,
    ):
        self.db = db
        self.repo = repo or ExaminationRepository(db)

    async def get_active_controlled_session(
        self,
        course_id: uuid.UUID,
        user_id: uuid.UUID,
        now: Optional[datetime] = None,
    ) -> ActiveExamSessionDTO:
        """Return whether the student is currently in an active CONTROLLED / AI-locked exam."""
        current_time = now or datetime.now(timezone.utc)
        sub = await self.repo.get_active_ai_locked_submission_for_user(
            course_id=course_id,
            user_id=user_id,
            now=current_time,
        )
        if sub is None:
            return ActiveExamSessionDTO(has_active_session=False, is_ai_locked=False)

        quiz = await self.repo.get_quiz_by_id(sub.quiz_id)
        is_controlled_locked = bool(
            quiz is not None
            and quiz.is_ai_locked
            and quiz.security_mode in (
                SecurityMode.CONTROLLED.value,
                SecurityMode.REMOTE_PROCTORED.value,
            )
        )
        return ActiveExamSessionDTO(
            has_active_session=True,
            is_ai_locked=is_controlled_locked,
            quiz_id=sub.quiz_id,
            submission_id=sub.id,
            expires_at=sub.expires_at,
        )

    async def assert_ai_tutor_allowed(
        self,
        course_id: uuid.UUID,
        user_id: uuid.UUID,
        now: Optional[datetime] = None,
    ) -> None:
        """Raise ExamAiLockedException (E-13) if student has an active AI-locked exam session."""
        session_info = await self.get_active_controlled_session(course_id, user_id, now=now)
        if session_info.has_active_session and session_info.is_ai_locked:
            raise ExamAiLockedException()

    async def get_best_quiz_score(
        self,
        quiz_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[Decimal]:
        """Return the highest graded `final_score` for a student across all attempts (max_attempts)."""
        return await self.repo.get_best_score_for_user(quiz_id, user_id)
