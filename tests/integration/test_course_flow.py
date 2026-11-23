# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Integration tests for Phase 1 Identity & Course flows against PostgreSQL."""

from datetime import date
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
from app.main import app
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


def _build_xlsx(rows: list[list[object]]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    wb.close()
    return buf.getvalue()


@pytest_asyncio.fixture
async def integration_client():
    """
    Yield `(client, session)` bound to a real PostgreSQL connection wrapped in a
    transaction that is rolled back after each test. Skips if DB is unreachable.
    """
    db_url = _resolve_test_db_url()
    engine = create_async_engine(db_url, pool_pre_ping=True)

    try:
        conn = await engine.connect()
    except Exception as exc:
        await engine.dispose()
        pytest.skip(f"PostgreSQL is not reachable for integration tests: {exc}")

    outer_tx = await conn.begin()
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


async def _create_user(
    session: AsyncSession,
    *,
    email: str,
    user_code: str,
    full_name: str,
    password: str = "Teacher@2026!",
    system_role: str = "ADMIN",
) -> User:
    user = User(
        id=uuid.uuid4(),
        email=email,
        user_code=user_code,
        full_name=full_name,
        password_hash=hash_password(password),
        system_role=system_role,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def _login_bearer(client: AsyncClient, identifier: str, password: str) -> str:
    res = await client.post(
        "/api/v1/auth/login",
        json={"identifier": identifier, "password": password, "remember_me": False},
    )
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    assert token
    return token


@pytest.mark.asyncio
async def test_1_instructor_create_course_add_three_los_and_publish(integration_client):
    """Scenario 1: Create instructor, login, create course, add 3 LOs, and publish."""
    client, session = integration_client
    suffix = uuid.uuid4().hex[:6].upper()
    email = f"gv_{suffix}@adlas.edu.vn"
    await _create_user(
        session,
        email=email,
        user_code=f"GV{suffix}",
        full_name="Giang Vien Test 1",
        system_role="ADMIN",
    )

    token = await _login_bearer(client, email, "Teacher@2026!")
    headers = {"Authorization": f"Bearer {token}"}

    course_res = await client.post(
        "/api/v1/courses",
        headers=headers,
        json={
            "course_code": f"INT{suffix[:4]}",
            "section_code": "N01",
            "name": "Kiem thu Tich hop",
            "semester": "HK1-2026",
            "credits": 3,
            "start_date": "2026-09-01",
            "end_date": "2026-12-20",
            "syllabus_text": "<p>De cuong mon hoc</p>",
            "is_template": False,
        },
    )
    assert course_res.status_code == 201, course_res.text
    course_id = course_res.json()["id"]
    assert course_res.json()["status"] == "UNPUBLISHED"

    for idx in range(1, 4):
        lo_res = await client.post(
            f"/api/v1/courses/{course_id}/learning-objectives",
            headers=headers,
            json={
                "code": f"LO-0{idx}",
                "description": f"Chuan dau ra thu {idx} cua mon hoc kiem thu",
                "bloom_level": "APPLY",
            },
        )
        assert lo_res.status_code == 201, lo_res.text

    pub_res = await client.post(
        f"/api/v1/courses/{course_id}/status",
        headers=headers,
        json={"target_status": "PUBLISHED"},
    )
    assert pub_res.status_code == 200, pub_res.text
    assert pub_res.json()["status"] == "PUBLISHED"
    assert len(pub_res.json()["learning_objectives"]) == 3


@pytest.mark.asyncio
async def test_2_clone_template_has_zero_students_and_matching_los(integration_client):
    """Scenario 2 (BR-03): Clone template copies LOs and leaves zero STUDENT enrollments."""
    client, session = integration_client
    suffix = uuid.uuid4().hex[:6].upper()
    email = f"gv_clone_{suffix}@adlas.edu.vn"
    await _create_user(
        session,
        email=email,
        user_code=f"GVC{suffix}",
        full_name="Giang Vien Clone",
        system_role="ADMIN",
    )
    token = await _login_bearer(client, email, "Teacher@2026!")
    headers = {"Authorization": f"Bearer {token}"}

    tpl_res = await client.post(
        "/api/v1/courses",
        headers=headers,
        json={
            "course_code": f"TPL{suffix[:4]}",
            "section_code": "TPL",
            "name": "Mon Hoc Mau",
            "semester": "TEMPLATE",
            "credits": 3,
            "start_date": "2026-09-01",
            "end_date": "2026-12-20",
            "syllabus_text": "<p>Noi dung mau</p>",
            "is_template": True,
        },
    )
    assert tpl_res.status_code == 201, tpl_res.text
    template_id = tpl_res.json()["id"]

    for idx in range(1, 3):
        lo_res = await client.post(
            f"/api/v1/courses/{template_id}/learning-objectives",
            headers=headers,
            json={
                "code": f"LO-0{idx}",
                "description": f"Chuan dau ra mau so {idx} cho mon hoc",
                "bloom_level": "UNDERSTAND",
            },
        )
        assert lo_res.status_code == 201, lo_res.text

    clone_res = await client.post(
        "/api/v1/courses/clone",
        headers=headers,
        json={
            "template_id": template_id,
            "section_code": "N02",
            "semester": "HK2-2026",
            "start_date": "2027-01-10",
            "end_date": "2027-05-10",
        },
    )
    assert clone_res.status_code == 201, clone_res.text
    cloned_id = clone_res.json()["id"]
    assert clone_res.json()["is_template"] is False
    assert len(clone_res.json()["learning_objectives"]) == 2

    count_res = await session.execute(
        text(
            "SELECT count(*) FROM course.course_enrollments "
            "WHERE course_id = :cid AND contextual_role = 'STUDENT'"
        ),
        {"cid": uuid.UUID(cloned_id)},
    )
    assert count_res.scalar_one() == 0


@pytest.mark.asyncio
async def test_3_import_50_students_xlsx_and_reimport_skips_duplicates(integration_client):
    """Scenario 3: Import 50-student XLSX (added=50), re-import same file (added=0, skipped=50)."""
    client, session = integration_client
    suffix = uuid.uuid4().hex[:6].upper()
    email = f"gv_imp_{suffix}@adlas.edu.vn"
    await _create_user(
        session,
        email=email,
        user_code=f"GVI{suffix}",
        full_name="Giang Vien Import",
        system_role="ADMIN",
    )
    token = await _login_bearer(client, email, "Teacher@2026!")
    headers = {"Authorization": f"Bearer {token}"}

    course_res = await client.post(
        "/api/v1/courses",
        headers=headers,
        json={
            "course_code": f"IMP{suffix[:4]}",
            "section_code": "N01",
            "name": "Lap trinh Web",
            "semester": "HK1-2026",
            "credits": 3,
            "start_date": "2026-09-01",
            "end_date": "2026-12-20",
            "is_template": False,
        },
    )
    assert course_res.status_code == 201, course_res.text
    course_id = course_res.json()["id"]

    rows: list[list[object]] = [["MSSV", "Ho va ten", "Email"]]
    for i in range(1, 51):
        rows.append([f"SV{suffix}{i:03d}", f"Sinh Vien {i}", f"sv{suffix.lower()}{i:03d}@adlas.edu.vn"])
    xlsx_bytes = _build_xlsx(rows)

    first_res = await client.post(
        f"/api/v1/courses/{course_id}/roster/confirm",
        headers=headers,
        data={"send_notification": "false"},
        files={"file": ("roster50.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert first_res.status_code == 200, first_res.text
    assert first_res.json()["added"] == 50

    second_res = await client.post(
        f"/api/v1/courses/{course_id}/roster/confirm",
        headers=headers,
        data={"send_notification": "false"},
        files={"file": ("roster50.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert second_res.status_code == 200, second_res.text
    assert second_res.json()["added"] == 0
    assert second_res.json()["skipped_duplicates"] == 50


@pytest.mark.asyncio
async def test_4_student_join_by_code_and_rejected_when_closed(integration_client):
    """Scenario 4: Student joins via join code; closing enrollment causes 403 E-JOIN-01."""
    client, session = integration_client
    suffix = uuid.uuid4().hex[:6].upper()
    gv_email = f"gv_join_{suffix}@adlas.edu.vn"
    sv_email = f"sv_join_{suffix}@adlas.edu.vn"

    await _create_user(
        session,
        email=gv_email,
        user_code=f"GVJ{suffix}",
        full_name="Giang Vien Join",
        system_role="ADMIN",
    )
    await _create_user(
        session,
        email=sv_email,
        user_code=f"SVJ{suffix}",
        full_name="Sinh Vien Join",
        system_role="USER",
    )

    gv_token = await _login_bearer(client, gv_email, "Teacher@2026!")
    sv_token = await _login_bearer(client, sv_email, "Teacher@2026!")
    gv_headers = {"Authorization": f"Bearer {gv_token}"}
    sv_headers = {"Authorization": f"Bearer {sv_token}"}

    course_res = await client.post(
        "/api/v1/courses",
        headers=gv_headers,
        json={
            "course_code": f"JON{suffix[:4]}",
            "section_code": "N01",
            "name": "Co so Du lieu",
            "semester": "HK1-2026",
            "credits": 3,
            "start_date": "2026-09-01",
            "end_date": "2026-12-20",
            "is_template": False,
        },
    )
    assert course_res.status_code == 201, course_res.text
    course_id = course_res.json()["id"]
    join_code = course_res.json()["join_code"]

    lo_res = await client.post(
        f"/api/v1/courses/{course_id}/learning-objectives",
        headers=gv_headers,
        json={
            "code": "LO-01",
            "description": "Thiet ke luoc do co so du lieu quan he chuan",
            "bloom_level": "CREATE",
        },
    )
    assert lo_res.status_code == 201, lo_res.text

    pub_res = await client.post(
        f"/api/v1/courses/{course_id}/status",
        headers=gv_headers,
        json={"target_status": "PUBLISHED"},
    )
    assert pub_res.status_code == 200, pub_res.text

    join_ok = await client.post(
        "/api/v1/courses/join",
        headers=sv_headers,
        json={"join_code": join_code},
    )
    assert join_ok.status_code == 200, join_ok.text
    assert join_ok.json()["id"] == course_id

    close_res = await client.put(
        f"/api/v1/courses/{course_id}/join-code/settings",
        headers=gv_headers,
        json={"is_enrollment_open": False},
    )
    assert close_res.status_code == 200, close_res.text

    join_closed = await client.post(
        "/api/v1/courses/join",
        headers=sv_headers,
        json={"join_code": join_code},
    )
    assert join_closed.status_code == 403, join_closed.text
    assert join_closed.json()["detail"]["code"] == "E-JOIN-01"


@pytest.mark.asyncio
async def test_5_five_failed_logins_sets_locked_until_and_returns_e6(integration_client):
    """Scenario 5 (BR-02): 5 wrong password attempts set locked_until in DB and return 429 E-6."""
    client, session = integration_client
    suffix = uuid.uuid4().hex[:6].upper()
    email = f"lock_{suffix}@adlas.edu.vn"
    user = await _create_user(
        session,
        email=email,
        user_code=f"SVL{suffix}",
        full_name="Sinh Vien Lock",
        system_role="USER",
    )

    for attempt in range(1, 5):
        res = await client.post(
            "/api/v1/auth/login",
            json={"identifier": email, "password": "WrongPassword!1"},
        )
        assert res.status_code == 401, res.text
        assert res.json()["detail"]["code"] == "E-5"
        assert res.json()["detail"]["remaining_attempts"] == 5 - attempt

    fifth_res = await client.post(
        "/api/v1/auth/login",
        json={"identifier": email, "password": "WrongPassword!1"},
    )
    assert fifth_res.status_code == 429, fifth_res.text
    assert fifth_res.json()["detail"]["code"] == "E-6"

    row = await session.execute(
        text("SELECT failed_login_count, locked_until FROM identity.users WHERE id = :uid"),
        {"uid": user.id},
    )
    count, locked_until = row.one()
    assert count >= 5
    assert locked_until is not None


@pytest.mark.asyncio
async def test_6_partition_40_students_into_10_groups_and_save(integration_client):
    """Scenario 6 (AC-03): Partition 40 students into 10 groups of 4 and persist in DB."""
    client, session = integration_client
    suffix = uuid.uuid4().hex[:6].upper()
    gv_email = f"gv_grp_{suffix}@adlas.edu.vn"
    await _create_user(
        session,
        email=gv_email,
        user_code=f"GVG{suffix}",
        full_name="Giang Vien Group",
        system_role="ADMIN",
    )
    token = await _login_bearer(client, gv_email, "Teacher@2026!")
    headers = {"Authorization": f"Bearer {token}"}

    course_res = await client.post(
        "/api/v1/courses",
        headers=headers,
        json={
            "course_code": f"GRP{suffix[:4]}",
            "section_code": "N01",
            "name": "Do an Phan mem",
            "semester": "HK1-2026",
            "credits": 3,
            "start_date": date(2026, 9, 1).isoformat(),
            "end_date": date(2026, 12, 20).isoformat(),
            "is_template": False,
        },
    )
    assert course_res.status_code == 201, course_res.text
    course_id = course_res.json()["id"]

    rows: list[list[object]] = [["MSSV", "Ho va ten", "Email"]]
    for i in range(1, 41):
        rows.append([f"SVG{suffix}{i:02d}", f"Sinh Vien G{i}", f"svg{suffix.lower()}{i:02d}@adlas.edu.vn"])
    xlsx_bytes = _build_xlsx(rows)

    imp_res = await client.post(
        f"/api/v1/courses/{course_id}/roster/confirm",
        headers=headers,
        data={"send_notification": "false"},
        files={"file": ("roster40.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert imp_res.status_code == 200, imp_res.text
    assert imp_res.json()["added"] == 40

    preview_res = await client.post(
        f"/api/v1/courses/{course_id}/groups/partition/preview",
        headers=headers,
        json={
            "group_set_name": "Do an nhom",
            "mode": "RANDOM",
            "group_size": 4,
        },
    )
    assert preview_res.status_code == 200, preview_res.text
    draft = preview_res.json()
    assert len(draft["groups"]) == 10

    save_payload = {
        "groups": [
            {"name": g["name"], "member_ids": [m["user_id"] for m in g["members"]]}
            for g in draft["groups"]
        ]
    }
    save_res = await client.put(
        f"/api/v1/courses/{course_id}/groups/sets/Do%20an%20nhom",
        headers=headers,
        json=save_payload,
    )
    assert save_res.status_code == 200, save_res.text

    grp_count = (
        await session.execute(
            text("SELECT count(*) FROM course.course_groups WHERE course_id = :cid"),
            {"cid": uuid.UUID(course_id)},
        )
    ).scalar_one()
    mem_count = (
        await session.execute(
            text(
                "SELECT count(*) FROM course.course_group_members gm "
                "JOIN course.course_groups g ON g.id = gm.group_id "
                "WHERE g.course_id = :cid"
            ),
            {"cid": uuid.UUID(course_id)},
        )
    ).scalar_one()

    assert grp_count == 10
    assert mem_count == 40
