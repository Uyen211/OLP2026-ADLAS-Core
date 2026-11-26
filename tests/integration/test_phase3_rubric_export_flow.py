# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Integration tests for Phase 3 flow: Authoring -> Rubric -> LO Lock -> Pledge -> Freeze -> Export."""

from datetime import date, datetime, timedelta, timezone
import io
import os
import uuid
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
import openpyxl
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.core.database import get_db
from app.core.security import hash_password
from app.modules.analytics.reporting.schemas import SHEET_GRADES, SHEET_LO, WATERMARK_TEXT
from app.modules.course.service import default_join_rate_limiter
from app.modules.identity.service import default_ip_rate_limiter
from app.modules.system.models import User


def _resolve_test_db_url() -> str:
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    load_dotenv(env_path)
    raw_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/adlas",
    )
    if raw_url.startswith("postgresql://"):
        raw_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if not os.path.exists("/.dockerenv"):
        raw_url = raw_url.replace("@postgres:", "@localhost:")
    return raw_url


@pytest_asyncio.fixture
async def phase3_client():
    """Real PostgreSQL connection wrapped in a transaction that rolls back after the test."""
    engine = create_async_engine(_resolve_test_db_url(), pool_pre_ping=True)
    try:
        conn = await engine.connect()
    except Exception as exc:
        await engine.dispose()
        pytest.skip(f"PostgreSQL is not reachable for integration tests: {exc}")

    from app.main import app

    outer_tx = await conn.begin()
    # Ensure Phase 2/3 additive DDL is present within the rolled-back test transaction.
    init_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "infra", "database", "init-scripts")
    )
    raw_conn = await conn.get_raw_connection()
    for sql_file in ("04-assessment-extensions.sql", "06-assessment-reporting-extensions.sql"):
        sql_path = os.path.join(init_dir, sql_file)
        if os.path.exists(sql_path):
            with open(sql_path, encoding="utf-8") as fh:
                await raw_conn.driver_connection.execute(fh.read())

    session = AsyncSession(
        bind=conn,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    async def _override_get_db():
        yield session
        await session.flush()

    app.dependency_overrides[get_db] = _override_get_db
    default_ip_rate_limiter.reset_all()
    default_join_rate_limiter.reset_all()

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client, session
    finally:
        app.dependency_overrides.clear()
        default_ip_rate_limiter.reset_all()
        default_join_rate_limiter.reset_all()
        await session.close()
        await outer_tx.rollback()
        await conn.close()
        await engine.dispose()


async def _create_user(session: AsyncSession, email: str, code: str, name: str, role: str) -> User:
    user = User(
        id=uuid.uuid4(),
        email=email,
        user_code=code,
        full_name=name,
        password_hash=hash_password("Adlas@2026!"),
        system_role=role,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def _login(client: AsyncClient, email: str) -> dict[str, str]:
    res = await client.post(
        "/api/v1/auth/login",
        json={"identifier": email, "password": "Adlas@2026!", "remember_me": False},
    )
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _rubric_payload(lo_id: str) -> dict:
    def levels(pts: float) -> list[dict]:
        return [
            {"level": "EXCELLENT", "label": "Xuất sắc", "description": "Đạt tối đa", "points": pts},
            {"level": "GOOD", "label": "Khá / Giỏi", "description": "Tốt", "points": round(pts * 0.8, 1)},
            {"level": "PROFICIENT", "label": "Đạt chuẩn", "description": "Cơ bản", "points": round(pts * 0.5, 1)},
            {"level": "INSUFFICIENT", "label": "Chưa đạt", "description": "Không đạt", "points": 0.0},
        ]

    return {
        "title": "Rubric Đồ án Chặng 3",
        "criteria": [
            {"title": "Kiến trúc", "lo_id": lo_id, "max_points": 4.0, "rating_levels": levels(4.0)},
            {"title": "Cài đặt", "lo_id": lo_id, "max_points": 6.0, "rating_levels": levels(6.0)},
        ],
    }


@pytest.mark.asyncio
async def test_phase3_end_to_end_authoring_rubric_pledge_and_export(phase3_client):
    client, session = phase3_client
    suffix = uuid.uuid4().hex[:6].upper()
    gv_email = f"gv_p3_{suffix}@adlas.edu.vn"
    sv_email = f"sv_p3_{suffix}@adlas.edu.vn"
    await _create_user(session, gv_email, f"GV{suffix}", "Giảng viên Chặng 3", "ADMIN")
    sv_user = await _create_user(session, sv_email, f"SV{suffix}", "Sinh viên Chặng 3", "USER")

    gv_headers = await _login(client, gv_email)
    sv_headers = await _login(client, sv_email)

    # 1. Create course, add LO, publish course, enroll student
    course_res = await client.post(
        "/api/v1/courses",
        headers=gv_headers,
        json={
            "course_code": f"IT{suffix[:4]}",
            "section_code": "150001",
            "name": "Kiểm thử tích hợp Chặng 3",
            "semester": "2026-1",
            "credits": 3,
            "start_date": date.today().isoformat(),
            "end_date": (date.today() + timedelta(days=90)).isoformat(),
            "syllabus_text": "<p>Đề cương kiểm thử Chặng 3</p>",
        },
    )
    assert course_res.status_code == 201, course_res.text
    course_id = course_res.json()["id"]

    lo_res = await client.post(
        f"/api/v1/courses/{course_id}/learning-objectives",
        headers=gv_headers,
        json={"code": "LO1", "description": "Thiết kế hệ thống phân tán và đánh giá năng lực", "bloom_level": "CREATE"},
    )
    assert lo_res.status_code == 201, lo_res.text
    lo_id = lo_res.json()["id"]

    pub_course = await client.post(
        f"/api/v1/courses/{course_id}/status",
        headers=gv_headers,
        json={"target_status": "PUBLISHED"},
    )
    assert pub_course.status_code == 200, pub_course.text
    join_code = pub_course.json()["join_code"]
    if not join_code:
        jc_res = await client.post(f"/api/v1/courses/{course_id}/join-code/regenerate", headers=gv_headers)
        assert jc_res.status_code == 200, jc_res.text
        join_code = jc_res.json()["join_code"]

    join_res = await client.post(
        "/api/v1/courses/join",
        headers=sv_headers,
        json={"join_code": join_code},
    )
    assert join_res.status_code in (200, 201), join_res.text

    # 2. Create Draft assignment -> hidden from student
    now = datetime.now(timezone.utc)
    create_asn = await client.post(
        f"/api/v1/assessments/courses/{course_id}/assignments",
        headers=gv_headers,
        json={
            "title": "Bài tập lớn Chặng 3",
            "instructions": "Xây dựng API và kiểm thử.",
            "due_date": (now + timedelta(days=5)).isoformat(),
            "until_date": (now + timedelta(days=7)).isoformat(),
            "is_viva_required": False,
            "ai_policy_level": "YELLOW",
            "publish": False,
        },
    )
    assert create_asn.status_code == 201, create_asn.text
    asn_id = create_asn.json()["id"]
    assert create_asn.json()["is_published"] is False

    hidden_detail = await client.get(f"/api/v1/assessments/assignments/{asn_id}", headers=sv_headers)
    assert hidden_detail.status_code == 404

    # 3. Publish assignment -> visible to student
    pub_asn = await client.post(f"/api/v1/assessments/assignments/{asn_id}/publish", headers=gv_headers)
    assert pub_asn.status_code == 200 and pub_asn.json()["is_published"] is True
    visible_detail = await client.get(f"/api/v1/assessments/assignments/{asn_id}", headers=sv_headers)
    assert visible_detail.status_code == 200

    # 4. Save Rubric 10.0 linked to LO -> blocks LO deletion (BR-LO-01)
    rubric_res = await client.put(
        f"/api/v1/assessments/assignments/{asn_id}/rubric",
        headers=gv_headers,
        json=_rubric_payload(lo_id),
    )
    assert rubric_res.status_code == 200, rubric_res.text
    assert rubric_res.json()["total_points"] == 10.0

    del_lo = await client.delete(f"/api/v1/courses/{course_id}/learning-objectives/{lo_id}", headers=gv_headers)
    assert del_lo.status_code == 409

    # 5. Student signs integrity pledge
    sign_res = await client.post(
        f"/api/v1/assessments/assignments/{asn_id}/integrity-pledge",
        headers=sv_headers,
        json={
            "accepted": True,
            "self_contribution_pct": 90,
            "tools_used": ["ChatGPT"],
            "usage_description": "Dùng ChatGPT để rà soát lỗi chính tả và cấu trúc tài liệu.",
        },
    )
    assert sign_res.status_code == 201, sign_res.text

    # 6. Student submits v1 -> Rubric automatically freezes -> PUT rubric returns 409 E-RUB-02
    sub_res = await client.post(
        f"/api/v1/assessments/assignments/{asn_id}/submissions",
        headers=sv_headers,
        json={
            "file_url": "http://storage/sub_v1.zip",
            "file_name": "sub_v1.zip",
            "is_pledge_signed": True,
            "ai_disclosure": {
                "self_contribution_pct": 90,
                "tools_used": ["ChatGPT"],
                "usage_description": "Dùng ChatGPT để rà soát lỗi chính tả và cấu trúc tài liệu.",
            },
        },
    )
    assert sub_res.status_code == 201, sub_res.text

    frozen_edit = await client.put(
        f"/api/v1/assessments/assignments/{asn_id}/rubric",
        headers=gv_headers,
        json=_rubric_payload(lo_id),
    )
    assert frozen_edit.status_code == 409
    assert frozen_edit.json()["detail"]["code"] == "E-RUB-02"

    # 7. Seed minimal gradebook rows & verify Excel (2-Sheet + Watermark) and PDF export
    group_id, col_id = uuid.uuid4(), uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO gradebook.gradebook_groups (id, course_id, group_name, weight_percent, is_hurdle) "
            "VALUES (:gid, :cid, 'Cuối kỳ', 100, false)"
        ),
        {"gid": group_id, "cid": uuid.UUID(course_id)},
    )
    await session.execute(
        text(
            "INSERT INTO gradebook.gradebook_columns (id, course_id, group_id, item_type, title, max_points) "
            "VALUES (:col_id, :cid, :gid, 'ASSIGNMENT', 'Thi cuối kỳ', 10.0)"
        ),
        {"col_id": col_id, "cid": uuid.UUID(course_id), "gid": group_id},
    )
    await session.execute(
        text(
            "INSERT INTO gradebook.grades (id, column_id, user_id, official_score) "
            "VALUES (:id, :col_id, :uid, 8.5)"
        ),
        {"id": uuid.uuid4(), "col_id": col_id, "uid": sv_user.id},
    )
    await session.flush()

    draft_xlsx = await client.get(
        f"/api/v1/analytics/reports/courses/{course_id}/export/excel?confirm_draft=true",
        headers=gv_headers,
    )
    assert draft_xlsx.status_code == 200, draft_xlsx.text
    assert "_DU_KIEN.xlsx" in draft_xlsx.headers.get("content-disposition", "")
    wb = openpyxl.load_workbook(io.BytesIO(draft_xlsx.content))
    assert wb.sheetnames == [SHEET_GRADES, SHEET_LO]
    vals = [c.value for r in wb[SHEET_GRADES].iter_rows() for c in r if c.value is not None]
    assert WATERMARK_TEXT in vals
    wb.close()

    pdf_res = await client.get(
        f"/api/v1/analytics/reports/courses/{course_id}/export/pdf?confirm_draft=true",
        headers=gv_headers,
    )
    assert pdf_res.status_code == 200 and pdf_res.content.startswith(b"%PDF-")

    # Lock gradebook -> official export without Watermark
    await session.execute(
        text(
            "INSERT INTO gradebook.course_gradebook_locks (course_id, is_locked, locked_at) "
            "VALUES (:cid, true, NOW())"
        ),
        {"cid": uuid.UUID(course_id)},
    )
    await session.flush()

    official_xlsx = await client.get(
        f"/api/v1/analytics/reports/courses/{course_id}/export/excel",
        headers=gv_headers,
    )
    assert official_xlsx.status_code == 200
    assert "_ChinhThuc.xlsx" in official_xlsx.headers.get("content-disposition", "")
    wb_off = openpyxl.load_workbook(io.BytesIO(official_xlsx.content))
    off_vals = [c.value for r in wb_off[SHEET_GRADES].iter_rows() for c in r if c.value is not None]
    assert WATERMARK_TEXT not in off_vals
    wb_off.close()
