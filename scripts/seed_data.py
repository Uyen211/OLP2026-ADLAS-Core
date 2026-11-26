# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Master single-command orchestrator to clean existing database records and seed ADLAS demo data."""

import asyncio
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


def _configure_runtime_env() -> str:
    """Ensure PYTHONPATH and host-reachable DATABASE_URL when invoked outside Docker."""
    env_file = os.path.join(REPO_ROOT, ".env")
    if os.path.exists(env_file):
        try:
            from dotenv import load_dotenv

            load_dotenv(env_file)
        except ImportError:
            pass

    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        db_url = "postgresql+asyncpg://postgres:AdlasPass2026@localhost:5432/postgres"

    # Rewrite Docker-internal 'postgres' hostname to 'localhost' when running on host OS
    if not os.path.exists("/.dockerenv") and "@postgres:" in db_url:
        db_url = db_url.replace("@postgres:", "@localhost:")
        os.environ["DATABASE_URL"] = db_url

    return db_url


async def _reset_database(db_url: str) -> None:
    """Apply schema extensions and dynamically truncate all domain tables before seeding."""
    import asyncpg

    clean_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    print("=" * 65)
    print(" ADLAS Platform - Database Reset & Migration Pre-check")
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
            WHERE table_schema IN ('identity', 'course', 'learning', 'assessment', 'examination', 'gradebook', 'analytics')
              AND table_type = 'BASE TABLE';
        """)
        if rows:
            table_list = [f'"{r["table_schema"]}"."{r["table_name"]}"' for r in rows]
            print(f"  [CLEANUP] Truncating {len(table_list)} tables with CASCADE...")
            await conn.execute(f"TRUNCATE TABLE {', '.join(table_list)} CASCADE;")
            print("  [OK] Cleaned all existing records successfully.")
        else:
            print("  [INFO] No domain tables found to truncate.")
    finally:
        await conn.close()


def seed_database() -> None:
    """Run complete idempotent demo seed covering accounts, 3 courses, modules, materials, and assessments."""
    db_url = _configure_runtime_env()

    # 1. Reset database records to ensure baseline consistency
    asyncio.run(_reset_database(db_url))

    # 2. Invoke unified learning demo seed
    try:
        from scripts.seed_learning_demo import seed_learning_demo
    except ModuleNotFoundError:
        from seed_learning_demo import seed_learning_demo

    print("\n" + "=" * 65)
    print(" ADLAS Platform - Unified Demo Data Orchestrator")
    print("=" * 65)
    asyncio.run(seed_learning_demo())
    print("-----------------------------------------------------------------")
    print(" Demo Accounts Ready:")
    print("   - Instructor : teacher1@adlas.edu.vn / TeacherPass123! (Mã: GV202601)")
    print("   - Student 1  : student1@adlas.edu.vn / StudentPass123! (Mã: SV2026001)")
    print("   - Student 2  : student2@adlas.edu.vn / StudentPass123! (Mã: SV2026002)")
    print("   - Admin      : admin@adlas.edu.vn    / AdminPass123!   (Mã: AD202600)")
    print(" Courses Seeded (Consistent TV1 + TV2 + TV3):")
    print("   1. IT4409 - Phat trien Ung dung Web Nang cao (L01)")
    print("   2. IT3080 - Mang May tinh & An toan Thong tin (L01)")
    print("   3. IT4010 - Kien truc & Thiet ke Phan mem (L01)")
    print("=================================================================")


if __name__ == "__main__":
    seed_database()
