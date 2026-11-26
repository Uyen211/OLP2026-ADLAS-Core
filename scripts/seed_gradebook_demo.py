# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT
# ruff: noqa: E402

"""Idempotent seed script for Module 5 (Gradebook & SpeedGrader) demo data."""

import asyncio
from decimal import Decimal
import os
import sys
import uuid

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.modules.assessment.models import (
    Assignment,
    AssignmentSubmission,
    Rubric,
    RubricCriteria,
)
from app.modules.course.models import Course, LearningObjective
from app.modules.gradebook.enums import EvidenceFlag, GradeItemType, GradingStatus
from app.modules.gradebook.models import (
    Grade,
    GradebookColumn,
    GradebookGroup,
)
from app.modules.system.models import User

ASSIGNMENT_ID = uuid.UUID("a1111111-1111-1111-1111-111111111111")
SUBMISSION_ID = uuid.UUID("b2222222-2222-2222-2222-222222222222")
RUBRIC_ID = uuid.UUID("c3333333-3333-3333-3333-333333333333")


async def seed_gradebook_demo() -> None:
    async with AsyncSessionLocal() as db:
        course = (
            await db.execute(
                select(Course).where(Course.course_code == "IT4409", Course.section_code == "L01")
            )
        ).scalar_one_or_none()
        if not course:
            course = (await db.execute(select(Course).limit(1))).scalar_one_or_none()
        if not course:
            print("No course found. Run seed_course_demo.py first.")
            return

        los = list(
            (
                await db.execute(
                    select(LearningObjective)
                    .where(LearningObjective.course_id == course.id)
                    .order_by(LearningObjective.order_index.asc())
                )
            )
            .scalars()
            .all()
        )

        # 1. Seed 4 Gradebook Groups totaling 100% (Final Exam has Hurdle 4.0)
        group_specs = [
            ("Chuyên cần & Thái độ", 10, 0, False, Decimal("4.00")),
            ("Bài tập lớn & Dự án", 30, 0, False, Decimal("4.00")),
            ("Kiểm tra giữa kỳ", 20, 0, False, Decimal("4.00")),
            ("Thi kết thúc học phần", 40, 0, True, Decimal("4.00")),
        ]
        groups_by_name: dict[str, GradebookGroup] = {}
        existing_groups = list(
            (
                await db.execute(
                    select(GradebookGroup).where(GradebookGroup.course_id == course.id)
                )
            )
            .scalars()
            .all()
        )
        for g in existing_groups:
            groups_by_name[g.group_name] = g

        if not existing_groups:
            for name, weight, drop_cnt, is_hurdle, hurdle_min in group_specs:
                grp = GradebookGroup(
                    course_id=course.id,
                    group_name=name,
                    weight_percent=weight,
                    drop_lowest_count=drop_cnt,
                    is_hurdle=is_hurdle,
                    hurdle_min_score=hurdle_min,
                )
                db.add(grp)
                groups_by_name[name] = grp
            await db.flush()
            print(f"Created 4 Gradebook Groups (100%) for course {course.course_code}.")
        else:
            print(f"Gradebook Groups already exist ({len(existing_groups)} groups).")

        # 2. Seed Rubric + 4 Criteria (total 10.0 pts) linked to Assignment
        assignment = (
            await db.execute(select(Assignment).where(Assignment.id == ASSIGNMENT_ID))
        ).scalar_one_or_none()
        rubric = None
        if assignment:
            rubric = (
                await db.execute(select(Rubric).where(Rubric.assignment_id == assignment.id))
            ).scalar_one_or_none()
        if assignment and not rubric:
            rubric = Rubric(
                id=RUBRIC_ID,
                assignment_id=assignment.id,
                title="Rubric Chấm Bài tập lớn NLP & AI Chatbot (Thang 10)",
                total_points=Decimal("10.0"),
            )
            db.add(rubric)
            await db.flush()

            criteria_specs = [
                (
                    "Kiến trúc Pipeline & Xử lý dữ liệu",
                    "Thiết kế pipeline trích xuất văn bản sạch, có xử lý OOV/chunking hợp lý.",
                    Decimal("3.0"),
                    [
                        {"level": "Xuất sắc", "points": 3.0, "description": "Pipeline chuẩn, tối ưu bộ nhớ và xử lý ngoại lệ đầy đủ."},
                        {"level": "Tốt", "points": 2.25, "description": "Pipeline hoạt động đúng yêu cầu, còn vài điểm nhỏ."},
                        {"level": "Đạt", "points": 1.5, "description": "Chạy được luồng cơ bản nhưng thiếu xử lý biên."},
                        {"level": "Chưa đạt", "points": 0.5, "description": "Không hoàn thiện hoặc lỗi nghiêm trọng."},
                    ],
                ),
                (
                    "Thuật toán mô hình & Thực nghiệm",
                    "Cài đặt chính xác PhoBERT/BiLSTM-CRF và đánh giá Active Learning định lượng.",
                    Decimal("3.0"),
                    [
                        {"level": "Xuất sắc", "points": 3.0, "description": "Có so sánh định lượng rõ ràng, giải thích sắc nét."},
                        {"level": "Tốt", "points": 2.25, "description": "Đạt mục tiêu mô hình, báo cáo kết quả đầy đủ."},
                        {"level": "Đạt", "points": 1.5, "description": "Huấn luyện được mô hình nhưng thiếu phân tích."},
                        {"level": "Chưa đạt", "points": 0.5, "description": "Thiếu kết quả thực nghiệm đáng tin cậy."},
                    ],
                ),
                (
                    "Kiểm chứng Vấn đáp Viva & Hiểu biết gốc",
                    "Trả lời chính xác câu hỏi phản biện Viva, nhất quán với mã nguồn đã nộp.",
                    Decimal("2.0"),
                    [
                        {"level": "Xuất sắc", "points": 2.0, "description": "Bảo vệ thuyết phục, làm chủ 100% kiến thức."},
                        {"level": "Tốt", "points": 1.5, "description": "Trả lời đúng trọng tâm hầu hết câu hỏi."},
                        {"level": "Đạt", "points": 1.0, "description": "Trả lời được ý chính nhưng còn lúng túng."},
                        {"level": "Chưa đạt", "points": 0.0, "description": "Mâu thuẫn nghiêm trọng hoặc không nắm được bài làm."},
                    ],
                ),
                (
                    "Chất lượng mã nguồn, Kiểm thử & Khai báo AI",
                    "Mã nguồn sạch, có kiểm thử tự động và khai báo minh bạch tỷ lệ sử dụng AI.",
                    Decimal("2.0"),
                    [
                        {"level": "Xuất sắc", "points": 2.0, "description": "Code sạch, test phủ cao, khai báo AI trung thực."},
                        {"level": "Tốt", "points": 1.5, "description": "Cấu trúc tốt, có test cơ bản và khai báo đầy đủ."},
                        {"level": "Đạt", "points": 1.0, "description": "Thiếu unit test hoặc tài liệu chưa rõ."},
                        {"level": "Chưa đạt", "points": 0.0, "description": "Không đạt chuẩn kỹ thuật hoặc khai báo thiếu trung thực."},
                    ],
                ),
            ]
            for idx, (title, desc, max_pts, levels) in enumerate(criteria_specs):
                lo_id = los[idx].id if idx < len(los) else (los[0].id if los else None)
                db.add(
                    RubricCriteria(
                        rubric_id=rubric.id,
                        lo_id=lo_id,
                        competency_code=f"C{idx + 1}",
                        title=title,
                        description=desc,
                        max_points=max_pts,
                        rating_levels=levels,
                        order_index=idx + 1,
                    )
                )
            await db.flush()
            print(f"Created Rubric {RUBRIC_ID} with 4 criteria (10.0 pts).")

        # 3. Seed Gradebook Columns
        existing_cols = list(
            (
                await db.execute(
                    select(GradebookColumn).where(GradebookColumn.course_id == course.id)
                )
            )
            .scalars()
            .all()
        )
        col_by_title = {c.title: c for c in existing_cols}

        att_grp = groups_by_name.get("Chuyên cần & Thái độ") or next(iter(groups_by_name.values()))
        btl_grp = groups_by_name.get("Bài tập lớn & Dự án") or att_grp
        mid_grp = groups_by_name.get("Kiểm tra giữa kỳ") or att_grp
        fin_grp = groups_by_name.get("Thi kết thúc học phần") or att_grp

        col_specs = [
            (att_grp.id, GradeItemType.PROGRESS_ATTENDANCE.value, None, "Điểm Chuyên cần", False),
            (
                btl_grp.id,
                GradeItemType.ASSIGNMENT.value,
                ASSIGNMENT_ID if assignment else None,
                assignment.title if assignment else "Bài tập lớn NLP & AI Chatbot",
                True,
            ),
            (mid_grp.id, GradeItemType.QUIZ.value, None, "Kiểm tra Giữa kỳ", False),
            (fin_grp.id, GradeItemType.MANUAL.value, None, "Thi Cuối kỳ (Điểm liệt 4.0)", False),
        ]
        cols_map: dict[str, GradebookColumn] = {}
        for grp_id, item_type, item_id, title, is_muted in col_specs:
            existing = col_by_title.get(title)
            if not existing and item_id is not None:
                existing = next((c for c in existing_cols if c.item_id == item_id), None)
            if not existing:
                existing = GradebookColumn(
                    course_id=course.id,
                    group_id=grp_id,
                    item_type=item_type,
                    item_id=item_id,
                    title=title,
                    max_points=Decimal("10.00"),
                    is_muted=is_muted,
                )
                db.add(existing)
                await db.flush()
            cols_map[item_type] = existing

        # 4. Seed sample grades for student1 (AI_PROPOSED on Assignment + other scores)
        student1 = (
            await db.execute(select(User).where(User.email == "student1@adlas.edu.vn"))
        ).scalar_one_or_none()
        sub = (
            await db.execute(
                select(AssignmentSubmission).where(AssignmentSubmission.id == SUBMISSION_ID)
            )
        ).scalar_one_or_none()

        if student1:
            sample_scores = [
                (cols_map[GradeItemType.PROGRESS_ATTENDANCE.value], Decimal("9.50"), GradingStatus.INSTRUCTOR_REVIEWED.value, None),
                (cols_map[GradeItemType.QUIZ.value], Decimal("8.00"), GradingStatus.INSTRUCTOR_REVIEWED.value, None),
                (cols_map[GradeItemType.MANUAL.value], Decimal("8.50"), GradingStatus.INSTRUCTOR_REVIEWED.value, None),
            ]
            for col, score_val, status_val, sub_id in sample_scores:
                exists = (
                    await db.execute(
                        select(Grade).where(
                            Grade.column_id == col.id,
                            Grade.user_id == student1.id,
                        )
                    )
                ).scalar_one_or_none()
                if not exists:
                    db.add(
                        Grade(
                            column_id=col.id,
                            user_id=student1.id,
                            submission_id=sub_id,
                            official_score=score_val,
                            grading_status=status_val,
                        )
                    )

            btl_col = cols_map[GradeItemType.ASSIGNMENT.value]
            btl_grade = (
                await db.execute(
                    select(Grade).where(
                        Grade.column_id == btl_col.id,
                        Grade.user_id == student1.id,
                    )
                )
            ).scalar_one_or_none()
            if not btl_grade and sub:
                db.add(
                    Grade(
                        column_id=btl_col.id,
                        user_id=student1.id,
                        submission_id=sub.id,
                        proposed_ai_score=Decimal("8.25"),
                        evidence_flag=EvidenceFlag.SUFFICIENT.value,
                        grading_status=GradingStatus.AI_PROPOSED.value,
                        instructor_feedback=None,
                    )
                )

        await db.commit()
        print("Seeded Gradebook & SpeedGrader demo data successfully.")


if __name__ == "__main__":
    asyncio.run(seed_gradebook_demo())
