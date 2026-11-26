# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""
Idempotent demo seed script for Member 3 Phase 1 (Course & Identity).
Creates 1 demo admin, 2 demo instructors, 2 demo students, 1 reusable template course with 3 LOs,
and 1 published active course. Can be run standalone or invoked from seed_data.py.
"""

import asyncio
import os
import sys
from datetime import date, timedelta

# Ensure backend package is importable when executed from repository root
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv

env_path = os.path.join(REPO_ROOT, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

db_url = os.getenv("DATABASE_URL", "")
if "@postgres:" in db_url:
    os.environ["DATABASE_URL"] = db_url.replace("@postgres:", "@localhost:")

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.modules.course.enums import (
    BloomLevel,
    ContextualRole,
    CourseStatus,
    EnrollmentStatus,
)
from app.modules.course.join_code import generate_join_code
from app.modules.course.models import Course, CourseEnrollment, LearningObjective
from app.modules.identity.repository import IdentityRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def _run_seed_course_logic(db: AsyncSession) -> dict:
    id_repo = IdentityRepository(db)

    async def ensure_user(email: str, code: str, full_name: str, password: str, role: str = "USER"):
        existing = await id_repo.get_by_email(email)
        if existing is not None:
            return existing
        return await id_repo.create_user(
            email=email,
            user_code=code,
            full_name=full_name,
            password_hash=hash_password(password),
            system_role=role,
        )

    admin = await ensure_user(
        email="admin@adlas.edu.vn",
        code="AD202601",
        full_name="Quản trị viên Hệ thống",
        password="AdminPass123!",
        role="ADMIN",
    )
    teacher = await ensure_user(
        email="teacher1@adlas.edu.vn",
        code="GV202601",
        full_name="TS. Nguyễn Minh Tuấn",
        password="TeacherPass123!",
    )
    teacher2 = await ensure_user(
        email="teacher2@adlas.edu.vn",
        code="GV202602",
        full_name="ThS. Trần Thị Lan",
        password="TeacherPass123!",
    )
    student1 = await ensure_user(
        email="student1@adlas.edu.vn",
        code="SV2026001",
        full_name="Lê Hoàng Nam",
        password="StudentPass123!",
    )
    student2 = await ensure_user(
        email="student2@adlas.edu.vn",
        code="SV2026002",
        full_name="Phạm Thị Mai",
        password="StudentPass123!",
    )

    # 1. Template course (BR-03: reusable template with 3 LOs, zero student enrollments)
    tpl_stmt = select(Course).where(
        Course.course_code == "IT4409",
        Course.section_code == "TEMPLATE",
        Course.semester == "TEMPLATE",
    )
    template = (await db.execute(tpl_stmt)).scalar_one_or_none()
    if template is None:
        template = Course(
            course_code="IT4409",
            section_code="TEMPLATE",
            name="Phát triển Ứng dụng Web Nâng cao",
            semester="TEMPLATE",
            credits=3,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 20),
            syllabus_text="<p>Đề cương mẫu môn Phát triển Ứng dụng Web Nâng cao theo chuẩn ADLAS.</p>",
            join_code=None,
            is_enrollment_open=False,
            is_template=True,
            status=CourseStatus.PUBLISHED.value,
            created_by=teacher.id,
        )
        db.add(template)
        await db.flush()

        db.add(
            CourseEnrollment(
                course_id=template.id,
                user_id=teacher.id,
                contextual_role=ContextualRole.INSTRUCTOR.value,
                enrollment_status=EnrollmentStatus.ACTIVE.value,
            )
        )

        sample_los = [
            (
                "LO-01",
                "Trình bày và phân tích kiến trúc phân tầng trong ứng dụng web hiện đại",
                "Nắm vững mô hình MVC/Clean Architecture, thiết kế Bounded Context và Dependency Injection.",
                30.0,
                BloomLevel.UNDERSTAND,
            ),
            (
                "LO-02",
                "Thiết kế và xây dựng REST API an toàn với xác thực JWT và phân quyền RBAC",
                "Hiện thực bảo mật 2 lớp, chống tấn công brute-force và quản lý phiên làm việc tập trung.",
                40.0,
                BloomLevel.APPLY,
            ),
            (
                "LO-03",
                "Đánh giá hiệu năng, bảo mật và kiểm thử tự động toàn trình hệ thống web",
                "Tối ưu truy vấn CSDL, kiểm thử tự động và đo lường tỷ lệ bao phủ mã nguồn.",
                30.0,
                BloomLevel.EVALUATE,
            ),
        ]
        for idx, (code, desc, detail, weight, bloom) in enumerate(sample_los, start=1):
            db.add(
                LearningObjective(
                    course_id=template.id,
                    code=code,
                    description=desc,
                    detail_description=detail,
                    weight_percent=weight,
                    bloom_level=bloom.value,
                    order_index=idx,
                )
            )

    # 2. Published active course section for immediate demo
    active_stmt = select(Course).where(
        Course.course_code == "IT4409",
        Course.section_code == "L01",
    )
    active_course = (await db.execute(active_stmt)).scalar_one_or_none()
    if active_course is None:
        start = date(2026, 9, 1)
        active_course = Course(
            course_code="IT4409",
            section_code="L01",
            name="Phát triển Ứng dụng Web Nâng cao",
            semester="2026.1",
            credits=3,
            start_date=start,
            end_date=start + timedelta(days=110),
            syllabus_text="<p>Lớp học phần chính thức môn Phát triển Ứng dụng Web Nâng cao - Học kỳ 2026.1.</p>",
            join_code=generate_join_code(),
            is_enrollment_open=True,
            is_template=False,
            status=CourseStatus.PUBLISHED.value,
            created_by=teacher.id,
        )
        db.add(active_course)
        await db.flush()

        db.add_all(
            [
                CourseEnrollment(
                    course_id=active_course.id,
                    user_id=teacher.id,
                    contextual_role=ContextualRole.INSTRUCTOR.value,
                    enrollment_status=EnrollmentStatus.ACTIVE.value,
                ),
                CourseEnrollment(
                    course_id=active_course.id,
                    user_id=student1.id,
                    contextual_role=ContextualRole.STUDENT.value,
                    enrollment_status=EnrollmentStatus.ACTIVE.value,
                ),
                CourseEnrollment(
                    course_id=active_course.id,
                    user_id=student2.id,
                    contextual_role=ContextualRole.STUDENT.value,
                    enrollment_status=EnrollmentStatus.ACTIVE.value,
                ),
            ]
        )
        db.add(
            LearningObjective(
                course_id=active_course.id,
                code="LO-01",
                description="Hiểu và áp dụng kiến trúc phân tầng trong phần mềm web",
                detail_description="Xây dựng ứng dụng hoàn chỉnh tích hợp API Gateway và AI Socratic Scaffolding.",
                weight_percent=100.0,
                bloom_level=BloomLevel.UNDERSTAND.value,
                order_index=1,
            )
        )

    await db.commit()
    print("Course demo seed completed successfully.")
    print(f"  Admin      : {admin.email}")
    print(f"  Instructor : {teacher.email}, {teacher2.email}")
    print(f"  Students   : {student1.email}, {student2.email}")
    print(f"  Template   : {template.course_code} ({template.id})")
    print(f"  Active L01 : {active_course.course_code} | Join Code: {active_course.join_code}")

    return {
        "admin": admin,
        "teacher": teacher,
        "teacher2": teacher2,
        "student1": student1,
        "student2": student2,
        "template_course": template,
        "active_course": active_course,
    }


async def seed_course_demo(session: AsyncSession | None = None) -> dict:
    if session is not None:
        return await _run_seed_course_logic(session)
    async with AsyncSessionLocal() as db:
        return await _run_seed_course_logic(db)


if __name__ == "__main__":
    asyncio.run(seed_course_demo())
