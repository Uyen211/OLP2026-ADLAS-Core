# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Academic report service (T2-P-M6-03): authorization, grade calculation, export orchestration."""

from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.analytics.reporting.csv_builder import build_csv
from app.modules.analytics.reporting.data_provider import (
    CourseGradeMatrixDTO,
    DefaultGradebookExportProvider,
    GradebookExportProvider,
    LoCompetencyDTO,
)
from app.modules.analytics.reporting.excel_builder import build_excel
from app.modules.analytics.reporting.exceptions import (
    MissingGradesConfirmationRequiredException,
    ReportAccessDeniedException,
    ReportDataUnavailableException,
)
from app.modules.analytics.reporting.pdf_builder import build_pdf
from app.modules.analytics.reporting.sanitizer import build_filename, convert_grade, round_score
from app.modules.analytics.reporting.schemas import (
    WATERMARK_TEXT,
    ExportFormat,
    ExportPreviewResponse,
    ExportResult,
    GradeRowPreview,
    LoRow,
    LoRowPreview,
    ReportData,
    StudentGradeRow,
)
from app.modules.course.enums import ContextualRole
from app.modules.course.exceptions import CourseForbiddenException
from app.modules.course.public_api import CoursePublicService

ADMIN_ROLES = {"ADMIN", "SUPER_ADMIN"}
MEDIA_TYPES = {
    ExportFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ExportFormat.CSV: "text/csv; charset=utf-8",
    ExportFormat.PDF: "application/pdf",
}


def _float(value: Optional[Decimal]) -> Optional[float]:
    return None if value is None else float(value)


def _extract_lo_scores(rubric_scores: Any) -> Dict[str, Decimal]:
    """Best-effort: accept {lo_id: score} or [{lo_id, score}] structures."""
    result: Dict[str, Decimal] = {}
    try:
        if isinstance(rubric_scores, dict):
            items = [(str(k), v) for k, v in rubric_scores.items()]
        elif isinstance(rubric_scores, list):
            items = [(str(i.get("lo_id")), i.get("score")) for i in rubric_scores if isinstance(i, dict)]
        else:
            return result
        for key, value in items:
            if isinstance(value, (int, float, Decimal, str)) and not isinstance(value, bool):
                result[key] = Decimal(str(value))
    except (ArithmeticError, ValueError):
        return {}
    return result


def compute_student_rows(
    matrix: CourseGradeMatrixDTO, lo_profile: List[LoCompetencyDTO]
) -> tuple[List[str], List[StudentGradeRow]]:
    """Pure grade calculation: weighted groups on scale 10, Hurdle detection, TT08 conversion."""
    groups: Dict[uuid.UUID, Dict[str, Any]] = {}
    for column in matrix.columns:
        group = groups.setdefault(
            column.group_id,
            {
                "name": column.group_name,
                "weight": Decimal(column.weight_percent),
                "is_hurdle": column.is_hurdle,
                "hurdle_min": column.hurdle_min_score,
                "columns": [],
            },
        )
        group["columns"].append(column)
    cells = {(c.column_id, c.user_id): c for c in matrix.cells}
    lo_by_id = {p.lo.id: p for p in lo_profile}
    total_weight = sum((g["weight"] for g in groups.values()), Decimal("0"))

    rows: List[StudentGradeRow] = []
    for student in matrix.students:
        group_scores: Dict[str, Optional[Decimal]] = {}
        weighted = Decimal("0")
        missing = False
        hurdle_failed = False
        lo_sums: Dict[str, Decimal] = {}
        for group in groups.values():
            normalized: List[Decimal] = []
            for column in group["columns"]:
                cell = cells.get((column.column_id, student.user_id))
                if cell is not None and cell.rubric_scores:
                    for key, score in _extract_lo_scores(cell.rubric_scores).items():
                        lo_sums[key] = lo_sums.get(key, Decimal("0")) + score
                if cell is None or cell.official_score is None or column.max_points <= 0:
                    normalized = []
                    break
                normalized.append(cell.official_score / column.max_points * Decimal("10"))
            if not normalized:
                group_scores[group["name"]] = None
                missing = True
                continue
            score = round_score(sum(normalized, Decimal("0")) / len(normalized))
            group_scores[group["name"]] = score
            weighted += score * group["weight"]
            if group["is_hurdle"] and group["hurdle_min"] is not None and score < group["hurdle_min"]:
                hurdle_failed = True
        total: Optional[Decimal] = None
        if not missing and total_weight > 0:
            total = round_score(weighted / total_weight)
        conversion = convert_grade(total, hurdle_failed and not missing)
        lo_attainment: Dict[str, Optional[Decimal]] = {}
        for lo_id, profile in lo_by_id.items():
            raw = lo_sums.get(str(lo_id))
            if raw is None or profile.criterion_max_points <= 0:
                lo_attainment[profile.lo.code] = None
            else:
                lo_attainment[profile.lo.code] = round_score(raw / profile.criterion_max_points * 100)
        rows.append(
            StudentGradeRow(
                user_id=student.user_id,
                user_code=student.user_code or "",
                full_name=student.full_name,
                email=student.email,
                group_scores=group_scores,
                total_score=conversion.score10,
                letter_grade=conversion.letter,
                scale4=conversion.scale4,
                hurdle_failed=hurdle_failed and not missing,
                missing=missing,
                lo_attainment=lo_attainment,
            )
        )
    group_names = [g["name"] for g in groups.values()]
    return group_names, rows


class ReportingService:
    def __init__(
        self,
        db: AsyncSession,
        provider: Optional[GradebookExportProvider] = None,
        course_service: Optional[CoursePublicService] = None,
    ):
        self.db = db
        self.provider = provider or DefaultGradebookExportProvider(db)
        self.course_service = course_service or CoursePublicService(db)

    async def _authorize(self, course_id: uuid.UUID, user: Any) -> None:
        is_admin = str(getattr(user, "system_role", "") or "").upper() in ADMIN_ROLES
        try:
            await self.course_service.assert_course_role(
                course_id=course_id,
                user_id=user.id,
                allowed_roles=[ContextualRole.INSTRUCTOR],
                is_admin=is_admin,
            )
        except CourseForbiddenException as exc:
            raise ReportAccessDeniedException() from exc

    async def build_report_data(self, course_id: uuid.UUID) -> ReportData:
        course = await self.course_service.get_course_info(course_id)
        if course is None:
            raise ReportDataUnavailableException("Course not found.")
        lock = await self.provider.get_lock_status(course_id)
        matrix = await self.provider.get_grade_matrix(course_id)
        if not matrix.columns or not matrix.students:
            raise ReportDataUnavailableException()
        lo_profile = await self.provider.get_lo_competency_profile(course_id)
        group_names, rows = compute_student_rows(matrix, lo_profile)
        lo_rows = [
            LoRow(
                code=p.lo.code,
                description=p.lo.description,
                bloom_level=p.lo.bloom_level.value,
                criterion_titles=p.criterion_titles,
                max_points=p.criterion_max_points,
            )
            for p in lo_profile
        ]
        return ReportData(
            course_code=course.course_code,
            section_code=course.section_code,
            course_name=course.name,
            semester=course.semester,
            credits=course.credits,
            is_locked=lock.is_locked,
            locked_at=lock.locked_at,
            group_names=group_names,
            rows=rows,
            lo_rows=lo_rows,
        )

    @staticmethod
    def _filenames(data: ReportData) -> Dict[str, str]:
        return {
            fmt.value: build_filename(data.section_code, data.course_code, data.is_locked, fmt.value)
            for fmt in ExportFormat
        }

    async def preview(self, course_id: uuid.UUID, user: Any) -> ExportPreviewResponse:
        await self._authorize(course_id, user)
        data = await self.build_report_data(course_id)
        return ExportPreviewResponse(
            course_id=course_id,
            course_code=data.course_code,
            section_code=data.section_code,
            course_name=data.course_name,
            is_locked=data.is_locked,
            locked_at=data.locked_at,
            total_students=len(data.rows),
            missing_grade_students_count=data.missing_count,
            requires_confirmation=(not data.is_locked and data.missing_count > 0),
            watermark_text=None if data.is_locked else WATERMARK_TEXT,
            group_names=data.group_names,
            grade_rows=[
                GradeRowPreview(
                    user_code=r.user_code,
                    full_name=r.full_name,
                    group_scores={k: _float(v) for k, v in r.group_scores.items()},
                    total_score=_float(r.total_score),
                    letter_grade=r.letter_grade,
                    scale4=_float(r.scale4),
                    hurdle_failed=r.hurdle_failed,
                    missing=r.missing,
                )
                for r in data.rows
            ],
            lo_rows=[
                LoRowPreview(
                    code=lo.code,
                    description=lo.description,
                    bloom_level=lo.bloom_level,
                    criterion_titles=list(lo.criterion_titles),
                    max_points=float(lo.max_points),
                )
                for lo in data.lo_rows
            ],
            filenames=self._filenames(data),
        )

    async def export(
        self,
        course_id: uuid.UUID,
        user: Any,
        fmt: ExportFormat,
        confirm_draft: bool = False,
    ) -> ExportResult:
        await self._authorize(course_id, user)
        data = await self.build_report_data(course_id)
        if not data.is_locked and data.missing_count > 0 and not confirm_draft:
            raise MissingGradesConfirmationRequiredException(data.missing_count)
        builders = {
            ExportFormat.EXCEL: build_excel,
            ExportFormat.CSV: build_csv,
            ExportFormat.PDF: build_pdf,
        }
        return ExportResult(
            content=builders[fmt](data),
            media_type=MEDIA_TYPES[fmt],
            filename=build_filename(data.section_code, data.course_code, data.is_locked, fmt.value),
        )
