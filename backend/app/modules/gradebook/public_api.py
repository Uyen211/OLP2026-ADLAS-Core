# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Public in-process service contract (IGradebookService) exposed for Learning, Examination, and Analytics."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.gradebook.calculation import validate_score_range
from app.modules.gradebook.enums import GradingStatus
from app.modules.gradebook.exceptions import GradebookLockedException, GradebookNotFoundException
from app.modules.gradebook.models import GradeEntry
from app.modules.gradebook.repository import GradebookRepository
from app.modules.gradebook.schemas import ClassGradebookOverviewResponse
from app.modules.gradebook.structure_service import GradebookStructureService


@dataclass(frozen=True)
class LOCompetencyScoreDTO:
    """Aggregated rubric score mapped to a specific Learning Objective (for Analytics/Export)."""

    lo_id: str
    average_score: Decimal
    criteria_count: int


class GradebookPublicService:
    """Cross-module contract matching IGradebookService in 06-gradebook-module.md."""

    def __init__(self, db: AsyncSession, repo: Optional[GradebookRepository] = None):
        self.db = db
        self.repo = repo or GradebookRepository(db)
        self.structure_service = GradebookStructureService(db, self.repo)

    async def is_course_gradebook_locked(self, course_id: uuid.UUID) -> bool:
        """Check whether a course gradebook has been permanently sealed (E-14 guard)."""
        return await self.repo.is_course_locked(course_id)

    async def get_course_official_grades(self, course_id: uuid.UUID) -> ClassGradebookOverviewResponse:
        """Return full TT08 rounded official grades for Analytics / Excel 2-sheet export."""
        return await self.structure_service.get_class_overview(course_id)

    async def get_student_competency_scores(
        self,
        student_id: uuid.UUID,
        course_id: uuid.UUID,
    ) -> List[LOCompetencyScoreDTO]:
        """Aggregate student rubric scores grouped by Learning Objective (lo_id)."""
        columns = await self.repo.list_columns_by_course(course_id)
        entries = await self.repo.list_grades_for_student([c.id for c in columns], student_id)
        totals: Dict[str, List[Decimal]] = {}
        for entry in entries:
            if not isinstance(entry.rubric_scores, dict):
                continue
            for item in entry.rubric_scores.values():
                if isinstance(item, dict) and item.get("lo_id") and item.get("points") is not None:
                    lo_key = str(item["lo_id"])
                    totals.setdefault(lo_key, []).append(Decimal(str(item["points"])))

        result: List[LOCompetencyScoreDTO] = []
        for lo_id, pts in totals.items():
            avg = (sum(pts, Decimal("0")) / Decimal(len(pts))).quantize(Decimal("0.01"))
            result.append(LOCompetencyScoreDTO(lo_id=lo_id, average_score=avg, criteria_count=len(pts)))
        return result

    async def record_auto_grade(
        self,
        column_id: uuid.UUID,
        student_id: uuid.UUID,
        raw_score: Decimal,
        origin: str = "AUTO_SYSTEM",
    ) -> None:
        """Receive automated score from Examination (Quiz) or Learning (Attendance) modules."""
        col = await self.repo.get_column_by_id(column_id)
        if col is None:
            raise GradebookNotFoundException("cot diem")
        if await self.repo.is_course_locked(col.course_id):
            raise GradebookLockedException()

        score = validate_score_range(raw_score)
        entry = await self.repo.get_grade_entry(column_id, student_id)
        now = datetime.now(timezone.utc)
        if entry is None:
            entry = GradeEntry(
                id=uuid.uuid4(),
                column_id=column_id,
                user_id=student_id,
                official_score=score,
                grading_status=GradingStatus.INSTRUCTOR_REVIEWED.value,
                graded_at=now,
                updated_at=now,
            )
        else:
            entry.official_score = score
            entry.grading_status = GradingStatus.INSTRUCTOR_REVIEWED.value
            entry.graded_at = now
            entry.updated_at = now

        await self.repo.save_grade_entry(entry)
        await self.repo.add_audit_log(
            user_id=None,
            action_type=f"AUTO_GRADE_{origin.upper()}",
            entity_name="grades",
            entity_id=entry.id,
            new_values={"official_score": str(score), "origin": origin},
        )
