# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Master single-command orchestrator to idempotently seed ADLAS demo data."""

import asyncio
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


def _configure_runtime_env() -> None:
    """Ensure PYTHONPATH and host-reachable DATABASE_URL when invoked outside Docker."""
    env_file = os.path.join(REPO_ROOT, ".env")
    if os.path.exists(env_file):
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
        except ImportError:
            pass

    db_url = os.getenv("DATABASE_URL", "")
    # Rewrite Docker-internal 'postgres' hostname to 'localhost' when running on host OS
    if not os.path.exists("/.dockerenv") and "@postgres:" in db_url:
        os.environ["DATABASE_URL"] = db_url.replace("@postgres:", "@localhost:")


def seed_database() -> None:
    """Run complete idempotent demo seed covering accounts, 3 courses, modules, materials, and assessments."""
    _configure_runtime_env()

    from seed_learning_demo import seed_learning_demo

    print("=================================================================")
    print(" ADLAS Platform - Unified Demo Data Orchestrator")
    print("=================================================================")
    asyncio.run(seed_learning_demo())
    print("-----------------------------------------------------------------")
    print(" Demo Accounts Ready:")
    print("   - Instructor : teacher1@adlas.edu.vn / TeacherPass123!")
    print("   - Student 1  : student1@adlas.edu.vn / StudentPass123!")
    print("   - Student 2  : student2@adlas.edu.vn / StudentPass123!")
    print("   - Admin      : admin@adlas.edu.vn    / AdminPass123!")
    print(" Courses Seeded (Consistent TV1 + TV2 + TV3):")
    print("   1. IT4409 - Phat trien Ung dung Web Nang cao (L01)")
    print("   2. IT3080 - Mang May tinh & An toan Thong tin (L01)")
    print("   3. IT4010 - Kien truc & Thiet ke Phan mem (L01)")
    print("=================================================================")


if __name__ == "__main__":
    seed_database()
