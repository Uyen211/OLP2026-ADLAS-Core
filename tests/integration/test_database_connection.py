# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

import os
import pytest
import asyncpg
from dotenv import load_dotenv


@pytest.mark.asyncio
async def test_database_connection_and_schemas():
    """Verify that PostgreSQL connection succeeds and all 8 schemas exist."""
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    load_dotenv(env_path)

    db_url = os.getenv("DATABASE_URL")
    assert db_url is not None, "DATABASE_URL not found in .env"

    clean_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(clean_url, timeout=10)

    try:
        # Check all 8 bounded context schemas
        schemas = await conn.fetch(
            """
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name IN ('identity', 'system', 'course', 'learning', 'assessment', 'examination', 'gradebook', 'analytics')
            ORDER BY schema_name;
            """
        )
        found_schemas = [r["schema_name"] for r in schemas]
        assert len(found_schemas) == 8, f"Expected 8 schemas, found {len(found_schemas)}: {found_schemas}"

        # Check total tables across schemas >= 35
        tables = await conn.fetch(
            """
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_schema IN ('identity', 'system', 'course', 'learning', 'assessment', 'examination', 'gradebook', 'analytics')
            ORDER BY table_schema, table_name;
            """
        )
        assert len(tables) >= 35, f"Expected at least 35 tables, found {len(tables)}"

    finally:
        await conn.close()

