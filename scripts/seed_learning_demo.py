# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Seed script to populate sample Learning Modules and Materials for Phase 1 demo."""

import asyncio
from datetime import datetime, timedelta, timezone
import os
import sys
import uuid

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.modules.course.models import Course, LearningObjective
from app.modules.learning.enums import MaterialType
from app.modules.learning.models import LearningMaterial, LearningModule

# Fixed UUIDs for idempotency
MOD_1_ID = uuid.UUID("11111111-aaaa-1111-aaaa-111111111111")
MOD_2_ID = uuid.UUID("22222222-bbbb-2222-bbbb-222222222222")
MOD_3_ID = uuid.UUID("33333333-cccc-3333-cccc-333333333333")
MOD_4_ID = uuid.UUID("44444444-dddd-4444-dddd-444444444444")

MAT_1_ID = uuid.UUID("11111111-1001-1111-1001-111111111111")
MAT_2_ID = uuid.UUID("11111111-1002-1111-1002-111111111111")
MAT_3_ID = uuid.UUID("22222222-2001-2222-2001-222222222222")
MAT_4_ID = uuid.UUID("22222222-2002-2222-2002-222222222222")
MAT_5_ID = uuid.UUID("33333333-3001-3333-3001-333333333333")
MAT_6_ID = uuid.UUID("44444444-4001-4444-4001-444444444444")


def _ensure_demo_files():
    """Create lightweight physical demo files on disk for downloads."""
    base_upload_dir = os.getenv("UPLOAD_DIR")
    if not base_upload_dir:
        if os.path.exists("/app"):
            base_upload_dir = "/app/uploads"
        else:
            base_upload_dir = os.path.join(os.path.expanduser("~"), ".adlas", "uploads")
    materials_dir = os.path.join(base_upload_dir, "materials")
    os.makedirs(materials_dir, exist_ok=True)

    demo_files = {
        "demo_chuong1_slide.pptx": b"ADLAS Demo Slide Deck Content - Chapter 1",
        "demo_chuong1_rag_guide.pdf": b"%PDF-1.4 Mock PDF Document - RAG Overview for ADLAS",
        "demo_chuong2_pgvector_handbook.md": b"# Huong dan truy van Cosine Similarity tren pgvector HNSW\n\nNoi dung demo...",
        "demo_chuong3_socratic.pptx": b"ADLAS Socratic Scaffolding Presentation",
        "demo_chuong4_lab.docx": b"ADLAS Lab Instructions Draft",
    }
    paths = {}
    for fname, data in demo_files.items():
        fpath = os.path.join(materials_dir, fname)
        if not os.path.exists(fpath):
            with open(fpath, "wb") as f:
                f.write(data)
        paths[fname] = fpath
    return paths


async def seed_learning_demo() -> None:
    file_paths = _ensure_demo_files()

    async with AsyncSessionLocal() as db:
        # 1. Resolve Target Course IT4409 (L01)
        course_stmt = select(Course).where(Course.course_code == "IT4409", Course.section_code == "L01")
        course = (await db.execute(course_stmt)).scalar_one_or_none()
        if not course:
            course = (await db.execute(select(Course).limit(1))).scalar_one_or_none()
        if not course:
            print("[SEED-LEARNING] No course found in database! Please run seed_course_demo.py first.")
            return

        print(f"[SEED-LEARNING] Seeding learning modules into course: {course.course_code} - {course.name} ({course.id})")

        # Resolve Course LOs
        lo_stmt = select(LearningObjective).where(LearningObjective.course_id == course.id)
        los = list((await db.execute(lo_stmt)).scalars().all())
        lo1 = next((lo for lo in los if lo.code == "LO1"), los[0] if los else None)
        lo2 = next((lo for lo in los if lo.code == "LO2"), los[1] if len(los) > 1 else None)

        now = datetime.now(timezone.utc)

        # 2. Upsert Module 1: Published & Unlocked
        m1 = (await db.execute(select(LearningModule).where(LearningModule.id == MOD_1_ID))).scalar_one_or_none()
        if not m1:
            m1 = LearningModule(
                id=MOD_1_ID,
                course_id=course.id,
                title="Chương 1: Tổng quan Kiến trúc Hệ thống & RAG Tri thức",
                order_index=1,
                unlock_at=None,
                prerequisite_module_id=None,
                is_published=True,
            )
            db.add(m1)
            await db.flush()
            print("  + Created Module 1 (Published & Unlocked)")

        # 3. Upsert Module 2: Published & Locked by Prerequisite (Module 1)
        m2 = (await db.execute(select(LearningModule).where(LearningModule.id == MOD_2_ID))).scalar_one_or_none()
        if not m2:
            m2 = LearningModule(
                id=MOD_2_ID,
                course_id=course.id,
                title="Chương 2: Kỹ thuật Chunking & Vector Database pgvector",
                order_index=2,
                unlock_at=None,
                prerequisite_module_id=MOD_1_ID,
                is_published=True,
            )
            db.add(m2)
            await db.flush()
            print("  + Created Module 2 (Published & Locked by Prerequisite Module 1)")

        # 4. Upsert Module 3: Published & Locked by Unlock Date Schedule (+7 days)
        m3 = (await db.execute(select(LearningModule).where(LearningModule.id == MOD_3_ID))).scalar_one_or_none()
        if not m3:
            m3 = LearningModule(
                id=MOD_3_ID,
                course_id=course.id,
                title="Chương 3: Động cơ Đối thoại Socratic AI (Socratic Dialog Engine)",
                order_index=3,
                unlock_at=now + timedelta(days=7),
                prerequisite_module_id=None,
                is_published=True,
            )
            db.add(m3)
            await db.flush()
            print("  + Created Module 3 (Published & Locked by Schedule)")

        # 5. Upsert Module 4: Draft (Unpublished, Instructor-only)
        m4 = (await db.execute(select(LearningModule).where(LearningModule.id == MOD_4_ID))).scalar_one_or_none()
        if not m4:
            m4 = LearningModule(
                id=MOD_4_ID,
                course_id=course.id,
                title="Chương 4: Đánh giá Năng lực Đa chiều (Bản nháp)",
                order_index=4,
                unlock_at=None,
                prerequisite_module_id=None,
                is_published=False,
            )
            db.add(m4)
            await db.flush()
            print("  + Created Module 4 (Draft / Unpublished)")

        # 6. Upsert Learning Materials
        materials_data = [
            (
                MAT_1_ID,
                MOD_1_ID,
                lo1.id if lo1 else None,
                "Slide Bài giảng: Kiến trúc DX-OS Open-Core và 8 Bounded Contexts",
                MaterialType.SLIDE.value,
                file_paths["demo_chuong1_slide.pptx"],
                True,
                45,
                True,
            ),
            (
                MAT_2_ID,
                MOD_1_ID,
                lo1.id if lo1 else None,
                "Tài liệu đọc: Hướng dẫn RAG và Vector Database trong Giáo dục Đại học",
                MaterialType.PDF.value,
                file_paths["demo_chuong1_rag_guide.pdf"],
                True,
                30,
                True,
            ),
            (
                MAT_3_ID,
                MOD_2_ID,
                lo2.id if lo2 else None,
                "Video: Trực quan hóa HNSW Indexing với m=16 và ef_construction=64",
                MaterialType.VIDEO.value,
                "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
                True,
                25,
                True,
            ),
            (
                MAT_4_ID,
                MOD_2_ID,
                lo2.id if lo2 else None,
                "Cẩm nang: Tối ưu truy vấn Cosine Similarity trên PostgreSQL 16",
                MaterialType.DOCUMENT.value,
                file_paths["demo_chuong2_pgvector_handbook.md"],
                False,
                20,
                True,
            ),
            (
                MAT_5_ID,
                MOD_3_ID,
                None,
                "Slide: Phương pháp Socratic Scaffolding và Hướng dẫn Tư duy Từng bước",
                MaterialType.SLIDE.value,
                file_paths["demo_chuong3_socratic.pptx"],
                True,
                40,
                True,
            ),
            (
                MAT_6_ID,
                MOD_4_ID,
                None,
                "Đề cương bài tập thực hành phòng Lab (Nội dung nháp)",
                MaterialType.DOCUMENT.value,
                file_paths["demo_chuong4_lab.docx"],
                False,
                15,
                False,
            ),
        ]

        for mat_id, mod_id, lo_id, title, mat_type, f_url, is_mand, duration, is_pub in materials_data:
            existing = (await db.execute(select(LearningMaterial).where(LearningMaterial.id == mat_id))).scalar_one_or_none()
            if not existing:
                db.add(
                    LearningMaterial(
                        id=mat_id,
                        module_id=mod_id,
                        lo_id=lo_id,
                        title=title,
                        material_type=mat_type,
                        file_url=f_url,
                        is_mandatory=is_mand,
                        est_duration_minutes=duration,
                        is_published=is_pub,
                    )
                )
                print(f"    - Added material: [{mat_type}] {title}")

        await db.commit()
        print("[SEED-LEARNING] Successfully seeded Phase 1 Learning modules & materials demo!")


if __name__ == "__main__":
    asyncio.run(seed_learning_demo())
