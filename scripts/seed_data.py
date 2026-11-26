# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""
Master Seed Orchestrator for ADLAS Platform.
Cleans existing domain records (TRUNCATE CASCADE) and orchestrates specific sub-seeds:
1. Schema extension verification (03, 04, 05 init-scripts)
2. Database cleanup across domain schemas
3. scripts/seed_course_demo.py (Identity accounts, Course templates, Active sections, LOs, Roster)
4. scripts/seed_assessment_demo.py (Assignments, Submissions, AI disclosures, Viva Sandbox transcripts)
"""

import asyncio
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv

env_path = os.path.join(REPO_ROOT, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

db_url = os.getenv("DATABASE_URL", "")
if not db_url:
    db_url = "postgresql+asyncpg://postgres:AdlasPass2026@localhost:5432/postgres"

# Auto-redirect host connection from container name "postgres" to "localhost"
if "@postgres:" in db_url:
    db_url = db_url.replace("@postgres:", "@localhost:")
    os.environ["DATABASE_URL"] = db_url

import asyncpg

from scripts.seed_assessment_demo import seed_assessment_demo
from scripts.seed_course_demo import seed_course_demo


async def reset_database(clean_url: str) -> None:
    """Apply schema extensions and dynamically truncate all domain tables."""
    print("=" * 65)
    print("ADLAS MASTER SEED: PHASE 1 - MIGRATION CHECK & DATABASE CLEANUP")
    print("=" * 65)
    print("Connecting to PostgreSQL...")
    conn = await asyncpg.connect(clean_url, timeout=15)
    try:
        # 1. Apply any pending migration extensions (03, 04, 05)
        init_scripts_dir = os.path.join(REPO_ROOT, "infra", "database", "init-scripts")
        if os.path.exists(init_scripts_dir):
            for filename in sorted(os.listdir(init_scripts_dir)):
                if filename.startswith(("03", "04", "05")) and filename.endswith(".sql"):
                    sql_path = os.path.join(init_scripts_dir, filename)
                    with open(sql_path, "r", encoding="utf-8") as f:  # noqa: ASYNC230
                        print(f"  [SCHEMA] Applying extension: {filename}...")
                        await conn.execute(f.read())

        # 2. Dynamically find all actual tables in application schemas
        rows = await conn.fetch("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_schema IN ('identity', 'course', 'assessment', 'examination', 'gradebook', 'analytics', 'learning')
              AND table_type = 'BASE TABLE';
        """)
        if rows:
            table_list = [f'"{r["table_schema"]}"."{r["table_name"]}"' for r in rows]
            print(f"  [CLEANUP] Truncating {len(table_list)} tables with CASCADE...")
            await conn.execute(f"TRUNCATE TABLE {', '.join(table_list)} CASCADE;")
            print("  [OK] Cleaned existing data successfully. Database is at baseline.")
        else:
            print("  [INFO] No domain tables found to truncate.")
    finally:
        await conn.close()


async def seed_database() -> None:
    clean_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    await reset_database(clean_url)

    print("\n" + "=" * 65)
    print("ADLAS MASTER SEED: PHASE 2 - MODULAR SEED EXECUTION")
    print("=" * 65)

    # Sub-seed 1: Course & Identity
    print("\n>>> Running Module Seed: Course & Identity (scripts/seed_course_demo.py)...")
    course_data = await seed_course_demo()
    print("  [OK] Course & Identity seed completed.")

    # Sub-seed 2: Assessment & Viva
    print("\n>>> Running Module Seed: Assessment & Viva Sandbox (scripts/seed_assessment_demo.py)...")
    await seed_assessment_demo()
    print("  [OK] Assessment & Viva Sandbox seed completed.")

    print("\n" + "=" * 65)
    print("ADLAS MASTER SEED COMPLETED SUCCESSFULLY! READY FOR EVALUATION.")
    print("=" * 65)
    print("Default Evaluation Accounts:")
    print("  - Quản trị viên (Admin)   : admin@adlas.edu.vn    / AdminPass123!   (Mã: AD202601)")
    print("  - Giảng viên 1 (Teacher)  : teacher1@adlas.edu.vn / TeacherPass123! (Mã: GV202601)")
    print("  - Giảng viên 2 (Teacher)  : teacher2@adlas.edu.vn / TeacherPass123! (Mã: GV202602)")
    print("  - Sinh viên 1 (Student)   : student1@adlas.edu.vn / StudentPass123! (Mã: SV2026001)")
    print("  - Sinh viên 2 (Student)   : student2@adlas.edu.vn / StudentPass123! (Mã: SV2026002)")
    print("-----------------------------------------------------------------")
    print("Active Course IT4409:")
    active_course = course_data.get("active_course")
    if active_course:
        print(f"  - Mã lớp học: {active_course.course_code} - {active_course.section_code}")
        print(f"  - Mã ghi danh (Join Code): {active_course.join_code}")
    print("Đường dẫn đăng nhập: http://localhost:5174/login")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(seed_database())
