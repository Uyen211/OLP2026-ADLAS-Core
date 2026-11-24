# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Assessment and submission lifecycle service enforcing deadlines, late penalties and versioning."""

import asyncio
from datetime import datetime, timezone
import logging
import math
import os
import shutil
from typing import List, Optional
import uuid
from fastapi import BackgroundTasks
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.database import AsyncSessionLocal
from app.modules.ai_gateway.service import AIGatewayService
from app.modules.assessment.exceptions import (
    AIDisclosureValidationException,
    AssessmentNotFoundException,
    IntegrityPledgeRequiredException,
    InvalidSubmissionPayloadException,
    PublicGitRepositoryException,
    SubmissionCutoffExceededException,
)
from app.modules.assessment.ingestion.digest_builder import UniversalDigestBuilder
from app.modules.assessment.models import Assignment, AssignmentSubmission, Rubric, VivaTranscript
from app.modules.assessment.schemas import (
    AssignmentDetailResponse,
    AssignmentSummaryItem,
    SubmissionCreateRequest,
    SubmissionResponse,
)

logger = logging.getLogger(__name__)


class AssessmentSubmissionService:
    """Service handling assignment retrieval, submission cutoff rules and version tracking."""

    def __init__(
        self,
        digest_builder: Optional[UniversalDigestBuilder] = None,
        ai_gateway: Optional[AIGatewayService] = None
    ):
        self.digest_builder = digest_builder or UniversalDigestBuilder()
        self.ai_gateway = ai_gateway or AIGatewayService()

    async def list_course_assignments(
        self,
        db: AsyncSession,
        course_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> List[AssignmentSummaryItem]:
        """List all assignments in a course with student's submission count and latest status."""
        stmt = (
            select(Assignment)
            .where(Assignment.course_id == course_id)
            .options(
                selectinload(Assignment.submissions.and_(AssignmentSubmission.user_id == user_id))
            )
            .order_by(Assignment.due_date.asc())
        )
        res = await db.execute(stmt)
        assignments = res.scalars().all()
        items: List[AssignmentSummaryItem] = []
        for a in assignments:
            subs = sorted(a.submissions, key=lambda s: s.version, reverse=True)
            items.append(
                AssignmentSummaryItem(
                    id=a.id,
                    course_id=a.course_id,
                    title=a.title,
                    due_date=a.due_date,
                    until_date=a.until_date,
                    late_penalty_percent=float(a.late_penalty_percent),
                    is_viva_required=a.is_viva_required,
                    viva_question_count=a.viva_question_count,
                    ai_policy_level=a.ai_policy_level or "YELLOW",
                    submission_count=len(subs),
                    latest_status=subs[0].status if subs else None,
                )
            )
        return items

    async def get_assignment_detail(
        self,
        db: AsyncSession,
        assignment_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> AssignmentDetailResponse:
        """Fetch assignment specification and student submission history."""
        stmt = (
            select(Assignment)
            .where(Assignment.id == assignment_id)
            .options(
                selectinload(Assignment.submissions.and_(AssignmentSubmission.user_id == user_id))
            )
        )
        res = await db.execute(stmt)
        assignment = res.scalar_one_or_none()
        if not assignment:
            raise AssessmentNotFoundException(str(assignment_id))

        submissions = sorted(assignment.submissions, key=lambda s: s.version, reverse=True)
        return AssignmentDetailResponse(
            id=assignment.id,
            course_id=assignment.course_id,
            title=assignment.title,
            instructions=assignment.instructions,
            attachment_url=assignment.attachment_url,
            submission_type=assignment.submission_type,
            allowed_extensions=assignment.allowed_extensions,
            max_file_size_mb=assignment.max_file_size_mb,
            due_date=assignment.due_date,
            until_date=assignment.until_date,
            late_penalty_percent=float(assignment.late_penalty_percent),
            is_viva_required=assignment.is_viva_required,
            viva_question_count=assignment.viva_question_count,
            ai_policy_level=assignment.ai_policy_level or "YELLOW",
            submissions=[SubmissionResponse.model_validate(s) for s in submissions]
        )

    async def create_submission(
        self,
        db: AsyncSession,
        assignment_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: SubmissionCreateRequest,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> SubmissionResponse:
        """Process student submission (v1, v2...) with integrity pledge and AI disclosure."""
        # 1. Fetch assignment
        stmt = (
            select(Assignment)
            .where(Assignment.id == assignment_id)
            .options(selectinload(Assignment.course))
        )
        res = await db.execute(stmt)
        assignment = res.scalar_one_or_none()
        if not assignment:
            raise AssessmentNotFoundException(str(assignment_id))

        now = datetime.now(timezone.utc)

        # 2. Check Cutoff (BR-11 / E-8)
        if assignment.until_date and now > assignment.until_date:
            raise SubmissionCutoffExceededException()

        # 3. Calculate late penalty if submitted past Due Date
        is_late = False
        late_penalty_applied = 0.0
        if now > assignment.due_date:
            is_late = True
            delta_seconds = (now - assignment.due_date).total_seconds()
            days_late = math.ceil(delta_seconds / 86400.0)
            penalty_rate = float(assignment.late_penalty_percent)
            late_penalty_applied = min(100.0, days_late * penalty_rate)

        # 4. Validate payload completeness and academic integrity pledge (E-7 / E-1)
        if not payload.is_pledge_signed:
            raise IntegrityPledgeRequiredException()

        if not payload.file_url and not payload.git_repo_url:
            raise InvalidSubmissionPayloadException("Submission must provide either a file upload URL or a Git repository link.")

        sub_type = (assignment.submission_type or "HYBRID").upper()
        if sub_type == "FILE_UPLOAD" and not payload.file_url:
            raise InvalidSubmissionPayloadException("This assignment requires a file upload.")
        if sub_type == "GIT_REPOSITORY" and not payload.git_repo_url:
            raise InvalidSubmissionPayloadException("This assignment requires a Git repository URL.")

        if payload.file_url and assignment.allowed_extensions:
            target_name = payload.file_name or payload.file_url
            ext = os.path.splitext(target_name)[1].lower()
            allowed = [e.strip().lower() for e in assignment.allowed_extensions.split(",") if e.strip()]
            if allowed and "*" not in allowed and ext and ext not in allowed:
                raise InvalidSubmissionPayloadException(
                    f"Unsupported file extension '{ext}'. Allowed: {assignment.allowed_extensions}"
                )

        # 5. Validate Git URL if provided (E-GIT-01)
        if payload.git_repo_url:
            if not (payload.git_repo_url.startswith("https://") or payload.git_repo_url.startswith("http://")):
                raise PublicGitRepositoryException(payload.git_repo_url)
            if background_tasks is not None:
                is_accessible = await self._verify_public_git_repo(payload.git_repo_url)
                if not is_accessible:
                    raise PublicGitRepositoryException(payload.git_repo_url)

        # 6. Validate AI disclosure length (E-1)
        if not payload.ai_disclosure or len(payload.ai_disclosure.usage_description.strip()) < 20:
            raise AIDisclosureValidationException()

        # 7. Determine version number (v1, v2...)
        ver_stmt = (
            select(AssignmentSubmission.version)
            .where(
                AssignmentSubmission.assignment_id == assignment_id,
                AssignmentSubmission.user_id == user_id
            )
            .order_by(desc(AssignmentSubmission.version))
            .limit(1)
        )
        ver_res = await db.execute(ver_stmt)
        latest_ver = ver_res.scalar_one_or_none()
        new_version = (latest_ver or 0) + 1

        # 8. Freeze Rubric if first submission in the course task
        rubric_stmt = select(Rubric).where(Rubric.assignment_id == assignment_id)
        rubric_res = await db.execute(rubric_stmt)
        rubric = rubric_res.scalar_one_or_none()
        if rubric and not rubric.is_frozen:
            rubric.is_frozen = True

        # 9. Create submission entity
        submission = AssignmentSubmission(
            id=uuid.uuid4(),
            assignment_id=assignment_id,
            user_id=user_id,
            version=new_version,
            project_title=payload.project_title,
            file_url=payload.file_url,
            git_repo_url=payload.git_repo_url,
            comments=payload.comments,
            ai_disclosure_data=payload.ai_disclosure.model_dump(),
            self_contribution_pct=payload.ai_disclosure.self_contribution_pct,
            is_pledge_signed=payload.is_pledge_signed,
            submitted_at=now,
            is_late=is_late,
            late_penalty_applied=late_penalty_applied,
            status="PENDING_VIVA" if assignment.is_viva_required else "SUBMITTED"
        )
        db.add(submission)
        await db.flush()

        # 10. Prepare Viva Sandbox defense questions if required
        if assignment.is_viva_required:
            if background_tasks is not None:
                viva_transcript = VivaTranscript(
                    id=uuid.uuid4(),
                    submission_id=submission.id,
                    questions_answers={
                        "total_questions": assignment.viva_question_count,
                        "current_index": 1,
                        "questions": [],
                        "answers": {},
                    },
                    violation_logs=[],
                    started_at=datetime.now(timezone.utc),
                    status="PREPARING",
                )
                db.add(viva_transcript)
                await db.commit()
                await db.refresh(submission)
                course_name = assignment.course.name if assignment.course else ""
                background_tasks.add_task(
                    self._prepare_viva_questions_bg,
                    transcript_id=viva_transcript.id,
                    assignment_title=assignment.title,
                    assignment_instructions=assignment.instructions,
                    question_count=assignment.viva_question_count,
                    course_name=course_name,
                    project_title=submission.project_title or "",
                    file_url=payload.file_url,
                    git_repo_url=payload.git_repo_url,
                    file_name=payload.file_name,
                    ai_disclosure=payload.ai_disclosure.model_dump(),
                )
                return SubmissionResponse.model_validate(submission)
            else:
                await self._initialize_viva_transcript(
                    db=db,
                    assignment=assignment,
                    submission=submission,
                    payload=payload
                )

        await db.commit()
        await db.refresh(submission)
        return SubmissionResponse.model_validate(submission)

    @staticmethod
    async def _verify_public_git_repo(repo_url: str) -> bool:
        """Check whether a public HTTP/HTTPS Git repository is reachable."""
        if not shutil.which("git"):
            return True
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "ls-remote", "--exit-code", repo_url,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            )
            await asyncio.wait_for(proc.wait(), timeout=8.0)
            return proc.returncode == 0
        except Exception as exc:
            logger.warning("Git repository reachability check failed for %s: %s", repo_url, exc)
            return False

    async def _prepare_viva_questions_bg(
        self,
        transcript_id: uuid.UUID,
        assignment_title: str,
        assignment_instructions: str,
        question_count: int,
        course_name: str,
        project_title: str,
        file_url: Optional[str],
        git_repo_url: Optional[str],
        file_name: Optional[str],
        ai_disclosure: dict,
    ) -> None:
        """Background worker building submission digest and generating Viva questions."""
        try:
            digest = await self.digest_builder.build_digest(
                file_path=file_url,
                git_repo_url=git_repo_url,
                file_name=file_name,
            )
            questions = await self.ai_gateway.generate_viva_questions(
                assignment_title=assignment_title,
                assignment_instructions=assignment_instructions,
                digest_type=digest.digest_type,
                digest_content=digest.content,
                ai_disclosure=ai_disclosure,
                question_count=question_count,
                course_name=course_name,
                project_title=project_title,
            )
        except Exception as exc:
            logger.error("Background Viva preparation failed (%s), using deterministic fallback", exc)
            questions = self.ai_gateway._generate_deterministic_questions(
                course_name=course_name,
                assignment_title=assignment_title,
                project_title=project_title,
                digest_type="DOCUMENT",
                digest_content="",
                ai_disclosure=ai_disclosure,
                question_count=question_count,
            )

        async with AsyncSessionLocal() as bg_db:
            res = await bg_db.execute(select(VivaTranscript).where(VivaTranscript.id == transcript_id))
            transcript = res.scalar_one_or_none()
            if transcript:
                transcript.questions_answers = {
                    "total_questions": question_count,
                    "current_index": 1,
                    "questions": questions,
                    "answers": {},
                }
                transcript.status = "READY"
                await bg_db.commit()

    async def _initialize_viva_transcript(
        self,
        db: AsyncSession,
        assignment: Assignment,
        submission: AssignmentSubmission,
        payload: SubmissionCreateRequest
    ) -> None:
        """Construct universal digest and generate N adaptive Viva defense questions."""
        digest = await self.digest_builder.build_digest(
            file_path=payload.file_url,
            git_repo_url=payload.git_repo_url,
            file_name=payload.file_name
        )

        course_name = assignment.course.name if assignment.course else ""

        questions = await self.ai_gateway.generate_viva_questions(
            assignment_title=assignment.title,
            assignment_instructions=assignment.instructions,
            digest_type=digest.digest_type,
            digest_content=digest.content,
            ai_disclosure=payload.ai_disclosure.model_dump(),
            question_count=assignment.viva_question_count,
            course_name=course_name,
            project_title=submission.project_title or "",
        )

        qa_payload = {
            "total_questions": assignment.viva_question_count,
            "current_index": 1,
            "questions": questions,
            "answers": {}
        }

        viva_transcript = VivaTranscript(
            id=uuid.uuid4(),
            submission_id=submission.id,
            questions_answers=qa_payload,
            violation_logs=[],
            started_at=datetime.now(timezone.utc),
            status="READY"
        )
        db.add(viva_transcript)
