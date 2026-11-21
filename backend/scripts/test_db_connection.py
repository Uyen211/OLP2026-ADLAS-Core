# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

import asyncio
import os
import sys
from urllib.parse import urlparse

import asyncpg
from dotenv import load_dotenv


async def test_connection():
    # Load environment variables
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    load_dotenv(env_path)

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not found in .env")
        sys.exit(1)

    # Clean URL if starts with postgresql+asyncpg://
    clean_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    print(f"Connecting to database...")
    try:
        conn = await asyncpg.connect(clean_url, timeout=10)
        print("SUCCESS: Connected to PostgreSQL database successfully.")

        # Check existing schemas
        schemas = await conn.fetch(
            """
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name IN ('identity', 'system', 'course', 'learning', 'assessment', 'examination', 'gradebook', 'analytics')
            ORDER BY schema_name;
            """
        )
        found_schemas = [r["schema_name"] for r in schemas]
        print(f"Schemas detected ({len(found_schemas)}/8): {', '.join(found_schemas)}")

        # Check tables in those schemas
        tables = await conn.fetch(
            """
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_schema IN ('identity', 'system', 'course', 'learning', 'assessment', 'examination', 'gradebook', 'analytics')
            ORDER BY table_schema, table_name;
            """
        )
        print(f"Tables detected across schemas: {len(tables)} tables")
        for t in tables:
            print(f"  - {t['table_schema']}.{t['table_name']}")

        await conn.close()
        return len(tables)

    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_connection())
