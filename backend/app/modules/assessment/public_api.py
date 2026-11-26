# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Public service contract exposed by Assessment Context for Gradebook & SpeedGrader."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
import difflib
import os
from typing import Any, Dict, List, Optional, Tuple
import uuid
import zipfile
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.storage_client import STORAGE_URI_PREFIX, storage_client
from app.modules.assessment.ingestion.document_summarizer import DocumentSummarizer
from app.modules.assessment.models import (
    Assignment,
    AssignmentSubmission,
    Rubric,
)


@dataclass(frozen=True)
class AssignmentMetaDTO:
    """Lightweight assignment metadata for syncing Gradebook columns."""

    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    due_date: datetime
    is_viva_required: bool
    viva_question_count: int


@dataclass(frozen=True)
class RubricCriterionDTO:
    """Immutable Rubric criterion passed to AI Grader and SpeedGrader."""

    id: uuid.UUID
    lo_id: Optional[uuid.UUID]
    competency_code: Optional[str]
    title: str
    description: Optional[str]
    max_points: Decimal
    order_index: int
    rating_levels: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class RubricDTO:
    """Immutable Rubric definition linked to an assignment."""

    id: uuid.UUID
    assignment_id: uuid.UUID
    title: str
    total_points: Decimal
    is_frozen: bool
    criteria: List[RubricCriterionDTO] = field(default_factory=list)


@dataclass(frozen=True)
class SubmissionVersionDTO:
    """Lightweight version metadata for v1/v2 switching."""

    submission_id: uuid.UUID
    version: int
    submitted_at: datetime
    is_late: bool
    file_url: Optional[str]
    git_repo_url: Optional[str]


@dataclass(frozen=True)
class SubmissionArtifactDTO:
    """Aggregated read-only submission + Viva + Rubric bundle for Gradebook/SpeedGrader."""

    submission_id: uuid.UUID
    assignment_id: uuid.UUID
    assignment_title: str
    course_id: uuid.UUID
    course_name: str
    student_id: uuid.UUID
    student_name: str
    student_email: str
    student_code: Optional[str]
    version: int
    versions: List[SubmissionVersionDTO]
    project_title: Optional[str]
    file_url: Optional[str]
    git_repo_url: Optional[str]
    comments: Optional[str]
    self_contribution_pct: int
    ai_disclosure_data: Dict[str, Any]
    submitted_at: datetime
    is_late: bool
    late_penalty_applied: float
    status: str
    viva_status: Optional[str]
    viva_started_at: Optional[datetime]
    viva_completed_at: Optional[datetime]
    ai_digest_summary: Optional[str]
    digest_type: Optional[str]
    summarizer_mode: Optional[str]
    generation_source: Optional[str]
    questions: List[Dict[str, Any]]
    answers: Dict[str, Any]
    violation_logs: List[Dict[str, Any]]
    rubric: Optional[RubricDTO]


@dataclass(frozen=True)
class SubmissionNavRowDTO:
    """Submission summary row for SpeedGrader top navigation bar."""

    submission_id: uuid.UUID
    assignment_id: uuid.UUID
    user_id: uuid.UUID
    user_code: Optional[str]
    student_name: str
    student_email: str
    version: int
    submitted_at: datetime
    is_late: bool
    late_penalty_applied: float
    viva_status: Optional[str]


class AssessmentPublicService:
    """Cross-context read/write contract keeping assessment.* ORM internals encapsulated."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_course_assignments_meta(self, course_id: uuid.UUID) -> List[AssignmentMetaDTO]:
        """List assignments in a course for Gradebook column synchronization."""
        stmt = (
            select(Assignment)
            .where(Assignment.course_id == course_id)
            .order_by(Assignment.due_date.asc())
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        return [
            AssignmentMetaDTO(
                id=a.id,
                course_id=a.course_id,
                title=a.title,
                due_date=a.due_date,
                is_viva_required=bool(a.is_viva_required),
                viva_question_count=int(a.viva_question_count or 3),
            )
            for a in rows
        ]

    async def get_assignment_meta(self, assignment_id: uuid.UUID) -> Optional[AssignmentMetaDTO]:
        """Fetch a single assignment's metadata."""
        row = (
            await self.db.execute(select(Assignment).where(Assignment.id == assignment_id))
        ).scalar_one_or_none()
        if row is None:
            return None
        return AssignmentMetaDTO(
            id=row.id,
            course_id=row.course_id,
            title=row.title,
            due_date=row.due_date,
            is_viva_required=bool(row.is_viva_required),
            viva_question_count=int(row.viva_question_count or 3),
        )

    async def get_assignment_rubric(self, assignment_id: uuid.UUID) -> Optional[RubricDTO]:
        """Return immutable RubricDTO with ordered criteria for an assignment."""
        stmt = (
            select(Rubric)
            .where(Rubric.assignment_id == assignment_id)
            .options(selectinload(Rubric.criteria))
        )
        rubric = (await self.db.execute(stmt)).scalar_one_or_none()
        if rubric is None:
            return None
        criteria = [
            RubricCriterionDTO(
                id=c.id,
                lo_id=c.lo_id,
                competency_code=c.competency_code,
                title=c.title,
                description=c.description,
                max_points=Decimal(str(c.max_points)),
                order_index=c.order_index,
                rating_levels=list(c.rating_levels or [])
                if isinstance(c.rating_levels, list)
                else [c.rating_levels] if isinstance(c.rating_levels, dict) else [],
            )
            for c in sorted(rubric.criteria, key=lambda item: item.order_index)
        ]
        return RubricDTO(
            id=rubric.id,
            assignment_id=rubric.assignment_id,
            title=rubric.title,
            total_points=Decimal(str(rubric.total_points)),
            is_frozen=bool(rubric.is_frozen),
            criteria=criteria,
        )

    async def list_assignment_submissions_for_grading(
        self,
        assignment_id: uuid.UUID,
    ) -> List[SubmissionNavRowDTO]:
        """Return the latest submission version per student for SpeedGrader navigation."""
        stmt = (
            select(AssignmentSubmission)
            .where(AssignmentSubmission.assignment_id == assignment_id)
            .options(
                selectinload(AssignmentSubmission.user),
                selectinload(AssignmentSubmission.viva_transcript),
            )
            .order_by(AssignmentSubmission.user_id, desc(AssignmentSubmission.version))
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        latest_by_user: Dict[uuid.UUID, AssignmentSubmission] = {}
        for sub in rows:
            if sub.user_id not in latest_by_user:
                latest_by_user[sub.user_id] = sub

        result: List[SubmissionNavRowDTO] = []
        for sub in sorted(latest_by_user.values(), key=lambda s: s.submitted_at, reverse=True):
            student = sub.user
            result.append(
                SubmissionNavRowDTO(
                    submission_id=sub.id,
                    assignment_id=sub.assignment_id,
                    user_id=sub.user_id,
                    user_code=student.user_code if student else None,
                    student_name=student.full_name if student else "Sinh vien",
                    student_email=student.email if student else "",
                    version=sub.version,
                    submitted_at=sub.submitted_at,
                    is_late=bool(sub.is_late),
                    late_penalty_applied=float(sub.late_penalty_applied or 0.0),
                    viva_status=sub.viva_transcript.status if sub.viva_transcript else None,
                )
            )
        return result

    async def get_submission_bundle(
        self,
        submission_id: uuid.UUID,
    ) -> Optional[SubmissionArtifactDTO]:
        """Load complete submission, all student versions, Viva transcript, and Rubric."""
        stmt = (
            select(AssignmentSubmission)
            .where(AssignmentSubmission.id == submission_id)
            .options(
                selectinload(AssignmentSubmission.assignment).selectinload(Assignment.course),
                selectinload(AssignmentSubmission.user),
                selectinload(AssignmentSubmission.viva_transcript),
            )
        )
        sub = (await self.db.execute(stmt)).scalar_one_or_none()
        if sub is None or sub.assignment is None:
            return None

        ver_stmt = (
            select(AssignmentSubmission)
            .where(
                AssignmentSubmission.assignment_id == sub.assignment_id,
                AssignmentSubmission.user_id == sub.user_id,
            )
            .order_by(desc(AssignmentSubmission.version))
        )
        ver_rows = (await self.db.execute(ver_stmt)).scalars().all()
        versions = [
            SubmissionVersionDTO(
                submission_id=v.id,
                version=v.version,
                submitted_at=v.submitted_at,
                is_late=bool(v.is_late),
                file_url=v.file_url,
                git_repo_url=v.git_repo_url,
            )
            for v in ver_rows
        ]

        rubric = await self.get_assignment_rubric(sub.assignment_id)
        transcript = sub.viva_transcript
        qa_data = dict(transcript.questions_answers or {}) if transcript else {}
        student = sub.user
        course = sub.assignment.course

        return SubmissionArtifactDTO(
            submission_id=sub.id,
            assignment_id=sub.assignment_id,
            assignment_title=sub.assignment.title,
            course_id=sub.assignment.course_id,
            course_name=course.name if course else "",
            student_id=sub.user_id,
            student_name=student.full_name if student else "Sinh vien",
            student_email=student.email if student else "",
            student_code=student.user_code if student else None,
            version=sub.version,
            versions=versions,
            project_title=sub.project_title,
            file_url=sub.file_url,
            git_repo_url=sub.git_repo_url,
            comments=sub.comments,
            self_contribution_pct=sub.self_contribution_pct,
            ai_disclosure_data=dict(sub.ai_disclosure_data or {}),
            submitted_at=sub.submitted_at,
            is_late=bool(sub.is_late),
            late_penalty_applied=float(sub.late_penalty_applied or 0.0),
            status=sub.status,
            viva_status=transcript.status if transcript else None,
            viva_started_at=transcript.started_at if transcript else None,
            viva_completed_at=transcript.completed_at if transcript else None,
            ai_digest_summary=qa_data.get("ai_digest_summary"),
            digest_type=qa_data.get("digest_type"),
            summarizer_mode=qa_data.get("summarizer_mode"),
            generation_source=qa_data.get("generation_source"),
            questions=list(qa_data.get("questions", []) or []),
            answers=dict(qa_data.get("answers", {}) or {}),
            violation_logs=list(transcript.violation_logs or []) if transcript else [],
            rubric=rubric,
        )

    async def mark_submission_graded(self, submission_id: uuid.UUID) -> None:
        """Update AssignmentSubmission.status to GRADED when instructor saves official grade."""
        stmt = select(AssignmentSubmission).where(AssignmentSubmission.id == submission_id)
        sub = (await self.db.execute(stmt)).scalar_one_or_none()
        if sub is not None:
            sub.status = "GRADED"
            await self.db.flush()

    async def extract_preview_text(self, file_url: Optional[str], max_chars: int = 20000) -> str:
        """Safely extract readable text/code preview from storage:// or local submission file."""
        if not file_url:
            return ""
        tmp_path = None
        cleanup = False
        try:
            if file_url.startswith(STORAGE_URI_PREFIX):
                tmp_path, cleanup = await storage_client.materialize_temp_file(file_url)
            elif os.path.isfile(file_url):
                tmp_path = file_url
            else:
                return ""

            ext = os.path.splitext(tmp_path)[1].lower()
            if ext in {".txt", ".md", ".py", ".ts", ".tsx", ".js", ".json", ".sql"}:
                with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read(max_chars)
            if ext in {".pdf", ".docx"}:
                return DocumentSummarizer().extract_text_from_file(tmp_path)[:max_chars]
            if ext == ".zip" and zipfile.is_zipfile(tmp_path):
                chunks: List[str] = []
                total = 0
                with zipfile.ZipFile(tmp_path, "r") as zf:
                    for info in zf.infolist():
                        if info.is_dir():
                            continue
                        if any(
                            skip in info.filename
                            for skip in ("node_modules/", ".git/", "__pycache__/", "venv/")
                        ):
                            continue
                        f_ext = os.path.splitext(info.filename)[1].lower()
                        if f_ext not in {".py", ".ts", ".tsx", ".js", ".jsx", ".sql", ".md", ".txt", ".json"}:
                            continue
                        raw = zf.read(info.filename).decode("utf-8", errors="ignore")
                        block = f"=== {info.filename} ===\n{raw}\n"
                        chunks.append(block)
                        total += len(block)
                        if total >= max_chars:
                            break
                return "\n".join(chunks)[:max_chars]
            return ""
        except Exception:
            return ""
        finally:
            if cleanup and tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    async def compute_versions_diff(
        self,
        v1_sub_id: uuid.UUID,
        v2_sub_id: uuid.UUID,
    ) -> Tuple[List[Dict[str, str]], str]:
        """Compute line-by-line diff between two submission versions (Subflow A-2 of M5-04)."""
        b1 = await self.get_submission_bundle(v1_sub_id)
        b2 = await self.get_submission_bundle(v2_sub_id)
        if b1 is None or b2 is None:
            return [], "Khong tim thay phien ban bai nop de so sanh."

        text1 = await self.extract_preview_text(b1.file_url) or (b1.ai_digest_summary or "")
        text2 = await self.extract_preview_text(b2.file_url) or (b2.ai_digest_summary or "")
        lines1 = text1.splitlines()
        lines2 = text2.splitlines()

        diff_rows: List[Dict[str, str]] = []
        added_count = 0
        removed_count = 0
        for line in difflib.unified_diff(
            lines1,
            lines2,
            fromfile=f"v{b1.version}",
            tofile=f"v{b2.version}",
            lineterm="",
        ):
            if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
                diff_rows.append({"line_type": "context", "content": line})
            elif line.startswith("+"):
                added_count += 1
                diff_rows.append({"line_type": "added", "content": line[1:]})
            elif line.startswith("-"):
                removed_count += 1
                diff_rows.append({"line_type": "removed", "content": line[1:]})
            else:
                diff_rows.append({"line_type": "context", "content": line[1:] if line.startswith(" ") else line})

        summary = f"So sanh v{b1.version} va v{b2.version}: +{added_count} dong moi, -{removed_count} dong xoa."
        return diff_rows[:600], summary
