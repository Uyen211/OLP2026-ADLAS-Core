# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""
Service implementing T2-P-M5-04: SpeedGrader 3-Column Cockpit.
Aggregates submission artifacts, Viva integrity evidence, AI Rubric proposals,
instructor override with audit trail (E-GB-07), 30s feedback draft (BR-SPEED-01),
and Voice Feedback persisted in Supabase Storage / S3 Object Storage.
"""

from datetime import datetime, timezone
from decimal import Decimal
import os
from typing import Dict, List, Optional, Tuple
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.storage_client import ObjectStorageClient, storage_client
from app.modules.assessment.public_api import AssessmentPublicService
from app.modules.gradebook.ai_grader_service import AIGraderService
from app.modules.gradebook.calculation import validate_score_range
from app.modules.gradebook.enums import (
    EvidenceFlag,
    GradeItemType,
    GradingStatus,
    SpeedGraderFilter,
)
from app.modules.gradebook.exceptions import (
    GradebookInvalidVoiceFileException,
    GradebookLockedException,
    GradebookNotFoundException,
    GradeOverrideReasonRequiredException,
)
from app.modules.gradebook.models import GradebookColumn, GradeEntry
from app.modules.gradebook.repository import GradebookRepository
from app.modules.gradebook.schemas import (
    RubricCriterionViewDTO,
    SpeedGraderDraftRequest,
    SpeedGraderSaveGradeRequest,
    SpeedGraderSubmissionListResponse,
    SpeedGraderSubmissionNavItem,
    SpeedGraderVersionItemDTO,
    SpeedGraderWorkspaceResponse,
    VersionDiffLineDTO,
    VersionDiffResponse,
)
from app.modules.gradebook.structure_service import GradebookStructureService

OVERRIDE_REASON_THRESHOLD = Decimal("1.50")
ALLOWED_VOICE_EXTENSIONS = {".webm", ".mp3", ".ogg", ".wav", ".m4a"}
MAX_VOICE_BYTES = 10 * 1024 * 1024  # 10MB max (~2 minutes audio)


class SpeedGraderService:
    """Orchestrates the 3-column SpeedGrader grading workflow and Voice Feedback storage."""

    def __init__(
        self,
        db: AsyncSession,
        repo: Optional[GradebookRepository] = None,
        assessment_public: Optional[AssessmentPublicService] = None,
        storage: Optional[ObjectStorageClient] = None,
    ):
        self.db = db
        self.repo = repo or GradebookRepository(db)
        self.assessment_public = assessment_public or AssessmentPublicService(db)
        self.structure_service = GradebookStructureService(db, self.repo)
        self.storage = storage or storage_client

    async def _ensure_assignment_column(
        self,
        course_id: uuid.UUID,
        assignment_id: uuid.UUID,
        assignment_title: str,
    ) -> GradebookColumn:
        col = await self.repo.get_column_by_item(
            course_id, GradeItemType.ASSIGNMENT.value, assignment_id
        )
        if col is not None:
            return col
        groups = await self.structure_service._ensure_default_structure(course_id)
        target_group = next(
            (g for g in groups if "bai tap" in g.group_name.lower() or "do an" in g.group_name.lower()),
            groups[0],
        )
        return await self.repo.add_column(
            GradebookColumn(
                id=uuid.uuid4(),
                course_id=course_id,
                group_id=target_group.id,
                item_type=GradeItemType.ASSIGNMENT.value,
                item_id=assignment_id,
                title=assignment_title[:150],
                max_points=Decimal("10.00"),
                is_muted=True,
            )
        )

    async def list_assignment_submissions(
        self,
        assignment_id: uuid.UUID,
        filter_mode: SpeedGraderFilter = SpeedGraderFilter.ALL,
    ) -> SpeedGraderSubmissionListResponse:
        """List student submissions for SpeedGrader top bar dropdown, progress counter, and filters."""
        meta = await self.assessment_public.get_assignment_meta(assignment_id)
        if meta is None:
            raise GradebookNotFoundException("bai tap")

        nav_rows = await self.assessment_public.list_assignment_submissions_for_grading(assignment_id)
        col = await self.repo.get_column_by_item(
            meta.course_id, GradeItemType.ASSIGNMENT.value, assignment_id
        )
        grades_by_user: Dict[uuid.UUID, GradeEntry] = {}
        if col is not None:
            entries = await self.repo.list_grades_for_columns([col.id])
            grades_by_user = {e.user_id: e for e in entries}

        all_items: List[SpeedGraderSubmissionNavItem] = []
        graded_count = 0
        for row in nav_rows:
            entry = grades_by_user.get(row.user_id)
            is_graded = entry is not None and entry.official_score is not None
            if is_graded:
                graded_count += 1
            all_items.append(
                SpeedGraderSubmissionNavItem(
                    submission_id=row.submission_id,
                    user_id=row.user_id,
                    user_code=row.user_code,
                    student_name=row.student_name,
                    student_email=row.student_email,
                    version=row.version,
                    submitted_at=row.submitted_at,
                    is_late=row.is_late,
                    late_penalty_applied=row.late_penalty_applied,
                    viva_status=row.viva_status,
                    grading_status=entry.grading_status if entry else GradingStatus.UNGRADED.value,
                    official_score=entry.official_score if entry else None,
                    proposed_ai_score=entry.proposed_ai_score if entry else None,
                    evidence_flag=entry.evidence_flag if entry else None,
                )
            )

        if filter_mode == SpeedGraderFilter.NEEDS_GRADING:
            filtered = [i for i in all_items if i.official_score is None]
        elif filter_mode == SpeedGraderFilter.GRADED:
            filtered = [i for i in all_items if i.official_score is not None]
        elif filter_mode == SpeedGraderFilter.CONFLICTING:
            filtered = [i for i in all_items if i.evidence_flag == EvidenceFlag.CONFLICTING.value]
        else:
            filtered = all_items

        total = len(all_items)
        pct = round((graded_count / total) * 100.0, 1) if total > 0 else 0.0
        return SpeedGraderSubmissionListResponse(
            assignment_id=assignment_id,
            assignment_title=meta.title,
            course_id=meta.course_id,
            total_submissions=total,
            graded_count=graded_count,
            progress_percent=pct,
            items=filtered,
        )

    async def get_workspace(self, submission_id: uuid.UUID) -> SpeedGraderWorkspaceResponse:
        """Aggregate all 3 columns of SpeedGrader for a student submission (T2-P-M5-04)."""
        bundle = await self.assessment_public.get_submission_bundle(submission_id)
        if bundle is None:
            raise GradebookNotFoundException("bai nop sinh vien")

        col = await self._ensure_assignment_column(
            bundle.course_id, bundle.assignment_id, bundle.assignment_title
        )
        is_locked = await self.repo.is_course_locked(bundle.course_id)
        entry = await self.repo.get_grade_entry(col.id, bundle.student_id)

        blur_count = sum(
            1 for log in bundle.violation_logs if isinstance(log, dict) and log.get("type") == "WINDOW_BLUR"
        )
        paste_count = sum(
            1 for log in bundle.violation_logs if isinstance(log, dict) and log.get("type") == "PASTE_ATTEMPT"
        )
        missing_viva = bundle.viva_status not in {"COMPLETED", "TIMEOUT"}

        criteria_views = [
            RubricCriterionViewDTO(
                id=c.id,
                lo_id=c.lo_id,
                competency_code=c.competency_code,
                title=c.title,
                description=c.description,
                max_points=c.max_points,
                order_index=c.order_index,
                rating_levels=c.rating_levels,
            )
            for c in (bundle.rubric.criteria if bundle.rubric else [])
        ]

        ai_proposal = None
        if entry is not None and isinstance(entry.ai_proposed_details, dict):
            ai_proposal = AIGraderService._to_proposal_response(submission_id, entry.ai_proposed_details)

        return SpeedGraderWorkspaceResponse(
            course_id=bundle.course_id,
            course_name=bundle.course_name,
            assignment_id=bundle.assignment_id,
            assignment_title=bundle.assignment_title,
            column_id=col.id,
            is_gradebook_locked=is_locked,
            is_column_muted=col.is_muted,
            submission_id=bundle.submission_id,
            student_id=bundle.student_id,
            student_name=bundle.student_name,
            student_email=bundle.student_email,
            student_code=bundle.student_code,
            version=bundle.version,
            versions=[
                SpeedGraderVersionItemDTO(
                    submission_id=v.submission_id,
                    version=v.version,
                    submitted_at=v.submitted_at,
                    is_late=v.is_late,
                    file_url=v.file_url,
                    git_repo_url=v.git_repo_url,
                )
                for v in bundle.versions
            ],
            project_title=bundle.project_title,
            file_url=bundle.file_url,
            git_repo_url=bundle.git_repo_url,
            comments=bundle.comments,
            self_contribution_pct=bundle.self_contribution_pct,
            ai_disclosure_data=bundle.ai_disclosure_data,
            submitted_at=bundle.submitted_at,
            is_late=bundle.is_late,
            late_penalty_applied=bundle.late_penalty_applied,
            missing_viva=missing_viva,
            viva_status=bundle.viva_status,
            viva_started_at=bundle.viva_started_at,
            viva_completed_at=bundle.viva_completed_at,
            ai_digest_summary=bundle.ai_digest_summary,
            digest_type=bundle.digest_type,
            summarizer_mode=bundle.summarizer_mode,
            generation_source=bundle.generation_source,
            questions=bundle.questions,
            answers=bundle.answers,
            violation_logs=bundle.violation_logs,
            window_blur_count=blur_count,
            paste_attempt_count=paste_count,
            rubric_id=bundle.rubric.id if bundle.rubric else None,
            rubric_title=bundle.rubric.title if bundle.rubric else None,
            rubric_criteria=criteria_views,
            ai_proposal=ai_proposal,
            grade_id=entry.id if entry else None,
            official_score=entry.official_score if entry else None,
            rubric_scores=dict(entry.rubric_scores or {}) if entry else {},
            instructor_feedback=entry.instructor_feedback if entry else None,
            voice_feedback_url=entry.voice_feedback_url if entry else None,
            is_overridden=bool(entry.is_overridden) if entry else False,
            grading_status=entry.grading_status if entry else GradingStatus.UNGRADED.value,
            graded_at=entry.graded_at if entry else None,
        )

    async def save_official_grade(
        self,
        submission_id: uuid.UUID,
        payload: SpeedGraderSaveGradeRequest,
        actor_id: uuid.UUID,
    ) -> SpeedGraderWorkspaceResponse:
        """
        Save instructor official score & feedback (Human-in-the-Loop BR-07):
        - Rejects if gradebook locked (E-14)
        - Validates [0.0, 10.0] (E-GB-02)
        - Enforces mandatory override_reason if delta > 1.5 pts vs AI proposal (E-GB-07)
        - Logs immutable audit trail and updates submission status to GRADED
        """
        bundle = await self.assessment_public.get_submission_bundle(submission_id)
        if bundle is None:
            raise GradebookNotFoundException("bai nop sinh vien")

        if await self.repo.is_course_locked(bundle.course_id):
            raise GradebookLockedException()

        score = validate_score_range(payload.official_score)
        col = await self._ensure_assignment_column(
            bundle.course_id, bundle.assignment_id, bundle.assignment_title
        )
        entry = await self.repo.get_grade_entry(col.id, bundle.student_id)
        now = datetime.now(timezone.utc)

        is_overridden = False
        if entry is not None and entry.proposed_ai_score is not None:
            delta = abs(score - Decimal(str(entry.proposed_ai_score)))
            if delta > Decimal("0.00"):
                is_overridden = True
            if delta > OVERRIDE_REASON_THRESHOLD and not (payload.override_reason or "").strip():
                raise GradeOverrideReasonRequiredException(float(delta))

        old_values = None
        if entry is None:
            entry = GradeEntry(
                id=uuid.uuid4(),
                column_id=col.id,
                user_id=bundle.student_id,
                submission_id=bundle.submission_id,
                official_score=score,
                rubric_scores=payload.rubric_scores,
                instructor_feedback=payload.instructor_feedback,
                voice_feedback_url=payload.voice_feedback_url,
                is_overridden=is_overridden,
                grading_status=GradingStatus.INSTRUCTOR_REVIEWED.value,
                graded_by=actor_id,
                graded_at=now,
                updated_at=now,
            )
        else:
            old_values = {
                "official_score": str(entry.official_score) if entry.official_score is not None else None,
                "proposed_ai_score": str(entry.proposed_ai_score) if entry.proposed_ai_score is not None else None,
                "is_overridden": entry.is_overridden,
            }
            entry.submission_id = bundle.submission_id
            entry.official_score = score
            entry.rubric_scores = payload.rubric_scores
            entry.instructor_feedback = payload.instructor_feedback
            if payload.voice_feedback_url is not None:
                entry.voice_feedback_url = payload.voice_feedback_url
            entry.is_overridden = is_overridden
            entry.grading_status = GradingStatus.INSTRUCTOR_REVIEWED.value
            entry.graded_by = actor_id
            entry.graded_at = now
            entry.updated_at = now

        await self.repo.save_grade_entry(entry)
        await self.repo.add_audit_log(
            user_id=actor_id,
            action_type="SPEEDGRADER_OVERRIDE" if is_overridden else "SPEEDGRADER_GRADE",
            entity_name="grades",
            entity_id=entry.id,
            old_values=old_values,
            new_values={
                "official_score": str(score),
                "submission_id": str(submission_id),
                "is_overridden": is_overridden,
            },
            reason=(payload.override_reason or "").strip() or None,
        )
        await self.assessment_public.mark_submission_graded(submission_id)
        return await self.get_workspace(submission_id)

    async def save_feedback_draft(
        self,
        submission_id: uuid.UUID,
        payload: SpeedGraderDraftRequest,
        actor_id: uuid.UUID,
    ) -> Dict[str, str]:
        """30-second autosave draft for instructor feedback without finalizing score (BR-SPEED-01)."""
        bundle = await self.assessment_public.get_submission_bundle(submission_id)
        if bundle is None:
            raise GradebookNotFoundException("bai nop sinh vien")
        if await self.repo.is_course_locked(bundle.course_id):
            raise GradebookLockedException()

        col = await self._ensure_assignment_column(
            bundle.course_id, bundle.assignment_id, bundle.assignment_title
        )
        entry = await self.repo.get_grade_entry(col.id, bundle.student_id)
        now = datetime.now(timezone.utc)
        if entry is None:
            entry = GradeEntry(
                id=uuid.uuid4(),
                column_id=col.id,
                user_id=bundle.student_id,
                submission_id=bundle.submission_id,
                instructor_feedback=payload.instructor_feedback,
                rubric_scores=payload.rubric_scores or {},
                grading_status=GradingStatus.UNGRADED.value,
                updated_at=now,
            )
        else:
            if payload.instructor_feedback is not None:
                entry.instructor_feedback = payload.instructor_feedback
            if payload.rubric_scores is not None:
                entry.rubric_scores = payload.rubric_scores
            entry.updated_at = now
        await self.repo.save_grade_entry(entry)
        return {"status": "draft_saved", "saved_at": now.isoformat()}

    async def get_submission_preview(self, submission_id: uuid.UUID) -> Dict[str, str]:
        """Return safe text/code preview extracted from Supabase Storage / S3 / legacy file."""
        bundle = await self.assessment_public.get_submission_bundle(submission_id)
        if bundle is None:
            raise GradebookNotFoundException("bai nop sinh vien")
        content = await self.assessment_public.extract_preview_text(bundle.file_url)
        return {
            "submission_id": str(submission_id),
            "file_url": bundle.file_url or "",
            "preview_text": content,
        }

    async def download_submission_bytes(self, submission_id: uuid.UUID) -> Tuple[bytes, str, str]:
        """Download raw submission artifact bytes via ObjectStorageClient (returns bytes, media_type, filename)."""
        bundle = await self.assessment_public.get_submission_bundle(submission_id)
        if bundle is None or not bundle.file_url:
            raise GradebookNotFoundException("tep bai nop")
        data, content_type = await self.storage.download_bytes(bundle.file_url)
        filename = os.path.basename(bundle.file_url.split("?")[0]) or f"submission-v{bundle.version}"
        return data, content_type, filename

    async def get_versions_diff(
        self,
        submission_id: uuid.UUID,
        compare_to_id: Optional[uuid.UUID] = None,
    ) -> VersionDiffResponse:
        """Compare two submission versions of the same student (Subflow A-2 of M5-04)."""
        bundle = await self.assessment_public.get_submission_bundle(submission_id)
        if bundle is None:
            raise GradebookNotFoundException("bai nop sinh vien")
        if len(bundle.versions) < 2:
            raise GradebookNotFoundException("phien ban truoc de so sanh")

        ordered = sorted(bundle.versions, key=lambda v: v.version)
        if compare_to_id is not None:
            other = next((v for v in ordered if v.submission_id == compare_to_id), None)
            if other is None:
                raise GradebookNotFoundException("phien ban doi chieu")
            v1_meta, v2_meta = (
                (other, next(v for v in ordered if v.submission_id == submission_id))
                if other.version < bundle.version
                else (next(v for v in ordered if v.submission_id == submission_id), other)
            )
        else:
            v1_meta, v2_meta = ordered[-2], ordered[-1]

        rows, summary = await self.assessment_public.compute_versions_diff(
            v1_meta.submission_id, v2_meta.submission_id
        )
        return VersionDiffResponse(
            v1_submission_id=v1_meta.submission_id,
            v2_submission_id=v2_meta.submission_id,
            v1_version=v1_meta.version,
            v2_version=v2_meta.version,
            summary=summary,
            lines=[VersionDiffLineDTO(line_type=r["line_type"], content=r["content"]) for r in rows],
        )

    async def upload_voice_feedback(
        self,
        data: bytes,
        filename: str,
        content_type: str,
        actor_id: uuid.UUID,
    ) -> Dict[str, str]:
        """
        Persist instructor voice feedback (.webm/.mp3, max 10MB) to Supabase Storage / S3.
        Returns a Backend proxy URL so Frontend plays audio securely with JWT authorization.
        """
        clean_name = os.path.basename(filename or "voice-feedback.webm")
        ext = os.path.splitext(clean_name)[1].lower() or ".webm"
        if ext not in ALLOWED_VOICE_EXTENSIONS:
            raise GradebookInvalidVoiceFileException(
                f"Dinh dang tep am thanh '{ext}' khong duoc ho tro. Chi chap nhan .webm, .mp3, .ogg, .wav."
            )
        if len(data) == 0:
            raise GradebookInvalidVoiceFileException("Tep ghi am khong co du lieu.")
        if len(data) > MAX_VOICE_BYTES:
            raise GradebookInvalidVoiceFileException("Tep ghi am vuot qua dung luong toi da 10MB (E-7).")

        object_key = f"{actor_id}/{uuid.uuid4()}{ext}"
        stored_uri = await self.storage.upload_bytes(
            bucket=settings.MINIO_BUCKET_VOICE,
            object_key=object_key,
            data=data,
            content_type=content_type or "audio/webm",
        )
        return {
            "voice_feedback_url": f"/api/v1/gradebook/voice-feedback/{object_key}",
            "storage_uri": stored_uri,
            "storage_backend": self.storage.last_backend,
        }

    async def download_voice_feedback(self, object_key: str) -> Tuple[bytes, str]:
        """Stream voice feedback audio bytes from Supabase Storage / S3 via Backend proxy."""
        clean_key = object_key.lstrip("/")
        if ".." in clean_key.split("/"):
            raise GradebookNotFoundException("tep ghi am")
        uri = ObjectStorageClient.build_uri(settings.MINIO_BUCKET_VOICE, clean_key)
        try:
            return await self.storage.download_bytes(uri)
        except FileNotFoundError:
            raise GradebookNotFoundException("tep ghi am")
