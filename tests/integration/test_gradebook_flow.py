# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""End-to-end integration tests for Module 5 (Gradebook, SpeedGrader, Storage & Sealing) against PostgreSQL."""

from datetime import date, datetime, timedelta, timezone
import os
import uuid

from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.modules.assessment.models import (
    Assignment,
    AssignmentSubmission,
    Rubric,
    RubricCriteria,
    VivaTranscript,
)
from app.modules.course.enums import ContextualRole, EnrollmentStatus
from app.modules.course.models import Course, CourseEnrollment, LearningObjective
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
async def gb_client():
    """Yield `(client, session)` bound to real PostgreSQL inside a rolled-back outer transaction."""
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

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client, session
    finally:
        app.dependency_overrides.clear()
        default_ip_rate_limiter.reset_all()
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
    password: str = "GradePass@2026!",
    system_role: str = "USER",
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
        json={"identifier": identifier, "password": password},
    )
    assert res.status_code == 200, res.text
    return f"Bearer {res.json()['access_token']}"


@pytest.mark.asyncio
async def test_full_gradebook_speedgrader_muted_hurdle_and_lock_lifecycle(gb_client):
    client, session = gb_client
    suffix = uuid.uuid4().hex[:8]

    # 1. Seed Instructor, Admin, 2 Students, Course, LO, Rubric, Assignment & Submission
    instructor = await _create_user(
        session,
        email=f"gv_{suffix}@adlas.edu.vn",
        user_code=f"GV{suffix[:5]}",
        full_name="Giang Vien Gradebook",
    )
    admin = await _create_user(
        session,
        email=f"admin_{suffix}@adlas.edu.vn",
        user_code=f"AD{suffix[:5]}",
        full_name="Quan Tri Dao Tao",
        system_role="ADMIN",
    )
    student_pass = await _create_user(
        session,
        email=f"sv1_{suffix}@adlas.edu.vn",
        user_code=f"SV1{suffix[:4]}",
        full_name="Sinh Vien Dat Chuan",
    )
    student_hurdle = await _create_user(
        session,
        email=f"sv2_{suffix}@adlas.edu.vn",
        user_code=f"SV2{suffix[:4]}",
        full_name="Sinh Vien Diem Liet",
    )

    course = Course(
        id=uuid.uuid4(),
        course_code=f"GB{suffix[:4].upper()}",
        section_code="L01",
        name="Kiem thu Module Gradebook & SpeedGrader",
        semester="HK1-2026",
        credits=3,
        start_date=date(2026, 9, 1),
        end_date=date(2026, 12, 30),
        status="PUBLISHED",
        created_by=instructor.id,
    )
    session.add(course)
    await session.flush()

    for usr, role in [
        (instructor, ContextualRole.INSTRUCTOR.value),
        (student_pass, ContextualRole.STUDENT.value),
        (student_hurdle, ContextualRole.STUDENT.value),
    ]:
        session.add(
            CourseEnrollment(
                course_id=course.id,
                user_id=usr.id,
                contextual_role=role,
                enrollment_status=EnrollmentStatus.ACTIVE.value,
            )
        )

    lo1 = LearningObjective(
        id=uuid.uuid4(),
        course_id=course.id,
        code="LO1",
        description="Thiet ke va trien khai he thong",
        bloom_level="APPLY",
        order_index=1,
    )
    session.add(lo1)
    await session.flush()

    now = datetime.now(timezone.utc)
    assignment = Assignment(
        id=uuid.uuid4(),
        course_id=course.id,
        title="BTL Tich hop SpeedGrader",
        instructions="Xay dung he thong ADLAS va bao ve Viva.",
        submission_type="FILE",
        due_date=now + timedelta(days=5),
        until_date=now + timedelta(days=7),
        is_viva_required=True,
        viva_question_count=2,
    )
    session.add(assignment)
    await session.flush()

    rubric = Rubric(assignment_id=assignment.id, title="Rubric Integration Test", total_points=10.0)
    session.add(rubric)
    await session.flush()
    crit1 = RubricCriteria(
        rubric_id=rubric.id,
        lo_id=lo1.id,
        competency_code="C1",
        title="Thiet ke kien truc",
        max_points=6.0,
        rating_levels=[{"level": "Tot", "points": 6.0}, {"level": "Dat", "points": 4.0}],
        order_index=1,
    )
    crit2 = RubricCriteria(
        rubric_id=rubric.id,
        lo_id=lo1.id,
        competency_code="C2",
        title="Bao ve Viva",
        max_points=4.0,
        rating_levels=[{"level": "Tot", "points": 4.0}, {"level": "Dat", "points": 2.0}],
        order_index=2,
    )
    session.add_all([crit1, crit2])
    await session.flush()

    sub = AssignmentSubmission(
        id=uuid.uuid4(),
        assignment_id=assignment.id,
        user_id=student_pass.id,
        version=1,
        project_title="He thong ADLAS",
        ai_disclosure_data={"tools_used": ["ChatGPT"], "self_contribution_pct": 85},
        self_contribution_pct=85,
        is_pledge_signed=True,
        submitted_at=now,
        status="VIVA_COMPLETED",
    )
    session.add(sub)
    await session.flush()

    viva = VivaTranscript(
        submission_id=sub.id,
        status="COMPLETED",
        questions_answers={
            "ai_digest_summary": "## Tom tat bai nop\nSinh vien da trien khai day du pipeline.",
            "digest_type": "SUBMISSION_DIGEST",
            "total_questions": 1,
            "questions": [{"id": "q1", "question_index": 1, "total_questions": 1, "question_text": "Giai thich kien truc?"}],
            "answers": {"q1": {"answer_text": "Em dung kien truc Modular Monolith tach bach service.", "time_spent_seconds": 45}},
        },
        violation_logs=[],
    )
    session.add(viva)
    await session.flush()

    gv_headers = {"Authorization": await _login_bearer(client, instructor.email, "GradePass@2026!")}
    sv1_headers = {"Authorization": await _login_bearer(client, student_pass.email, "GradePass@2026!")}
    admin_headers = {"Authorization": await _login_bearer(client, admin.email, "GradePass@2026!")}

    # 2. Structure weight validation (E-11 when != 100%)
    bad_struct = await client.put(
        f"/api/v1/gradebook/courses/{course.id}/structure",
        headers=gv_headers,
        json={
            "groups": [
                {"group_name": "BTL", "weight_percent": 40, "drop_lowest_count": 0, "is_hurdle": False, "hurdle_min_score": 4.0},
                {"group_name": "Cuoi ky", "weight_percent": 50, "drop_lowest_count": 0, "is_hurdle": True, "hurdle_min_score": 4.0},
            ]
        },
    )
    assert bad_struct.status_code == 400
    assert bad_struct.json()["detail"]["code"] == "E-11"

    # Valid 100% structure: BTL 40% + Final 60% (Hurdle 4.0)
    ok_struct = await client.put(
        f"/api/v1/gradebook/courses/{course.id}/structure",
        headers=gv_headers,
        json={
            "groups": [
                {"group_name": "BTL", "weight_percent": 40, "drop_lowest_count": 0, "is_hurdle": False, "hurdle_min_score": 4.0},
                {"group_name": "Cuoi ky", "weight_percent": 60, "drop_lowest_count": 0, "is_hurdle": True, "hurdle_min_score": 4.0},
            ]
        },
    )
    assert ok_struct.status_code == 200, ok_struct.text
    groups = ok_struct.json()["groups"]
    final_group = next(g for g in groups if g["group_name"] == "Cuoi ky")

    # Sync assignments & create Final Exam column
    sync_res = await client.post(
        f"/api/v1/gradebook/courses/{course.id}/sync-items",
        headers=gv_headers,
    )
    assert sync_res.status_code == 200

    final_col_res = await client.post(
        f"/api/v1/gradebook/courses/{course.id}/columns",
        headers=gv_headers,
        json={
            "group_id": final_group["id"],
            "title": "Thi Cuoi ky",
            "item_type": "MANUAL",
            "max_points": 10.0,
            "is_muted": True,
        },
    )
    assert final_col_res.status_code == 201, final_col_res.text
    final_col_id = final_col_res.json()["id"]

    # Find synced BTL column (default is_muted=True per BR-09)
    struct_after = (
        await client.get(f"/api/v1/gradebook/courses/{course.id}/structure", headers=gv_headers)
    ).json()
    btl_col = next(
        c for g in struct_after["groups"] for c in g["columns"] if c["item_id"] == str(assignment.id)
    )
    assert btl_col["is_muted"] is True

    # 3. Upload & stream back Voice Feedback (verify byte-for-byte storage integrity)
    audio_bytes = b"OggS-mock-voice-feedback-payload-adlas-2026"
    upload_res = await client.post(
        "/api/v1/gradebook/voice-feedback/upload",
        headers=gv_headers,
        files={"file": ("feedback.webm", audio_bytes, "audio/webm")},
    )
    assert upload_res.status_code == 200, upload_res.text
    voice_url = upload_res.json()["voice_feedback_url"]

    stream_res = await client.get(voice_url, headers=sv1_headers)
    assert stream_res.status_code == 200
    assert stream_res.content == audio_bytes

    # 4. SpeedGrader workspace, draft autosave, and official grade save
    ws_res = await client.get(
        f"/api/v1/gradebook/speedgrader/submissions/{sub.id}",
        headers=gv_headers,
    )
    assert ws_res.status_code == 200, ws_res.text
    assert ws_res.json()["missing_viva"] is False

    draft_res = await client.patch(
        f"/api/v1/gradebook/speedgrader/submissions/{sub.id}/draft",
        headers=gv_headers,
        json={"instructor_feedback": "Ban nhap nhan xet 30s"},
    )
    assert draft_res.status_code == 200

    save_res = await client.post(
        f"/api/v1/gradebook/speedgrader/submissions/{sub.id}/grade",
        headers=gv_headers,
        json={
            "official_score": 8.5,
            "rubric_scores": {
                str(crit1.id): {"points": 5.0, "label": "Tot", "lo_id": str(lo1.id)},
                str(crit2.id): {"points": 3.5, "label": "Tot", "lo_id": str(lo1.id)},
            },
            "instructor_feedback": "Bai lam rat tot va bao ve Viva thuyet phuc.",
            "voice_feedback_url": voice_url,
        },
    )
    assert save_res.status_code == 200, save_res.text
    assert float(save_res.json()["official_score"]) == 8.5

    # Manual grades: student_pass gets 9.0 Final; student_hurdle gets 10.0 BTL but 3.5 Final (Hurdle fail!)
    for uid, col_id, score in [
        (student_pass.id, final_col_id, 9.0),
        (student_hurdle.id, btl_col["id"], 10.0),
        (student_hurdle.id, final_col_id, 3.5),
    ]:
        up_res = await client.put(
            f"/api/v1/gradebook/courses/{course.id}/columns/{col_id}/grades",
            headers=gv_headers,
            json={"user_id": str(uid), "official_score": score},
        )
        assert up_res.status_code == 200, up_res.text

    # 5. Muted Gradebook student read isolation (BR-09)
    sv1_muted = await client.get(
        f"/api/v1/gradebook/courses/{course.id}/my-grades",
        headers=sv1_headers,
    )
    assert sv1_muted.status_code == 200
    for item in sv1_muted.json()["items"]:
        assert item["is_muted"] is True
        assert item["official_score"] is None
        assert item["instructor_feedback"] is None

    # 6. Lock blocked while muted columns exist (E-GB-06)
    lock_blocked = await client.post(
        f"/api/v1/gradebook/courses/{course.id}/lock",
        headers=gv_headers,
        json={"confirmation_text": "KHOA DIEM"},
    )
    assert lock_blocked.status_code == 422
    assert lock_blocked.json()["detail"]["code"] == "E-GB-06"

    # 7. Post Grades (Unmute both columns) -> Student sees score & TT08 calculation
    for cid in [btl_col["id"], final_col_id]:
        post_res = await client.post(
            f"/api/v1/gradebook/courses/{course.id}/columns/{cid}/post-grades",
            headers=gv_headers,
            json={"scope": "ALL", "send_notification": True},
        )
        assert post_res.status_code == 200

    sv1_visible = await client.get(
        f"/api/v1/gradebook/courses/{course.id}/my-grades",
        headers=sv1_headers,
    )
    assert sv1_visible.status_code == 200
    # 8.5 * 0.4 + 9.0 * 0.6 = 3.4 + 5.4 = 8.8 -> A (4.0)
    assert float(sv1_visible.json()["final_score_10"]) == 8.8
    assert sv1_visible.json()["letter_grade"] == "A"

    # Verify Class Overview Hurdle rule (BR-10): student_hurdle has 10*0.4 + 3.5*0.6 = 6.1 but Final=3.5 < 4.0 -> F
    overview = (
        await client.get(f"/api/v1/gradebook/courses/{course.id}/overview", headers=gv_headers)
    ).json()
    hurdle_row = next(s for s in overview["students"] if s["user_id"] == str(student_hurdle.id))
    assert hurdle_row["hurdle_failed"] is True
    assert hurdle_row["letter_grade"] == "F"
    assert hurdle_row["is_passed"] is False

    # 8. Poka-Yoke Lock: wrong text (E-LOCK-01) -> exact "KHOA DIEM" succeeds
    wrong_lock = await client.post(
        f"/api/v1/gradebook/courses/{course.id}/lock",
        headers=gv_headers,
        json={"confirmation_text": "khoa diem"},
    )
    assert wrong_lock.status_code == 400
    assert wrong_lock.json()["detail"]["code"] == "E-LOCK-01"

    ok_lock = await client.post(
        f"/api/v1/gradebook/courses/{course.id}/lock",
        headers=gv_headers,
        json={"confirmation_text": "KHOA DIEM"},
    )
    assert ok_lock.status_code == 200, ok_lock.text
    assert ok_lock.json()["is_locked"] is True

    # 9. Locked mutation rejected at API layer (423 E-14)
    locked_edit = await client.put(
        f"/api/v1/gradebook/courses/{course.id}/columns/{final_col_id}/grades",
        headers=gv_headers,
        json={"user_id": str(student_pass.id), "official_score": 10.0},
    )
    assert locked_edit.status_code == 423
    assert locked_edit.json()["detail"]["code"] == "E-14"

    # 10. Physical PostgreSQL Trigger blocks raw SQL UPDATE on locked gradebook!
    with pytest.raises(DBAPIError) as exc_info:
        async with session.begin_nested():
            await session.execute(
                text(
                    "UPDATE gradebook.grades SET official_score = 10.0 "
                    "WHERE column_id = :cid AND user_id = :uid"
                ),
                {"cid": uuid.UUID(final_col_id), "uid": student_pass.id},
            )
    assert "GRADEBOOK_IS_PERMANENTLY_LOCKED" in str(exc_info.value)

    # 11. Emergency Unlock Subflow A-1 (Admin only)
    unlock_res = await client.post(
        f"/api/v1/gradebook/courses/{course.id}/emergency-unlock",
        headers=admin_headers,
        json={"decision_code": "QD-2026-099", "reason": "Phuc khao diem theo quyet dinh Phong Dao tao"},
    )
    assert unlock_res.status_code == 200, unlock_res.text
    assert unlock_res.json()["is_locked"] is False
