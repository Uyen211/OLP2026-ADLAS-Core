# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""
Service implementing T2-I-M5-03: AI Rubric Cross-Evidence Proposal Assistant.
Reads submission digest + Viva transcript via AssessmentPublicService, calls AIGatewayService,
and persists AI_PROPOSED scores and citations without overriding instructor official scores (BR-07).
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.ai_gateway.service import AIGatewayService
from app.modules.assessment.public_api import AssessmentPublicService, SubmissionArtifactDTO
from app.modules.gradebook.enums import EvidenceFlag, GradeItemType, GradingStatus
from app.modules.gradebook.exceptions import GradebookLockedException, GradebookNotFoundException
from app.modules.gradebook.models import GradebookColumn, GradeEntry
from app.modules.gradebook.repository import GradebookRepository
from app.modules.gradebook.schemas import (
    CitationItemSchema,
    CriterionProposalSchema,
    RubricProposalResponse,
)
from app.modules.gradebook.structure_service import GradebookStructureService


class AIGraderService:
    """Orchestrates AI Rubric evaluation and persists proposed scores for SpeedGrader."""

    def __init__(
        self,
        db: AsyncSession,
        repo: Optional[GradebookRepository] = None,
        ai_gateway: Optional[AIGatewayService] = None,
        assessment_public: Optional[AssessmentPublicService] = None,
    ):
        self.db = db
        self.repo = repo or GradebookRepository(db)
        self.ai_gateway = ai_gateway or AIGatewayService()
        self.assessment_public = assessment_public or AssessmentPublicService(db)
        self.structure_service = GradebookStructureService(db, self.repo)

    async def _ensure_assignment_column(self, bundle: SubmissionArtifactDTO) -> GradebookColumn:
        """Ensure a GradebookColumn exists for the assignment so AI proposals can always be stored."""
        existing = await self.repo.get_column_by_item(
            bundle.course_id, GradeItemType.ASSIGNMENT.value, bundle.assignment_id
        )
        if existing is not None:
            return existing
        groups = await self.structure_service._ensure_default_structure(bundle.course_id)
        target_group = next(
            (g for g in groups if "bai tap" in g.group_name.lower() or "do an" in g.group_name.lower()),
            groups[0],
        )
        col = GradebookColumn(
            id=uuid.uuid4(),
            course_id=bundle.course_id,
            group_id=target_group.id,
            item_type=GradeItemType.ASSIGNMENT.value,
            item_id=bundle.assignment_id,
            title=bundle.assignment_title[:150],
            max_points=Decimal("10.00"),
            is_muted=True,
        )
        return await self.repo.add_column(col)

    async def generate_rubric_proposal(
        self,
        submission_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
    ) -> RubricProposalResponse:
        """
        Evaluate a student submission against its Rubric using saved Call-1 AI Digest
        and Viva Q&A transcript. Never overwrites instructor official_score (BR-07).
        """
        bundle = await self.assessment_public.get_submission_bundle(submission_id)
        if bundle is None:
            raise GradebookNotFoundException("bai nop sinh vien")

        if await self.repo.is_course_locked(bundle.course_id):
            raise GradebookLockedException()

        rubric_criteria_payload: List[Dict[str, Any]] = []
        if bundle.rubric is not None:
            for c in bundle.rubric.criteria:
                rubric_criteria_payload.append({
                    "id": str(c.id),
                    "title": c.title,
                    "description": c.description or "",
                    "max_points": float(c.max_points),
                    "lo_id": str(c.lo_id) if c.lo_id else None,
                    "rating_levels": c.rating_levels,
                })

        digest_text = (bundle.ai_digest_summary or "").strip()
        if not digest_text and bundle.file_url:
            digest_text = await self.assessment_public.extract_preview_text(bundle.file_url, max_chars=8000)

        eval_result = await self.ai_gateway.evaluate_rubric_cross_evidence(
            assignment_title=bundle.assignment_title,
            project_title=bundle.project_title or bundle.assignment_title,
            digest_summary=digest_text,
            ai_disclosure=bundle.ai_disclosure_data,
            viva_questions=bundle.questions,
            viva_answers=bundle.answers,
            violation_logs=bundle.violation_logs,
            rubric_criteria=rubric_criteria_payload,
        )

        # Persist proposal into gradebook.grades (never overwriting official_score)
        col = await self._ensure_assignment_column(bundle)
        entry = await self.repo.get_grade_entry(col.id, bundle.student_id)
        now = datetime.now(timezone.utc)
        proposed_total = (
            Decimal(str(eval_result["proposed_total_score"])).quantize(Decimal("0.01"))
            if eval_result.get("proposed_total_score") is not None
            else None
        )
        all_citations: List[Dict[str, Any]] = []
        for cp in eval_result.get("criteria_proposals", []):
            for cit in cp.get("citations", []):
                all_citations.append({"criterion_id": cp["criterion_id"], **cit})

        if entry is None:
            entry = GradeEntry(
                id=uuid.uuid4(),
                column_id=col.id,
                user_id=bundle.student_id,
                submission_id=bundle.submission_id,
                proposed_ai_score=proposed_total,
                proposed_ai_citations=all_citations,
                evidence_flag=eval_result["evidence_flag"],
                ai_proposed_details=eval_result,
                grading_status=GradingStatus.AI_PROPOSED.value,
                updated_at=now,
            )
        else:
            entry.submission_id = bundle.submission_id
            entry.proposed_ai_score = proposed_total
            entry.proposed_ai_citations = all_citations
            entry.evidence_flag = eval_result["evidence_flag"]
            entry.ai_proposed_details = eval_result
            if entry.official_score is None:
                entry.grading_status = GradingStatus.AI_PROPOSED.value
            entry.updated_at = now

        await self.repo.save_grade_entry(entry)
        await self.repo.add_audit_log(
            user_id=actor_id,
            action_type="AI_RUBRIC_PROPOSAL",
            entity_name="grades",
            entity_id=entry.id,
            new_values={
                "evidence_flag": eval_result["evidence_flag"],
                "proposed_ai_score": str(proposed_total) if proposed_total is not None else None,
                "generation_source": eval_result.get("generation_source", "gemini_live"),
            },
        )
        return self._to_proposal_response(submission_id, eval_result)

    @staticmethod
    def _to_proposal_response(
        submission_id: uuid.UUID,
        raw: Dict[str, Any],
    ) -> RubricProposalResponse:
        criteria_items: List[CriterionProposalSchema] = []
        for cp in raw.get("criteria_proposals", []):
            citations = [
                CitationItemSchema(
                    source_type=c.get("source_type", "SUBMISSION"),
                    reference=c.get("reference", "Trich dan"),
                    excerpt=c.get("excerpt", ""),
                )
                for c in cp.get("citations", [])
                if isinstance(c, dict) and c.get("excerpt")
            ]
            criteria_items.append(
                CriterionProposalSchema(
                    criterion_id=str(cp.get("criterion_id", "")),
                    criterion_title=str(cp.get("criterion_title", "")),
                    max_points=Decimal(str(cp.get("max_points", 0))),
                    proposed_points=Decimal(str(cp.get("proposed_points", 0))),
                    rating_level_label=str(cp.get("rating_level_label", "")),
                    explanation=str(cp.get("explanation", "")),
                    citations=citations,
                )
            )
        flag_str = str(raw.get("evidence_flag") or EvidenceFlag.HUMAN_REVIEW.value)
        try:
            flag = EvidenceFlag(flag_str)
        except ValueError:
            flag = EvidenceFlag.HUMAN_REVIEW

        total = (
            Decimal(str(raw["proposed_total_score"]))
            if raw.get("proposed_total_score") is not None
            else None
        )
        return RubricProposalResponse(
            submission_id=submission_id,
            evidence_flag=flag,
            proposed_total_score=total,
            summary_comment=str(raw.get("summary_comment") or ""),
            generation_source=str(raw.get("generation_source") or "gemini_live"),
            criteria_proposals=criteria_items,
        )
