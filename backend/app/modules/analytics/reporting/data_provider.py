# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Pluggable data provider for grade report export (T2-P-M6-03).

Prefers `app.modules.gradebook.public_api` once TV1 merges it; until then a
strictly read-only fallback adapter reads `gradebook.*` tables directly.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import importlib
from typing import Any, Dict, List, Optional, Protocol, Tuple
import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.course.public_api import CoursePublicService, LODTO, StudentEnrollmentDTO

GRADEBOOK_PUBLIC_API_MODULE = "app.modules.gradebook.public_api"


@dataclass(frozen=True)
class GradebookLockDTO:
    course_id: uuid.UUID
    is_locked: bool
    locked_at: Optional[datetime] = None


@dataclass(frozen=True)
class GradeColumnDTO:
    column_id: uuid.UUID
    group_id: uuid.UUID
    group_name: str
    weight_percent: int
    is_hurdle: bool
    hurdle_min_score: Optional[Decimal]
    title: str
    max_points: Decimal


@dataclass(frozen=True)
class GradeCellDTO:
    column_id: uuid.UUID
    user_id: uuid.UUID
    official_score: Optional[Decimal]
    rubric_scores: Optional[Any] = None


@dataclass(frozen=True)
class CourseGradeMatrixDTO:
    course_id: uuid.UUID
    columns: Tuple[GradeColumnDTO, ...]
    cells: Tuple[GradeCellDTO, ...]
    students: Tuple[StudentEnrollmentDTO, ...]


@dataclass(frozen=True)
class LoCompetencyDTO:
    lo: LODTO
    criterion_titles: Tuple[str, ...]
    criterion_max_points: Decimal


class GradebookExportProvider(Protocol):
    """Contract consumed by reporting service/builders."""

    async def get_lock_status(self, course_id: uuid.UUID) -> GradebookLockDTO: ...

    async def get_grade_matrix(self, course_id: uuid.UUID) -> CourseGradeMatrixDTO: ...

    async def get_lo_competency_profile(self, course_id: uuid.UUID) -> List[LoCompetencyDTO]: ...


class FallbackGradebookReadAdapter:
    """Read-only (SELECT only) adapter over gradebook.*, course and assessment data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_lock_status(self, course_id: uuid.UUID) -> GradebookLockDTO:
        row = (
            await self.db.execute(
                text(
                    "SELECT is_locked, locked_at FROM gradebook.course_gradebook_locks "
                    "WHERE course_id = :course_id"
                ),
                {"course_id": course_id},
            )
        ).first()
        if row is None:
            return GradebookLockDTO(course_id=course_id, is_locked=False)
        return GradebookLockDTO(course_id=course_id, is_locked=bool(row[0]), locked_at=row[1])

    async def get_grade_matrix(self, course_id: uuid.UUID) -> CourseGradeMatrixDTO:
        col_rows = (
            await self.db.execute(
                text(
                    "SELECT c.id, g.id, g.group_name, g.weight_percent, g.is_hurdle, "
                    "g.hurdle_min_score, c.title, c.max_points "
                    "FROM gradebook.gradebook_columns c "
                    "JOIN gradebook.gradebook_groups g ON g.id = c.group_id "
                    "WHERE c.course_id = :course_id ORDER BY g.group_name, c.title"
                ),
                {"course_id": course_id},
            )
        ).all()
        columns = tuple(
            GradeColumnDTO(
                column_id=r[0],
                group_id=r[1],
                group_name=r[2],
                weight_percent=int(r[3]),
                is_hurdle=bool(r[4]),
                hurdle_min_score=None if r[5] is None else Decimal(str(r[5])),
                title=r[6],
                max_points=Decimal(str(r[7])),
            )
            for r in col_rows
        )
        cell_rows = (
            await self.db.execute(
                text(
                    "SELECT gr.column_id, gr.user_id, gr.official_score, gr.rubric_scores "
                    "FROM gradebook.grades gr "
                    "JOIN gradebook.gradebook_columns c ON c.id = gr.column_id "
                    "WHERE c.course_id = :course_id"
                ),
                {"course_id": course_id},
            )
        ).all()
        cells = tuple(
            GradeCellDTO(
                column_id=r[0],
                user_id=r[1],
                official_score=None if r[2] is None else Decimal(str(r[2])),
                rubric_scores=r[3],
            )
            for r in cell_rows
        )
        students = await CoursePublicService(self.db).list_active_students(course_id)
        return CourseGradeMatrixDTO(
            course_id=course_id,
            columns=columns,
            cells=cells,
            students=tuple(students),
        )

    async def get_lo_competency_profile(self, course_id: uuid.UUID) -> List[LoCompetencyDTO]:
        los = await CoursePublicService(self.db).get_learning_objectives(course_id)
        rows = (
            await self.db.execute(
                text(
                    "SELECT rc.lo_id, rc.title, rc.max_points "
                    "FROM assessment.rubric_criteria rc "
                    "JOIN assessment.rubrics r ON r.id = rc.rubric_id "
                    "JOIN assessment.assignments a ON a.id = r.assignment_id "
                    "WHERE a.course_id = :course_id AND rc.lo_id IS NOT NULL"
                ),
                {"course_id": course_id},
            )
        ).all()
        titles: Dict[uuid.UUID, List[str]] = {}
        points: Dict[uuid.UUID, Decimal] = {}
        for lo_id, title, max_points in rows:
            titles.setdefault(lo_id, []).append(title)
            points[lo_id] = points.get(lo_id, Decimal("0")) + Decimal(str(max_points))
        return [
            LoCompetencyDTO(
                lo=lo,
                criterion_titles=tuple(titles.get(lo.id, [])),
                criterion_max_points=points.get(lo.id, Decimal("0")),
            )
            for lo in los
        ]


class DefaultGradebookExportProvider:
    """Delegates to gradebook.public_api when available, otherwise to the read-only fallback."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._fallback = FallbackGradebookReadAdapter(db)
        self._gradebook_service = self._load_gradebook_service(db)

    @staticmethod
    def _load_gradebook_service(db: AsyncSession) -> Optional[Any]:
        try:
            module = importlib.import_module(GRADEBOOK_PUBLIC_API_MODULE)
        except ImportError:
            return None
        factory = getattr(module, "GradebookPublicService", None)
        return factory(db) if factory is not None else None

    @property
    def uses_gradebook_service(self) -> bool:
        return self._gradebook_service is not None

    async def _delegate(self, name: str, course_id: uuid.UUID) -> Optional[Any]:
        method = getattr(self._gradebook_service, name, None)
        if method is None:
            return None
        return await method(course_id)

    async def get_lock_status(self, course_id: uuid.UUID) -> GradebookLockDTO:
        if self._gradebook_service is not None:
            result = await self._delegate("get_lock_status", course_id)
            if isinstance(result, GradebookLockDTO):
                return result
        return await self._fallback.get_lock_status(course_id)

    async def get_grade_matrix(self, course_id: uuid.UUID) -> CourseGradeMatrixDTO:
        if self._gradebook_service is not None:
            result = await self._delegate("get_grade_matrix", course_id)
            if isinstance(result, CourseGradeMatrixDTO):
                return result
        return await self._fallback.get_grade_matrix(course_id)

    async def get_lo_competency_profile(self, course_id: uuid.UUID) -> List[LoCompetencyDTO]:
        return await self._fallback.get_lo_competency_profile(course_id)
