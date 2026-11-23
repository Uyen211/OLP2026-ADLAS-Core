# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Assessment and submission lifecycle service enforcing deadlines, late penalties and versioning."""

from datetime import datetime, timezone
import math
from typing import Optional
import uuid
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.modules.ai_gateway.service import AIGatewayService
from app.modules.assessment.exceptions import (
    AIDisclosureValidationException,
    AssessmentNotFoundException,
    InvalidSubmissionPayloadException,
    PublicGitRepositoryException,
    SubmissionCutoffExceededException,
)
from app.modules.assessment.ingestion.digest_builder import UniversalDigestBuilder
from app.modules.assessment.models import Assignment, AssignmentSubmission, Rubric, VivaTranscript
from app.modules.assessment.schemas import AssignmentDetailResponse, SubmissionCreateRequest, SubmissionResponse


class AssessmentSubmissionService:
    """Service handling assignment retrieval, submission cutoff rules and version tracking."""

    def __init__(
        self,
        digest_builder: Optional[UniversalDigestBuilder] = None,
        ai_gateway: Optional[AIGatewayService] = None
    ):
        self.digest_builder = digest_builder or UniversalDigestBuilder()
        self.ai_gateway = ai_gateway or AIGatewayService()

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
            submissions=[SubmissionResponse.model_validate(s) for s in submissions]
        )

    async def create_submission(
        self,
        db: AsyncSession,
        assignment_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: SubmissionCreateRequest
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

        # 4. Validate payload completeness (E-7)
        if not payload.file_url and not payload.git_repo_url:
            raise InvalidSubmissionPayloadException("Submission must provide either a file upload URL or a Git repository link.")

        # 5. Validate Git URL if provided (E-GIT-01)
        if payload.git_repo_url:
            if not (payload.git_repo_url.startswith("https://") or payload.git_repo_url.startswith("http://")):
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
            await self._initialize_viva_transcript(
                db=db,
                assignment=assignment,
                submission=submission,
                payload=payload
            )

        await db.commit()
        await db.refresh(submission)
        return SubmissionResponse.model_validate(submission)

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
