# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Blind peer review and Fi contribution factor calculation service (TV3)."""

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.modules.assessment.authoring_schemas import (
    PeerReviewMemberSummary,
    PeerReviewResponse,
    PeerReviewSubmitRequest,
    PeerReviewSummaryResponse,
)
from app.modules.assessment.exceptions import (
    PeerReviewNotMemberException,
    PeerReviewSelfNotAllowedException,
    StudentGroupNotFoundException,
)
from app.modules.assessment.models import (
    GroupMember,
    PeerReview,
    StudentGroup,
)
from app.modules.identity.models import User


class PeerReviewService:
    """Service managing blind peer reviews and Fi clamping logic [0.50, 1.20]."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def submit_peer_review(
        self,
        assignment_id: uuid.UUID,
        reviewer: User,
        payload: PeerReviewSubmitRequest,
    ) -> PeerReviewResponse:
        """Submit blind evaluation for a group member."""
        if reviewer.id == payload.reviewee_id:
            raise PeerReviewSelfNotAllowedException()

        reviewer_groups_stmt = (
            select(GroupMember.group_id)
            .join(StudentGroup, StudentGroup.id == GroupMember.group_id)
            .where(
                StudentGroup.assignment_id == assignment_id,
                GroupMember.student_id == reviewer.id,
            )
        )
        reviewer_groups_res = await self.db.execute(reviewer_groups_stmt)
        reviewer_group_ids = set(reviewer_groups_res.scalars().all())

        reviewee_groups_stmt = (
            select(GroupMember.group_id)
            .join(StudentGroup, StudentGroup.id == GroupMember.group_id)
            .where(
                StudentGroup.assignment_id == assignment_id,
                GroupMember.student_id == payload.reviewee_id,
            )
        )
        reviewee_groups_res = await self.db.execute(reviewee_groups_stmt)
        reviewee_group_ids = set(reviewee_groups_res.scalars().all())

        common_groups = reviewer_group_ids.intersection(reviewee_group_ids)
        if not common_groups:
            raise PeerReviewNotMemberException()

        existing_stmt = select(PeerReview).where(
            PeerReview.assignment_id == assignment_id,
            PeerReview.milestone_id == payload.milestone_id,
            PeerReview.reviewer_id == reviewer.id,
            PeerReview.reviewee_id == payload.reviewee_id,
        )
        existing_res = await self.db.execute(existing_stmt)
        review = existing_res.scalar_one_or_none()

        if review:
            review.criteria_scores_json = payload.criteria_scores
            review.total_score = payload.total_score
            review.comment = payload.comment
            review.submitted_at = datetime.now(timezone.utc)
        else:
            review = PeerReview(
                assignment_id=assignment_id,
                milestone_id=payload.milestone_id,
                reviewer_id=reviewer.id,
                reviewee_id=payload.reviewee_id,
                criteria_scores_json=payload.criteria_scores,
                total_score=payload.total_score,
                comment=payload.comment,
                submitted_at=datetime.now(timezone.utc),
            )
            self.db.add(review)

        await self.db.commit()
        await self.db.refresh(review)

        return PeerReviewResponse(
            id=review.id,
            assignment_id=review.assignment_id,
            milestone_id=review.milestone_id,
            reviewee_id=review.reviewee_id,
            criteria_scores_json=review.criteria_scores_json,
            total_score=float(review.total_score),
            comment=review.comment,
            submitted_at=review.submitted_at,
        )

    async def calculate_peer_review_factors(
        self,
        assignment_id: uuid.UUID,
        group_id: uuid.UUID,
        milestone_id: Optional[uuid.UUID] = None,
        raw_group_grade: float = 10.0,
    ) -> PeerReviewSummaryResponse:
        """Compute Fi factors and adjusted grades for each student in the group."""
        group_stmt = (
            select(StudentGroup)
            .options(selectinload(StudentGroup.members).selectinload(GroupMember.student))
            .where(StudentGroup.id == group_id, StudentGroup.assignment_id == assignment_id)
        )
        group_res = await self.db.execute(group_stmt)
        group = group_res.scalar_one_or_none()
        if not group:
            raise StudentGroupNotFoundException(str(group_id))

        members = group.members
        if not members:
            return PeerReviewSummaryResponse(
                assignment_id=assignment_id,
                group_id=group_id,
                milestone_id=milestone_id,
                summaries=[],
            )

        member_ids = [m.student_id for m in members]

        reviews_stmt = select(PeerReview).where(
            PeerReview.assignment_id == assignment_id,
            PeerReview.milestone_id == milestone_id,
            PeerReview.reviewee_id.in_(member_ids),
        )
        reviews_res = await self.db.execute(reviews_stmt)
        all_reviews = list(reviews_res.scalars().all())

        scores_by_reviewee: Dict[uuid.UUID, List[Decimal]] = {mid: [] for mid in member_ids}
        for rev in all_reviews:
            if rev.reviewee_id in scores_by_reviewee:
                scores_by_reviewee[rev.reviewee_id].append(Decimal(str(rev.total_score)))

        member_avg_scores: Dict[uuid.UUID, Decimal] = {}
        for mid in member_ids:
            scores = scores_by_reviewee[mid]
            if scores:
                avg = sum(scores) / Decimal(str(len(scores)))
            else:
                avg = Decimal("100.0")
            member_avg_scores[mid] = avg

        group_avg_score = sum(member_avg_scores.values()) / Decimal(str(len(member_ids)))

        min_f = Decimal("0.50")
        max_f = Decimal("1.20")
        raw_grade_dec = Decimal(str(raw_group_grade))

        summaries: List[PeerReviewMemberSummary] = []
        for gm in members:
            s_i = member_avg_scores[gm.student_id]
            if group_avg_score > 0:
                raw_ratio = s_i / group_avg_score
            else:
                raw_ratio = Decimal("1.0")

            f_i = max(min_f, min(max_f, raw_ratio))
            f_i_rounded = f_i.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            calc_grade = (raw_grade_dec * f_i_rounded).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            final_grade = min(raw_grade_dec, calc_grade)

            student_name = f"{gm.student.first_name} {gm.student.last_name}" if gm.student else "Student"
            student_email = gm.student.email if gm.student else ""

            summaries.append(
                PeerReviewMemberSummary(
                    student_id=gm.student_id,
                    student_name=student_name,
                    student_email=student_email,
                    average_score_received=float(s_i.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
                    group_average_score=float(group_avg_score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
                    factor_f=float(f_i_rounded),
                    raw_grade=float(raw_grade_dec),
                    adjusted_grade=float(final_grade),
                )
            )

        return PeerReviewSummaryResponse(
            assignment_id=assignment_id,
            group_id=group_id,
            milestone_id=milestone_id,
            summaries=summaries,
        )
