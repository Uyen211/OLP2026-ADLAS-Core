# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""
Idempotent demo seed script for Member 3 Phase 1 (Course & Identity).
Creates 1 demo instructor, 2 demo students, 1 reusable template course with 3 LOs,
and 1 published active course without touching TV1's seed_data.py.
"""

import asyncio
from datetime import date, timedelta
import os
import sys

# Ensure backend package is importable when executed from repository root
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import select  # noqa: E402
from app.core.database import AsyncSessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.modules.course.enums import BloomLevel, ContextualRole, CourseStatus, EnrollmentStatus  # noqa: E402
from app.modules.course.join_code import generate_join_code  # noqa: E402
from app.modules.course.models import Course, CourseEnrollment, LearningObjective  # noqa: E402
from app.modules.identity.repository import IdentityRepository  # noqa: E402


async def seed_course_demo() -> None:
    async with AsyncSessionLocal() as db:
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

        teacher = await ensure_user(
            email="teacher1@adlas.edu.vn",
            code="GV202601",
            full_name="TS. Nguyen Minh Tuan",
            password="TeacherPass123!",
        )
        student1 = await ensure_user(
            email="student1@adlas.edu.vn",
            code="SV2026001",
            full_name="Le Hoang Nam",
            password="StudentPass123!",
        )
        student2 = await ensure_user(
            email="student2@adlas.edu.vn",
            code="SV2026002",
            full_name="Pham Thi Mai",
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
                name="Phat trien Ung dung Web Nang cao",
                semester="TEMPLATE",
                credits=3,
                start_date=date(2026, 9, 1),
                end_date=date(2026, 12, 20),
                syllabus_text="<p>De cuong mau mon Phat trien Ung dung Web Nang cao theo chuan ADLAS.</p>",
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
                ("LO-01", "Trinh bay va phan tich kien truc phan tang trong ung dung web hien dai", BloomLevel.UNDERSTAND),
                ("LO-02", "Thiet ke va xay dung REST API an toan voi xac thuc JWT va phan quyen RBAC", BloomLevel.APPLY),
                ("LO-03", "Danh gia hieu nang, bao mat va kiem thu tu dong toan trinh he thong web", BloomLevel.EVALUATE),
            ]
            for idx, (code, desc, bloom) in enumerate(sample_los, start=1):
                db.add(
                    LearningObjective(
                        course_id=template.id,
                        code=code,
                        description=desc,
                        bloom_level=bloom.value,
                        order_index=idx,
                    )
                )

        # 2. Published active course section for immediate demo
        active_stmt = select(Course).where(
            Course.course_code == "IT4409",
            Course.section_code == "L01",
            Course.semester == "HK1-2026-2027",
        )
        active_course = (await db.execute(active_stmt)).scalar_one_or_none()
        if active_course is None:
            start = date.today()
            active_course = Course(
                course_code="IT4409",
                section_code="L01",
                name="Phat trien Ung dung Web Nang cao",
                semester="HK1-2026-2027",
                credits=3,
                start_date=start,
                end_date=start + timedelta(days=90),
                syllabus_text="<p>Lop hoc phan chinh thuc hoc ky 1 nam hoc 2026-2027.</p>",
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
                    description="Hieu va ap dung kien truc phan tang trong phan mem web",
                    bloom_level=BloomLevel.UNDERSTAND.value,
                    order_index=1,
                )
            )

        await db.commit()
        print("Course demo seed completed successfully.")
        print(f"  Instructor : {teacher.email}")
        print(f"  Students   : {student1.email}, {student2.email}")
        print(f"  Template   : {template.course_code} ({template.id})")
        print(f"  Active L01 : {active_course.course_code} | Join Code: {active_course.join_code}")


if __name__ == "__main__":
    asyncio.run(seed_course_demo())
