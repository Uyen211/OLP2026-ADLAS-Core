# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Academic integrity pledge service (T2-P-M3-03): standard terms, append-only signing, AI policy."""

from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.assessment.authoring_schemas import (
    PledgeSignRequest,
    PledgeSignResponse,
    PledgeStatusResponse,
    PledgeTerm,
)
from app.modules.assessment.authoring_service import is_system_admin
from app.modules.assessment.exceptions import (
    AssessmentNotFoundException,
    IntegrityPledgeNotSignedException,
)
from app.modules.assessment.models import IntegrityPledge
from app.modules.assessment.repository import AssessmentRepository
from app.modules.course.enums import ContextualRole
from app.modules.course.public_api import CoursePublicService

PLEDGE_VERSION = "v1.0"
MIN_AI_DESCRIPTION_CHARS = 20

PLEDGE_TERMS: List[PledgeTerm] = [
    PledgeTerm(
        code="ORIGINAL_WORK",
        text="Tôi cam đoan bài nộp là sản phẩm do chính tôi thực hiện, không sao chép hay thuê người khác làm.",
    ),
    PledgeTerm(
        code="AI_DISCLOSURE",
        text="Tôi khai báo trung thực mọi công cụ trí tuệ nhân tạo đã sử dụng theo đúng chính sách của bài tập.",
    ),
    PledgeTerm(
        code="VIVA_AND_CONSEQUENCES",
        text="Tôi đồng ý tham gia vấn đáp xác thực và chấp nhận xử lý theo quy chế nếu vi phạm liêm chính học thuật.",
    ),
]


def validate_pledge_payload(ai_policy_level: str, payload: PledgeSignRequest) -> None:
    """Apply GREEN / YELLOW / RED AI policy rules; raise E-PLG-01 (422) on violation."""
    if not payload.accepted:
        raise IntegrityPledgeNotSignedException()
    tools = [t for t in payload.tools_used if t and t.strip()]
    level = (ai_policy_level or "YELLOW").upper()
    if level == "RED":
        # Generative AI is strictly forbidden: only a 100% self-made declaration is allowed.
        if tools or payload.self_contribution_pct < 100:
            raise IntegrityPledgeNotSignedException()
    elif level == "YELLOW":
        if tools and len((payload.usage_description or "").strip()) < MIN_AI_DESCRIPTION_CHARS:
            raise IntegrityPledgeNotSignedException()
    # GREEN: AI allowed, only the acceptance checkbox is mandatory.


class PledgeService:
    def __init__(
        self,
        db: AsyncSession,
        repo: Optional[AssessmentRepository] = None,
        course_service: Optional[CoursePublicService] = None,
    ):
        self.db = db
        self.repo = repo or AssessmentRepository(db)
        self.course_service = course_service or CoursePublicService(db)

    async def _load_visible_assignment(self, assignment_id: uuid.UUID, user: Any):
        assignment = await self.repo.get_assignment(assignment_id)
        if assignment is None:
            raise AssessmentNotFoundException(str(assignment_id))
        role = await self.course_service.assert_course_role(
            course_id=assignment.course_id,
            user_id=user.id,
            allowed_roles=[ContextualRole.STUDENT, ContextualRole.INSTRUCTOR, ContextualRole.TA],
            is_admin=is_system_admin(user),
        )
        if role == ContextualRole.STUDENT and not assignment.is_published:
            raise AssessmentNotFoundException(str(assignment_id))
        return assignment

    @staticmethod
    def _status(assignment: Any, pledge: Optional[IntegrityPledge]) -> Dict[str, Any]:
        return {
            "assignment_id": assignment.id,
            "pledge_version": PLEDGE_VERSION,
            "ai_policy_level": assignment.ai_policy_level or "YELLOW",
            "terms": PLEDGE_TERMS,
            "signed": pledge is not None,
            "signed_at": pledge.signed_at if pledge else None,
            "self_contribution_pct": pledge.self_contribution_pct if pledge else None,
        }

    async def get_status(self, assignment_id: uuid.UUID, user: Any) -> PledgeStatusResponse:
        assignment = await self._load_visible_assignment(assignment_id, user)
        pledge = await self.repo.get_latest_pledge(assignment_id, user.id)
        return PledgeStatusResponse(**self._status(assignment, pledge))

    async def sign(
        self,
        assignment_id: uuid.UUID,
        user: Any,
        payload: PledgeSignRequest,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> PledgeSignResponse:
        assignment = await self._load_visible_assignment(assignment_id, user)
        level = (assignment.ai_policy_level or "YELLOW").upper()
        validate_pledge_payload(level, payload)
        pledge = IntegrityPledge(
            id=uuid.uuid4(),
            assignment_id=assignment_id,
            user_id=user.id,
            pledge_version=PLEDGE_VERSION,
            ai_policy_level=level,
            self_contribution_pct=payload.self_contribution_pct,
            ai_disclosure_snapshot={
                "tools_used": [t.strip() for t in payload.tools_used if t and t.strip()],
                "usage_description": (payload.usage_description or "").strip(),
                "terms": [term.code for term in PLEDGE_TERMS],
            },
            client_ip=(client_ip or None) and client_ip[:45],
            user_agent=(user_agent or None) and user_agent[:255],
        )
        await self.repo.add_pledge(pledge)
        await self.db.commit()
        return PledgeSignResponse(pledge_id=pledge.id, **self._status(assignment, pledge))
