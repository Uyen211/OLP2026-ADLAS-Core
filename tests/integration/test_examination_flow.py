# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""End-to-end integration tests for Module 4 (Examination) against real PostgreSQL."""

from datetime import date, datetime, timedelta, timezone
import os
import uuid
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.modules.course.enums import ContextualRole, EnrollmentStatus
from app.modules.course.models import Course, CourseEnrollment, LearningObjective
from app.modules.examination.models import QuizQuestion
from app.modules.identity.service import default_ip_rate_limiter
from app.modules.system.models import OutboxEvent, User


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
async def exam_client():
    """
    Yield `(client, session)` bound to real PostgreSQL wrapped in an outer transaction
    that rolls back completely after each test.
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
    password: str = "ExamPass@2026!",
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
    token = res.json()["access_token"]
    return f"Bearer {token}"


@pytest.mark.asyncio
async def test_full_examination_lifecycle_snapshot_autosave_resume_and_class_regrade(exam_client):
    client, session = exam_client
    suffix = uuid.uuid4().hex[:8]

    # 1. Seed Instructor, 2 Students, Course, LO, and Enrollments
    instructor = await _create_user(
        session,
        email=f"gv_exam_{suffix}@adlas.edu.vn",
        user_code=f"GV{suffix}",
        full_name="Giang Vien Khao Thi",
    )
    sv1 = await _create_user(
        session,
        email=f"sv1_exam_{suffix}@adlas.edu.vn",
        user_code=f"SV1{suffix}",
        full_name="Sinh Vien Mot",
    )
    sv2 = await _create_user(
        session,
        email=f"sv2_exam_{suffix}@adlas.edu.vn",
        user_code=f"SV2{suffix}",
        full_name="Sinh Vien Hai",
    )

    course = Course(
        id=uuid.uuid4(),
        course_code=f"CS{suffix[:6].upper()}",
        section_code="01",
        name="Cau truc du lieu va Giai thuat",
        semester="HK1-2026",
        credits=3,
        start_date=date(2026, 9, 1),
        end_date=date(2026, 12, 30),
        status="PUBLISHED",
        created_by=instructor.id,
    )
    session.add(course)
    await session.flush()

    lo1 = LearningObjective(
        id=uuid.uuid4(),
        course_id=course.id,
        code="LO1",
        description="Phan tich do phuc tap thuat toan va cau truc du lieu co ban",
        bloom_level="UNDERSTAND",
        order_index=1,
    )
    session.add(lo1)
    session.add_all(
        [
            CourseEnrollment(
                course_id=course.id,
                user_id=instructor.id,
                contextual_role=ContextualRole.INSTRUCTOR.value,
                enrollment_status=EnrollmentStatus.ACTIVE.value,
            ),
            CourseEnrollment(
                course_id=course.id,
                user_id=sv1.id,
                contextual_role=ContextualRole.STUDENT.value,
                enrollment_status=EnrollmentStatus.ACTIVE.value,
            ),
            CourseEnrollment(
                course_id=course.id,
                user_id=sv2.id,
                contextual_role=ContextualRole.STUDENT.value,
                enrollment_status=EnrollmentStatus.ACTIVE.value,
            ),
        ]
    )
    await session.flush()

    gv_headers = {"Authorization": await _login_bearer(client, instructor.email, "ExamPass@2026!")}
    sv1_headers = {"Authorization": await _login_bearer(client, sv1.email, "ExamPass@2026!")}
    sv2_headers = {"Authorization": await _login_bearer(client, sv2.email, "ExamPass@2026!")}

    # 2. Create Question Bank & 2 Questions (Q1 Single-Choice tagged LO1, Q2 Multi-Select)
    bank_res = await client.post(
        f"/api/v1/examinations/courses/{course.id}/question-banks",
        headers=gv_headers,
        json={"category_name": "Chuong 1: Do phuc tap thuat toan"},
    )
    assert bank_res.status_code == 201, bank_res.text
    bank_id = bank_res.json()["id"]

    q1_res = await client.post(
        f"/api/v1/examinations/courses/{course.id}/questions",
        headers=gv_headers,
        json={
            "bank_id": bank_id,
            "lo_id": str(lo1.id),
            "bloom_level": "UNDERSTAND",
            "question_text": "Do phuc tap cua tim kiem nhi phan la gi?",
            "question_type": "MULTIPLE_CHOICE",
            "default_points": "1.00",
            "options": [
                {"id": "q1_o1", "key": "A", "text": "O(n)", "is_correct": True},
                {"id": "q1_o2", "key": "B", "text": "O(log n)", "is_correct": False},
                {"id": "q1_o3", "key": "C", "text": "O(n^2)", "is_correct": False},
                {"id": "q1_o4", "key": "D", "text": "O(1)", "is_correct": False},
            ],
            "explanation": "Luu y: co tinh dat sai dap an goc la O(n) de test phuc khao toan lop.",
        },
    )
    assert q1_res.status_code == 201, q1_res.text
    q1_id = q1_res.json()["id"]

    q2_res = await client.post(
        f"/api/v1/examinations/courses/{course.id}/questions",
        headers=gv_headers,
        json={
            "bank_id": bank_id,
            "bloom_level": "APPLY",
            "question_text": "Chon cac cau truc du lieu tuyen tinh:",
            "question_type": "MULTI_SELECT",
            "default_points": "1.00",
            "options": [
                {"id": "q2_o1", "key": "A", "text": "Stack", "is_correct": True},
                {"id": "q2_o2", "key": "B", "text": "Queue", "is_correct": True},
                {"id": "q2_o3", "key": "C", "text": "Graph", "is_correct": False},
                {"id": "q2_o4", "key": "D", "text": "Binary Tree", "is_correct": False},
            ],
            "explanation": "Stack va Queue la cau truc du lieu tuyen tinh.",
        },
    )
    assert q2_res.status_code == 201, q2_res.text

    # 3. Verify BR-LO-01: LO1 cannot be deleted while referenced by Q1
    del_lo_res = await client.delete(
        f"/api/v1/courses/{course.id}/learning-objectives/{lo1.id}",
        headers=gv_headers,
    )
    assert del_lo_res.status_code == 409, del_lo_res.text
    assert del_lo_res.json()["detail"]["code"] == "E-LO-IN-USE"

    # 4. Create Quiz with Matrix Snapshot & MANUAL grade release + Passcode, then Publish
    now = datetime.now(timezone.utc)
    quiz_res = await client.post(
        f"/api/v1/examinations/courses/{course.id}/quizzes",
        headers=gv_headers,
        json={
            "title": "Kiem tra giua ky CTDL",
            "time_limit_mins": 30,
            "available_from": (now - timedelta(minutes=5)).isoformat(),
            "available_until": (now + timedelta(hours=2)).isoformat(),
            "passcode": "LAB202",
            "grade_release_policy": "MANUAL",
            "security_mode": "CONTROLLED",
            "max_attempts": 1,
            "shuffle_questions": True,
            "shuffle_options": True,
            "matrix_config": [
                {"bank_id": bank_id, "bloom_level": "UNDERSTAND", "count": 1},
                {"bank_id": bank_id, "bloom_level": "APPLY", "count": 1},
            ],
        },
    )
    assert quiz_res.status_code == 201, quiz_res.text
    quiz_id = quiz_res.json()["id"]
    assert quiz_res.json()["question_count"] == 2

    pub_res = await client.post(
        f"/api/v1/examinations/quizzes/{quiz_id}/publish",
        headers=gv_headers,
    )
    assert pub_res.status_code == 200, pub_res.text
    assert pub_res.json()["status"] == "PUBLISHED"

    # 5. Mutate & Soft-Delete Q1 in bank -> Verify Tier-1 Snapshot Immutability (BR-EXAM-01)
    mut_res = await client.put(
        f"/api/v1/examinations/questions/{q1_id}",
        headers=gv_headers,
        json={"question_text": "CAU HOI DA BI SUA TRONG KHO GOC"},
    )
    assert mut_res.status_code == 200, mut_res.text

    del_q1_res = await client.delete(
        f"/api/v1/examinations/questions/{q1_id}",
        headers=gv_headers,
    )
    assert del_q1_res.status_code == 200, del_q1_res.text
    assert del_q1_res.json()["soft_deleted"] is True

    # Verify frozen quiz_questions still retains original text
    quiz_detail_gv = await client.get(
        f"/api/v1/examinations/quizzes/{quiz_id}",
        headers=gv_headers,
    )
    assert quiz_detail_gv.status_code == 200
    snap_texts = [q["question_text_snapshot"] for q in quiz_detail_gv.json()["questions"]]
    assert "Do phuc tap cua tim kiem nhi phan la gi?" in snap_texts

    # 6. Student 1 enters wrong passcode -> 403 E-SEC-02; then correct passcode -> Start Attempt
    bad_pass = await client.post(
        f"/api/v1/examinations/quizzes/{quiz_id}/attempts/start",
        headers=sv1_headers,
        json={"passcode": "WRONG1"},
    )
    assert bad_pass.status_code == 403
    assert bad_pass.json()["detail"]["code"] == "E-SEC-02"

    start_sv1 = await client.post(
        f"/api/v1/examinations/quizzes/{quiz_id}/attempts/start",
        headers=sv1_headers,
        json={"passcode": "LAB202"},
    )
    assert start_sv1.status_code == 200, start_sv1.text
    sv1_data = start_sv1.json()
    sv1_sub_id = sv1_data["submission_id"]
    assert sv1_data["resumed"] is False
    assert len(sv1_data["questions"]) == 2
    # Ensure no answer keys leaked to student
    for q in sv1_data["questions"]:
        assert all("is_correct" not in opt for opt in q["options_snapshot"])

    # Active session endpoint reports AI locked (E-13)
    active_res = await client.get(
        f"/api/v1/examinations/quizzes/{quiz_id}/active-session",
        headers=sv1_headers,
    )
    assert active_res.status_code == 200
    assert active_res.json()["has_active_session"] is True
    assert active_res.json()["is_ai_locked"] is True

    # Find keys for SV1's shuffled options: SV1 picks "O(log n)" (q1_o2) for Q1, and both Stack & Queue for Q2
    sv1_q1 = next(q for q in sv1_data["questions"] if "tim kiem nhi phan" in q["question_text"])
    sv1_q2 = next(q for q in sv1_data["questions"] if "tuyen tinh" in q["question_text"])
    sv1_q1_ologn_key = next(o["key"] for o in sv1_q1["options_snapshot"] if o["id"] == "q1_o2")
    sv1_q2_correct_keys = [
        o["key"] for o in sv1_q2["options_snapshot"] if o["id"] in ("q2_o1", "q2_o2")
    ]

    # 7. Autosave with seq_num=2, then stale seq_num=1 (rejected without overwriting)
    auto_new = await client.post(
        f"/api/v1/examinations/attempts/{sv1_sub_id}/autosave",
        headers=sv1_headers,
        json={
            "seq_num": 2,
            "answers": {
                sv1_q1["id"]: sv1_q1_ologn_key,
                sv1_q2["id"]: sv1_q2_correct_keys,
            },
            "flagged_questions": [sv1_q1["id"]],
            "fullscreen_exit_delta": 1,
            "violation_event": {"type": "FULLSCREEN_EXIT", "ts": now.isoformat()},
        },
    )
    assert auto_new.status_code == 200, auto_new.text
    assert auto_new.json()["accepted"] is True
    assert auto_new.json()["seq_num"] == 2
    assert auto_new.json()["fullscreen_exit_count"] == 1

    auto_stale = await client.post(
        f"/api/v1/examinations/attempts/{sv1_sub_id}/autosave",
        headers=sv1_headers,
        json={
            "seq_num": 1,
            "answers": {},
        },
    )
    assert auto_stale.status_code == 200
    assert auto_stale.json()["accepted"] is False
    assert auto_stale.json()["seq_num"] == 2

    # 8. Idempotent Resume Exam for SV1
    resume_sv1 = await client.post(
        f"/api/v1/examinations/quizzes/{quiz_id}/attempts/start",
        headers=sv1_headers,
        json={"passcode": "LAB202"},
    )
    assert resume_sv1.status_code == 200
    assert resume_sv1.json()["resumed"] is True
    assert resume_sv1.json()["submission_id"] == sv1_sub_id
    assert resume_sv1.json()["seq_num"] == 2
    assert resume_sv1.json()["student_answers"][sv1_q1["id"]] == sv1_q1_ologn_key

    # 9. SV1 submits & SV2 takes and submits (SV2 also picks O(log n) for Q1, wrong for Q2)
    sub_sv1 = await client.post(
        f"/api/v1/examinations/attempts/{sv1_sub_id}/submit",
        headers=sv1_headers,
    )
    assert sub_sv1.status_code == 200, sub_sv1.text
    # MANUAL policy before publish-grades -> score hidden!
    assert sub_sv1.json()["grades_visible"] is False
    assert sub_sv1.json()["final_score"] is None

    start_sv2 = await client.post(
        f"/api/v1/examinations/quizzes/{quiz_id}/attempts/start",
        headers=sv2_headers,
        json={"passcode": "LAB202"},
    )
    assert start_sv2.status_code == 200
    sv2_data = start_sv2.json()
    sv2_sub_id = sv2_data["submission_id"]
    sv2_q1 = next(q for q in sv2_data["questions"] if "tim kiem nhi phan" in q["question_text"])
    sv2_q2 = next(q for q in sv2_data["questions"] if "tuyen tinh" in q["question_text"])
    sv2_q1_ologn_key = next(o["key"] for o in sv2_q1["options_snapshot"] if o["id"] == "q1_o2")
    sv2_q2_wrong_key = next(o["key"] for o in sv2_q2["options_snapshot"] if o["id"] == "q2_o3")

    sub_sv2 = await client.post(
        f"/api/v1/examinations/attempts/{sv2_sub_id}/submit",
        headers=sv2_headers,
        json={
            "answers": {
                sv2_q1["id"]: sv2_q1_ologn_key,
                sv2_q2["id"]: [sv2_q2_wrong_key],
            }
        },
    )
    assert sub_sv2.status_code == 200, sub_sv2.text

    # Before publish-grades, GET /result hides scores
    res_hidden = await client.get(
        f"/api/v1/examinations/attempts/{sv1_sub_id}/result",
        headers=sv1_headers,
    )
    assert res_hidden.status_code == 200
    assert res_hidden.json()["grades_visible"] is False
    assert res_hidden.json()["final_score"] is None
    assert res_hidden.json()["questions"] == []

    # 10. Instructor publishes grades -> scores become visible (SV1=5.0, SV2=0.0 initially)
    pub_grades = await client.post(
        f"/api/v1/examinations/quizzes/{quiz_id}/publish-grades",
        headers=gv_headers,
    )
    assert pub_grades.status_code == 200, pub_grades.text

    res_sv1_before = await client.get(
        f"/api/v1/examinations/attempts/{sv1_sub_id}/result",
        headers=sv1_headers,
    )
    assert res_sv1_before.status_code == 200
    assert res_sv1_before.json()["grades_visible"] is True
    assert res_sv1_before.json()["can_request_regrade"] is True
    assert float(res_sv1_before.json()["final_score"]) == 5.0

    # 11. Both SV1 and SV2 file 48h regrade requests on Q1
    reg1_res = await client.post(
        f"/api/v1/examinations/attempts/{sv1_sub_id}/regrades",
        headers=sv1_headers,
        json={
            "attempt_question_id": sv1_q1["id"],
            "student_reason": "Tim kiem nhi phan co do phuc tap O(log n), dap an goc O(n) bi nham lan.",
        },
    )
    assert reg1_res.status_code == 201, reg1_res.text
    reg1_id = reg1_res.json()["id"]

    reg2_res = await client.post(
        f"/api/v1/examinations/attempts/{sv2_sub_id}/regrades",
        headers=sv2_headers,
        json={
            "attempt_question_id": sv2_q1["id"],
            "student_reason": "Em cung chon O(log n) cho cau tim kiem nhi phan, de nghi cham lai.",
        },
    )
    assert reg2_res.status_code == 201, reg2_res.text

    # 12. Instructor approves SV1's regrade with ENTIRE_CLASS fixing Q1's key to q1_o2
    review_res = await client.post(
        f"/api/v1/examinations/regrades/{reg1_id}/review",
        headers=gv_headers,
        json={
            "approved": True,
            "regrade_scope": "ENTIRE_CLASS",
            "correct_option_ids": ["q1_o2"],
            "reviewer_feedback": "Xac nhan dap an chuan la O(log n), da cham lai toan lop.",
        },
    )
    assert review_res.status_code == 200, review_res.text
    review_data = review_res.json()
    assert review_data["affected_submissions_count"] == 2
    assert review_data["closed_pending_regrades_count"] == 1
    assert float(review_data["regrade"]["new_score"]) == 10.0

    # Verify SV1 now has 10.0 and SV2 now has 5.0!
    res_sv1_after = await client.get(
        f"/api/v1/examinations/attempts/{sv1_sub_id}/result",
        headers=sv1_headers,
    )
    res_sv2_after = await client.get(
        f"/api/v1/examinations/attempts/{sv2_sub_id}/result",
        headers=sv2_headers,
    )
    assert float(res_sv1_after.json()["final_score"]) == 10.0
    assert float(res_sv2_after.json()["final_score"]) == 5.0
    assert res_sv2_after.json()["regrades"][0]["status"] == "APPROVED"

    # Verify Tier-1 quiz_questions was updated to q1_o2
    t1_rows = (
        await session.execute(
            select(QuizQuestion).where(QuizQuestion.quiz_id == uuid.UUID(quiz_id))
        )
    ).scalars().all()
    t1_q1 = next(r for r in t1_rows if "tim kiem nhi phan" in r.question_text_snapshot)
    correct_ids = [o["id"] for o in t1_q1.options_snapshot if o["is_correct"]]
    assert correct_ids == ["q1_o2"]

    # Verify Outbox Events (2x examination.quiz_completed + 1x examination.quiz_regraded)
    outbox_rows = (
        await session.execute(
            select(OutboxEvent).where(
                OutboxEvent.event_type.in_(
                    ["examination.quiz_completed", "examination.quiz_regraded"]
                )
            )
        )
    ).scalars().all()
    completed_events = [
        e for e in outbox_rows
        if e.event_type == "examination.quiz_completed"
        and e.payload.get("quiz_id") == quiz_id
    ]
    regraded_events = [
        e for e in outbox_rows
        if e.event_type == "examination.quiz_regraded"
        and e.payload.get("quiz_id") == quiz_id
    ]
    assert len(completed_events) == 2
    assert all(
        "user_id" in e.payload
        and "final_score" in e.payload
        and any(o.get("lo_id") == str(lo1.id) for o in e.payload.get("question_outcomes", []))
        for e in completed_events
    )
    assert len(regraded_events) == 1
    assert regraded_events[0].payload["regrade_scope"] == "ENTIRE_CLASS"
    affected_regrade = regraded_events[0].payload["affected_submissions"]
    assert len(affected_regrade) == 2
    assert all(
        "user_id" in item
        and "new_score" in item
        and any(
            o.get("lo_id") == str(lo1.id) and o.get("is_correct") is True
            for o in item.get("question_outcomes", [])
        )
        for item in affected_regrade
    )
