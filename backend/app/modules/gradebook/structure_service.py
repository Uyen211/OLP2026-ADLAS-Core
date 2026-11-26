# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""
Service implementing T2-P-M5-01 (Dynamic Gradebook Structure 100%)
and T2-P-M5-02 (TT08 Calculation Engine, Hurdle, Overview & Student Muted View).
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.assessment.public_api import AssessmentPublicService
from app.modules.course.public_api import CoursePublicService
from app.modules.examination.public_api import ExaminationPublicService
from app.modules.gradebook.calculation import (
    GroupCalcSpec,
    build_grade_distribution,
    compute_student_final_grade,
    round_tt08,
    validate_score_range,
)
from app.modules.gradebook.enums import GradeItemType, GradingStatus
from app.modules.gradebook.exceptions import (
    GradebookGroupNotEmptyException,
    GradebookLockedException,
    GradebookNotFoundException,
    GradebookSumInvalidException,
)
from app.modules.gradebook.models import GradebookColumn, GradebookGroup, GradeEntry
from app.modules.gradebook.repository import GradebookRepository
from app.modules.gradebook.schemas import (
    CellGradeDTO,
    ClassGradebookOverviewResponse,
    GradebookStructureResponse,
    GradebookStructureSaveRequest,
    GradeColumnCreateRequest,
    GradeColumnResponse,
    GradeGroupResponse,
    ManualGradeUpsertRequest,
    StudentCourseSummaryRow,
    StudentMyGradeItem,
    StudentMyGradesResponse,
)

DEFAULT_GROUPS_TEMPLATE: List[Tuple[str, int, bool, Decimal]] = [
    ("Chuyen can & Tuong tac hoc lieu", 10, False, Decimal("4.00")),
    ("Bai tap qua trinh & Do an", 30, False, Decimal("4.00")),
    ("Kiem tra giua ky", 20, False, Decimal("4.00")),
    ("Thi danh gia cuoi ky", 40, True, Decimal("4.00")),
]


class GradebookStructureService:
    """Manages dynamic grade categories, columns, sync, TT08 calculation, and student view."""

    def __init__(self, db: AsyncSession, repo: Optional[GradebookRepository] = None):
        self.db = db
        self.repo = repo or GradebookRepository(db)
        self.course_public = CoursePublicService(db)
        self.assessment_public = AssessmentPublicService(db)
        self.exam_public = ExaminationPublicService(db)

    async def _ensure_default_structure(self, course_id: uuid.UUID) -> List[GradebookGroup]:
        """Auto-initialize 10/30/20/40 syllabus template if course has no gradebook groups yet."""
        groups = await self.repo.list_groups_with_columns(course_id)
        if groups:
            return groups
        for name, weight, is_hurdle, min_score in DEFAULT_GROUPS_TEMPLATE:
            await self.repo.add_group(
                GradebookGroup(
                    id=uuid.uuid4(),
                    course_id=course_id,
                    group_name=name,
                    weight_percent=weight,
                    drop_lowest_count=0,
                    is_hurdle=is_hurdle,
                    hurdle_min_score=min_score,
                )
            )
        await self.db.flush()
        return await self.repo.list_groups_with_columns(course_id)

    async def get_structure(self, course_id: uuid.UUID) -> GradebookStructureResponse:
        """Return course gradebook structure, total weight check, and lock status."""
        groups = await self._ensure_default_structure(course_id)
        lock = await self.repo.get_course_lock(course_id)
        is_locked = bool(lock is not None and lock.is_locked)
        total_weight = sum(g.weight_percent for g in groups)
        return GradebookStructureResponse(
            course_id=course_id,
            total_weight_percent=total_weight,
            is_weight_valid=(total_weight == 100),
            is_locked=is_locked,
            locked_at=lock.locked_at if (lock and lock.is_locked) else None,
            groups=[GradeGroupResponse.model_validate(g) for g in groups],
        )

    async def save_structure(
        self,
        course_id: uuid.UUID,
        payload: GradebookStructureSaveRequest,
        actor_id: uuid.UUID,
    ) -> GradebookStructureResponse:
        """
        Save course gradebook groups enforcing:
        - Not locked (E-14)
        - Total weight == 100% (BR-GB-01 / E-11)
        """
        if await self.repo.is_course_locked(course_id):
            raise GradebookLockedException()

        total_weight = sum(g.weight_percent for g in payload.groups)
        if total_weight != 100:
            raise GradebookSumInvalidException(total_weight)

        existing = await self.repo.list_groups_with_columns(course_id)
        existing_by_id = {g.id: g for g in existing}
        incoming_ids = {g.id for g in payload.groups if g.id is not None}

        # Guard against silently deleting groups that already contain student grades
        for old_id, old_group in existing_by_id.items():
            if old_id not in incoming_ids:
                graded_count = await self.repo.count_grades_in_group(old_id)
                if graded_count > 0:
                    raise GradebookGroupNotEmptyException(graded_count)
                await self.repo.delete_group(old_group)

        for item in payload.groups:
            if item.id and item.id in existing_by_id:
                grp = existing_by_id[item.id]
                grp.group_name = item.group_name
                grp.weight_percent = item.weight_percent
                grp.drop_lowest_count = item.drop_lowest_count
                grp.is_hurdle = item.is_hurdle
                grp.hurdle_min_score = item.hurdle_min_score
            else:
                await self.repo.add_group(
                    GradebookGroup(
                        id=item.id or uuid.uuid4(),
                        course_id=course_id,
                        group_name=item.group_name,
                        weight_percent=item.weight_percent,
                        drop_lowest_count=item.drop_lowest_count,
                        is_hurdle=item.is_hurdle,
                        hurdle_min_score=item.hurdle_min_score,
                    )
                )

        await self.repo.add_audit_log(
            user_id=actor_id,
            action_type="UPDATE_GRADEBOOK_STRUCTURE",
            entity_name="gradebook_structure",
            entity_id=course_id,
            new_values={
                "groups": [
                    {
                        "name": g.group_name,
                        "weight_percent": g.weight_percent,
                        "is_hurdle": g.is_hurdle,
                        "drop_lowest_count": g.drop_lowest_count,
                    }
                    for g in payload.groups
                ]
            },
        )
        await self.db.flush()
        return await self.get_structure(course_id)

    async def delete_group(
        self,
        course_id: uuid.UUID,
        group_id: uuid.UUID,
        confirmation_text: Optional[str],
        actor_id: uuid.UUID,
    ) -> None:
        """Delete a grade group, requiring exact 'XOA' when student grades exist (E-GB-01)."""
        if await self.repo.is_course_locked(course_id):
            raise GradebookLockedException()

        group = await self.repo.get_group_by_id(group_id)
        if group is None or group.course_id != course_id:
            raise GradebookNotFoundException("nhom diem")

        graded_count = await self.repo.count_grades_in_group(group_id)
        if graded_count > 0 and (confirmation_text or "").strip() != "XOA":
            raise GradebookGroupNotEmptyException(graded_count)

        await self.repo.add_audit_log(
            user_id=actor_id,
            action_type="DELETE_GRADEBOOK_GROUP",
            entity_name="gradebook_groups",
            entity_id=group.id,
            old_values={"group_name": group.group_name, "weight_percent": group.weight_percent},
            reason=f"Confirmed delete with {graded_count} grades.",
        )
        await self.repo.delete_group(group)

    async def create_column(
        self,
        course_id: uuid.UUID,
        payload: GradeColumnCreateRequest,
        actor_id: uuid.UUID,
    ) -> GradeColumnResponse:
        """Add a sub-column inside a grade group (Subflow A-1 of M5-01)."""
        if await self.repo.is_course_locked(course_id):
            raise GradebookLockedException()

        group = await self.repo.get_group_by_id(payload.group_id)
        if group is None or group.course_id != course_id:
            raise GradebookNotFoundException("nhom diem")

        col = GradebookColumn(
            id=uuid.uuid4(),
            course_id=course_id,
            group_id=payload.group_id,
            item_type=payload.item_type.value,
            item_id=payload.item_id,
            title=payload.title,
            max_points=payload.max_points,
            is_muted=payload.is_muted,
        )
        await self.repo.add_column(col)
        await self.repo.add_audit_log(
            user_id=actor_id,
            action_type="CREATE_GRADEBOOK_COLUMN",
            entity_name="gradebook_columns",
            entity_id=col.id,
            new_values={"title": col.title, "item_type": col.item_type, "is_muted": col.is_muted},
        )
        return GradeColumnResponse.model_validate(col)

    async def sync_course_items(
        self,
        course_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> Dict[str, int]:
        """Synchronize assignments from Assessment into gradebook columns without duplicates."""
        if await self.repo.is_course_locked(course_id):
            raise GradebookLockedException()

        groups = await self._ensure_default_structure(course_id)
        # Prefer assignment/project group or fall back to first group
        target_group = next(
            (g for g in groups if "bai tap" in g.group_name.lower() or "do an" in g.group_name.lower()),
            groups[0],
        )

        assignments = await self.assessment_public.list_course_assignments_meta(course_id)
        created_columns = 0
        for item in assignments:
            existing = await self.repo.get_column_by_item(
                course_id, GradeItemType.ASSIGNMENT.value, item.id
            )
            if existing is None:
                await self.repo.add_column(
                    GradebookColumn(
                        id=uuid.uuid4(),
                        course_id=course_id,
                        group_id=target_group.id,
                        item_type=GradeItemType.ASSIGNMENT.value,
                        item_id=item.id,
                        title=item.title[:150],
                        max_points=Decimal("10.00"),
                        is_muted=True,
                    )
                )
                created_columns += 1

        return {"synced_assignments": created_columns}

    async def upsert_manual_grade(
        self,
        course_id: uuid.UUID,
        column_id: uuid.UUID,
        payload: ManualGradeUpsertRequest,
        actor_id: uuid.UUID,
    ) -> CellGradeDTO:
        """Directly enter or update a student's official score on a gradebook column."""
        if await self.repo.is_course_locked(course_id):
            raise GradebookLockedException()

        column = await self.repo.get_column_by_id(column_id)
        if column is None or column.course_id != course_id:
            raise GradebookNotFoundException("cot diem")

        score = validate_score_range(payload.official_score)
        entry = await self.repo.get_grade_entry(column_id, payload.user_id)
        old_val = None
        now = datetime.now(timezone.utc)

        if entry is None:
            entry = GradeEntry(
                id=uuid.uuid4(),
                column_id=column_id,
                user_id=payload.user_id,
                official_score=score,
                instructor_feedback=payload.instructor_feedback,
                is_overridden=False,
                grading_status=GradingStatus.INSTRUCTOR_REVIEWED.value,
                graded_by=actor_id,
                graded_at=now,
                updated_at=now,
            )
        else:
            old_val = {
                "official_score": str(entry.official_score) if entry.official_score is not None else None,
                "instructor_feedback": entry.instructor_feedback,
            }
            entry.official_score = score
            if payload.instructor_feedback is not None:
                entry.instructor_feedback = payload.instructor_feedback
            entry.grading_status = GradingStatus.INSTRUCTOR_REVIEWED.value
            entry.graded_by = actor_id
            entry.graded_at = now
            entry.updated_at = now

        await self.repo.save_grade_entry(entry)
        await self.repo.add_audit_log(
            user_id=actor_id,
            action_type="UPSERT_MANUAL_GRADE",
            entity_name="grades",
            entity_id=entry.id,
            old_values=old_val,
            new_values={"official_score": str(score), "column_id": str(column_id)},
            reason=payload.reason,
        )
        return CellGradeDTO(
            column_id=column_id,
            grade_id=entry.id,
            submission_id=entry.submission_id,
            official_score=entry.official_score,
            proposed_ai_score=entry.proposed_ai_score,
            evidence_flag=entry.evidence_flag,
            grading_status=entry.grading_status,
            is_muted=column.is_muted,
            is_overridden=entry.is_overridden,
            instructor_feedback=entry.instructor_feedback,
            voice_feedback_url=entry.voice_feedback_url,
        )

    async def get_class_overview(self, course_id: uuid.UUID) -> ClassGradebookOverviewResponse:
        """Compute full TT08 + Hurdle overview for all enrolled students in the course (T2-P-M5-02)."""
        groups = await self._ensure_default_structure(course_id)
        lock = await self.repo.get_course_lock(course_id)
        is_locked = bool(lock is not None and lock.is_locked)
        locked_by_name = await self.repo.get_user_display_name(lock.locked_by) if (lock and is_locked) else None

        all_columns: List[GradebookColumn] = [col for grp in groups for col in grp.columns]
        col_by_id = {col.id: col for col in all_columns}
        grades = await self.repo.list_grades_for_columns([c.id for c in all_columns])

        grades_by_user_col: Dict[Tuple[uuid.UUID, uuid.UUID], GradeEntry] = {
            (g.user_id, g.column_id): g for g in grades
        }

        students = await self.course_public.list_active_students(course_id)
        quiz_ids = [
            col.item_id
            for col in all_columns
            if col.item_type == GradeItemType.QUIZ.value and col.item_id is not None
        ]
        quiz_best_scores = await self.exam_public.get_best_quiz_scores_batch(
            quiz_ids=quiz_ids,
            user_ids=[s.user_id for s in students],
        )
        group_specs = [
            GroupCalcSpec(
                group_id=str(g.id),
                weight_percent=g.weight_percent,
                drop_lowest_count=int(g.drop_lowest_count or 0),
                is_hurdle=g.is_hurdle,
                hurdle_min_score=Decimal(str(g.hurdle_min_score or Decimal("4.00"))),
                column_ids=[str(c.id) for c in g.columns],
            )
            for g in groups
        ]

        rows: List[StudentCourseSummaryRow] = []
        passed_count = 0
        failed_count = 0
        hurdle_failed_count = 0
        incomplete_count = 0
        final_scores_10: List[Decimal] = []

        for stu in students:
            col_cells: Dict[str, CellGradeDTO] = {}
            scores_map: Dict[str, Optional[Decimal]] = {}

            for col_id, col in col_by_id.items():
                entry = grades_by_user_col.get((stu.user_id, col_id))
                score_val: Optional[Decimal] = None
                if entry is not None and entry.official_score is not None:
                    score_val = Decimal(str(entry.official_score))
                elif col.item_type == GradeItemType.QUIZ.value and col.item_id is not None:
                    best = quiz_best_scores.get((col.item_id, stu.user_id))
                    if best is not None:
                        score_val = Decimal(str(best))

                scores_map[str(col_id)] = score_val
                col_cells[str(col_id)] = CellGradeDTO(
                    column_id=col_id,
                    grade_id=entry.id if entry else None,
                    submission_id=entry.submission_id if entry else None,
                    official_score=score_val,
                    proposed_ai_score=entry.proposed_ai_score if entry else None,
                    evidence_flag=entry.evidence_flag if entry else None,
                    grading_status=(
                        entry.grading_status
                        if entry
                        else (GradingStatus.INSTRUCTOR_REVIEWED.value if score_val is not None else GradingStatus.UNGRADED.value)
                    ),
                    is_muted=col.is_muted,
                    is_overridden=bool(entry.is_overridden) if entry else False,
                    instructor_feedback=entry.instructor_feedback if entry else None,
                    voice_feedback_url=entry.voice_feedback_url if entry else None,
                )

            calc = compute_student_final_grade(group_specs, scores_map)
            if calc.is_provisional:
                incomplete_count += 1
            if calc.final_score_10 is not None:
                final_scores_10.append(calc.final_score_10)
            if calc.is_passed is True:
                passed_count += 1
            elif calc.is_passed is False:
                failed_count += 1
            if calc.hurdle_failed:
                hurdle_failed_count += 1

            rows.append(
                StudentCourseSummaryRow(
                    user_id=stu.user_id,
                    user_code=stu.user_code,
                    full_name=stu.full_name,
                    email=stu.email,
                    column_grades=col_cells,
                    group_averages=calc.group_averages,
                    final_score_10=calc.final_score_10,
                    letter_grade=calc.letter_grade,
                    score_4=calc.score_4,
                    is_passed=calc.is_passed,
                    hurdle_failed=calc.hurdle_failed,
                    is_provisional=calc.is_provisional,
                    missing_columns_count=calc.missing_columns_count,
                )
            )

        graded_total = passed_count + failed_count
        pass_rate = round((passed_count / graded_total) * 100.0, 1) if graded_total > 0 else 0.0
        fail_rate = round((failed_count / graded_total) * 100.0, 1) if graded_total > 0 else 0.0
        class_avg = (
            round_tt08(sum(final_scores_10, Decimal("0")) / Decimal(len(final_scores_10)))
            if final_scores_10
            else None
        )

        return ClassGradebookOverviewResponse(
            course_id=course_id,
            is_locked=is_locked,
            locked_at=lock.locked_at if (lock and is_locked) else None,
            locked_by_name=locked_by_name,
            total_students=len(students),
            passed_count=passed_count,
            failed_count=failed_count,
            hurdle_failed_count=hurdle_failed_count,
            incomplete_students_count=incomplete_count,
            class_average_10=class_avg,
            pass_rate_pct=pass_rate,
            fail_rate_pct=fail_rate,
            groups=[GradeGroupResponse.model_validate(g) for g in groups],
            students=rows,
            distribution=build_grade_distribution([r.letter_grade for r in rows]),
        )

    async def get_student_my_grades(
        self,
        course_id: uuid.UUID,
        student_id: uuid.UUID,
    ) -> StudentMyGradesResponse:
        """
        Student-only grade summary strictly enforcing BR-09 Muted Policy:
        Columns with is_muted=True NEVER leak scores, feedback, or voice URLs.
        """
        groups = await self._ensure_default_structure(course_id)
        is_locked = await self.repo.is_course_locked(course_id)
        all_columns = [col for grp in groups for col in grp.columns]
        entries = await self.repo.list_grades_for_student([c.id for c in all_columns], student_id)
        entry_by_col = {e.column_id: e for e in entries}

        items: List[StudentMyGradeItem] = []
        visible_scores: Dict[str, Optional[Decimal]] = {}

        for grp in groups:
            for col in grp.columns:
                if col.is_muted:
                    visible_scores[str(col.id)] = None
                    items.append(
                        StudentMyGradeItem(
                            column_id=col.id,
                            group_name=grp.group_name,
                            weight_percent=grp.weight_percent,
                            is_hurdle=grp.is_hurdle,
                            title=col.title,
                            item_type=col.item_type,
                            max_points=col.max_points,
                            is_muted=True,
                            official_score=None,
                            instructor_feedback=None,
                            voice_feedback_url=None,
                            status_label="Giang vien dang cham bai, diem so chua duoc cong bo",
                        )
                    )
                else:
                    entry = entry_by_col.get(col.id)
                    score = Decimal(str(entry.official_score)) if (entry and entry.official_score is not None) else None
                    visible_scores[str(col.id)] = score
                    items.append(
                        StudentMyGradeItem(
                            column_id=col.id,
                            group_name=grp.group_name,
                            weight_percent=grp.weight_percent,
                            is_hurdle=grp.is_hurdle,
                            title=col.title,
                            item_type=col.item_type,
                            max_points=col.max_points,
                            is_muted=False,
                            official_score=score,
                            instructor_feedback=entry.instructor_feedback if entry else None,
                            voice_feedback_url=entry.voice_feedback_url if entry else None,
                            status_label="Da cong bo" if score is not None else "Chua co diem",
                        )
                    )

        group_specs = [
            GroupCalcSpec(
                group_id=str(g.id),
                weight_percent=g.weight_percent,
                drop_lowest_count=int(g.drop_lowest_count or 0),
                is_hurdle=g.is_hurdle,
                hurdle_min_score=Decimal(str(g.hurdle_min_score or Decimal("4.00"))),
                column_ids=[str(c.id) for c in g.columns],
            )
            for g in groups
        ]
        calc = compute_student_final_grade(group_specs, visible_scores)

        return StudentMyGradesResponse(
            course_id=course_id,
            is_locked=is_locked,
            items=items,
            final_score_10=calc.final_score_10,
            letter_grade=calc.letter_grade,
            score_4=calc.score_4,
            is_passed=calc.is_passed,
            hurdle_failed=calc.hurdle_failed,
            is_provisional=calc.is_provisional,
        )
