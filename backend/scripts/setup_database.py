# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

import asyncio
import os
import sys

import asyncpg
from dotenv import load_dotenv


async def setup_database():
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    load_dotenv(env_path)

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not found in .env")
        sys.exit(1)

    clean_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    sql_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "infra",
            "database",
            "init-scripts",
            "02-init-tables-and-system.sql",
        )
    )

    if not os.path.exists(sql_path):
        print(f"ERROR: SQL script not found at {sql_path}")
        sys.exit(1)

    with open(sql_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    print("Connecting to Supabase PostgreSQL database...")
    try:
        conn = await asyncpg.connect(clean_url, timeout=15)
        print("Executing 02-init-tables-and-system.sql...")
        await conn.execute(sql_content)
        print("SUCCESS: Executed all DDL statements successfully.")

        # Verify created tables
        tables = await conn.fetch(
            """
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_schema IN ('identity', 'system', 'course', 'learning', 'assessment', 'examination', 'gradebook', 'analytics')
            ORDER BY table_schema, table_name;
            """
        )
        print(f"Total tables created ({len(tables)} tables):")
        for t in tables:
            print(f"  [OK] {t['table_schema']}.{t['table_name']}")

        await conn.close()

    except Exception as e:
        print(f"ERROR executing DDL: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(setup_database())
