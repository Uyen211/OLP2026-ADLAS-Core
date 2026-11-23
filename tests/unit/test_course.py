# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Unit tests for Course Lifecycle, LOs, BR-03 Clone, Join Code, Roster, and Grouping."""

import io
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import uuid

import openpyxl
from pydantic import ValidationError
import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.course.enums import (
    BloomLevel,
    ContextualRole,
    CourseStatus,
    EnrollmentStatus,
    RosterRowStatus,
)
from app.modules.course.exceptions import (
    DuplicateResourceException,
    InvalidCourseStateException,
    JoinCodeInvalidException,
    LoInUseException,
    RosterFormatException,
)
from app.modules.course.grouping import (
    partition_students_random,
    validate_group_set_members,
)
from app.modules.course.join_code import (
    JOIN_CODE_ALPHABET,
    JOIN_CODE_LENGTH,
    generate_join_code,
    is_valid_join_code,
)
from app.modules.course.lifecycle import assert_transition, can_transition
from app.modules.course.lo_references import LoReferenceRegistry
from app.modules.course.models import Course, CourseEnrollment, LearningObjective
from app.modules.course.roster_ingestion import normalize_header, parse_roster_bytes
from app.modules.course.schemas import CourseCloneRequest, CourseCreate, LOCreate
from app.modules.course.service import (
    CourseService,
    GroupService,
    LearningObjectiveService,
    RosterService,
)
from app.modules.system.models import User


def _make_actor(role: str = "USER") -> User:
    return User(
        id=uuid.uuid4(),
        email="gv@adlas.edu.vn",
        user_code="GV001",
        full_name="Giang Vien",
        password_hash="hashed",
        system_role=role,
        is_active=True,
    )


def _make_course(
    *,
    is_template: bool = False,
    status: CourseStatus = CourseStatus.UNPUBLISHED,
    is_enrollment_open: bool = True,
    join_code: str | None = "ABC234",
    created_by: uuid.UUID | None = None,
) -> Course:
    now = datetime.now(timezone.utc)
    return Course(
        id=uuid.uuid4(),
        course_code="CS101",
        section_code="N01",
        name="Nhap mon Lap trinh",
        semester="HK1-2026",
        credits=3,
        grading_scheme="SCALE_10",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 12, 20),
        syllabus_text="<p>Noi dung de cuong</p>",
        join_code=join_code,
        is_enrollment_open=is_enrollment_open,
        is_template=is_template,
        status=status.value,
        created_by=created_by or uuid.uuid4(),
        created_at=now,
        updated_at=now,
    )


def _build_xlsx_bytes(rows: list[list[object]]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    wb.close()
    return buf.getvalue()


def test_course_create_rejects_end_date_less_than_7_days():
    """E-2: Course end_date must be at least 7 days after start_date."""
    with pytest.raises(ValidationError):
        CourseCreate(
            course_code="CS101",
            section_code="N01",
            name="Nhap mon Lap trinh",
            semester="HK1-2026",
            credits=3,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 5),
        )


def test_course_code_must_be_uppercase():
    """E-2: Course code must match uppercase pattern ^[A-Z0-9_-]{2,30}$."""
    with pytest.raises(ValidationError):
        CourseCreate(
            course_code="cs101",
            section_code="N01",
            name="Nhap mon Lap trinh",
            semester="HK1-2026",
            credits=3,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 1),
        )


@pytest.mark.asyncio
async def test_duplicate_course_section_semester_maps_to_e4():
    """E-4: Unique constraint violation on (course_code, section_code, semester) maps to 409 E-4."""
    mock_db = AsyncMock()
    actor = _make_actor(role="ADMIN")

    repo = MagicMock()
    repo.join_code_exists = AsyncMock(return_value=False)
    repo.create_course = AsyncMock(side_effect=IntegrityError("stmt", "params", Exception("uq")))

    service = CourseService(db=mock_db, repo=repo)
    payload = CourseCreate(
        course_code="CS101",
        section_code="N01",
        name="Nhap mon Lap trinh",
        semester="HK1-2026",
        credits=3,
        start_date=date(2026, 9, 1),
        end_date=date(2026, 12, 1),
    )

    with pytest.raises(DuplicateResourceException) as exc_info:
        await service.create_course(payload, actor)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "E-4"


@pytest.mark.asyncio
async def test_duplicate_lo_code_maps_to_e4():
    """E-4: Duplicate LO code within the same course maps to 409 E-4."""
    mock_db = AsyncMock()
    actor = _make_actor(role="ADMIN")
    course = _make_course(created_by=actor.id)

    repo = MagicMock()
    repo.get_course_by_id = AsyncMock(return_value=course)
    repo.list_los = AsyncMock(return_value=[])
    repo.create_lo = AsyncMock(side_effect=IntegrityError("stmt", "params", Exception("uq_lo")))

    service = LearningObjectiveService(db=mock_db, repo=repo)
    payload = LOCreate(
        code="LO-01",
        description="Hieu va ap dung duoc cau truc du lieu co ban",
        bloom_level=BloomLevel.APPLY,
    )

    with pytest.raises(DuplicateResourceException) as exc_info:
        await service.create_lo(course.id, payload, actor)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "E-4"
    assert exc_info.value.detail["field"] == "code"


@pytest.mark.parametrize(
    ("current", "target", "allowed"),
    [
        (CourseStatus.UNPUBLISHED, CourseStatus.PUBLISHED, True),
        (CourseStatus.UNPUBLISHED, CourseStatus.ENROLLMENT_CLOSED, False),
        (CourseStatus.UNPUBLISHED, CourseStatus.ARCHIVED, False),
        (CourseStatus.PUBLISHED, CourseStatus.ENROLLMENT_CLOSED, True),
        (CourseStatus.PUBLISHED, CourseStatus.ARCHIVED, True),
        (CourseStatus.PUBLISHED, CourseStatus.UNPUBLISHED, False),
        (CourseStatus.ENROLLMENT_CLOSED, CourseStatus.PUBLISHED, True),
        (CourseStatus.ENROLLMENT_CLOSED, CourseStatus.ARCHIVED, True),
        (CourseStatus.ENROLLMENT_CLOSED, CourseStatus.UNPUBLISHED, False),
        (CourseStatus.ARCHIVED, CourseStatus.PUBLISHED, False),
        (CourseStatus.ARCHIVED, CourseStatus.ENROLLMENT_CLOSED, False),
        (CourseStatus.ARCHIVED, CourseStatus.UNPUBLISHED, False),
    ],
)
def test_lifecycle_allowed_and_forbidden_transitions(
    current: CourseStatus,
    target: CourseStatus,
    allowed: bool,
):
    """Verify pure FSM lifecycle transition matrix."""
    assert can_transition(current, target) is allowed
    if not allowed:
        with pytest.raises(InvalidCourseStateException) as exc_info:
            assert_transition(current, target)
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail["code"] == "E-COURSE-STATE"


@pytest.mark.asyncio
async def test_clone_copies_syllabus_and_los_only():
    """BR-03: Cloning copies syllabus metadata and LOs accurately."""
    mock_db = AsyncMock()
    actor = _make_actor(role="ADMIN")
    template = _make_course(is_template=True, join_code=None, created_by=actor.id)
    now = datetime.now(timezone.utc)
    template_los = [
        LearningObjective(
            id=uuid.uuid4(),
            course_id=template.id,
            code="LO-01",
            description="Trinh bay khai niem co ban ve thuat toan",
            bloom_level=BloomLevel.UNDERSTAND.value,
            order_index=1,
            created_at=now,
            updated_at=now,
        ),
        LearningObjective(
            id=uuid.uuid4(),
            course_id=template.id,
            code="LO-02",
            description="Van dung cau truc du lieu giai quyet bai toan",
            bloom_level=BloomLevel.APPLY.value,
            order_index=2,
            created_at=now,
            updated_at=now,
        ),
    ]

    created_courses: list[Course] = []
    created_los: list[LearningObjective] = []

    async def fake_create_course(c: Course) -> Course:
        c.id = uuid.uuid4()
        c.created_at = now
        c.updated_at = now
        created_courses.append(c)
        return c

    async def fake_create_lo(lo: LearningObjective) -> LearningObjective:
        lo.id = uuid.uuid4()
        lo.created_at = now
        lo.updated_at = now
        created_los.append(lo)
        return lo

    repo = MagicMock()
    repo.get_course_by_id = AsyncMock(return_value=template)
    repo.join_code_exists = AsyncMock(return_value=False)
    repo.create_course = AsyncMock(side_effect=fake_create_course)
    repo.create_enrollment = AsyncMock()
    repo.list_los = AsyncMock(return_value=template_los)
    repo.create_lo = AsyncMock(side_effect=fake_create_lo)

    service = CourseService(db=mock_db, repo=repo)
    detail = await service.clone_from_template(
        CourseCloneRequest(
            template_id=template.id,
            section_code="N99",
            semester="HK2-2026",
            start_date=date(2027, 1, 10),
            end_date=date(2027, 5, 10),
        ),
        actor,
    )

    assert detail.syllabus_text == template.syllabus_text
    assert detail.credits == template.credits
    assert detail.name == template.name
    assert len(detail.learning_objectives) == 2
    assert [lo.code for lo in detail.learning_objectives] == ["LO-01", "LO-02"]


@pytest.mark.asyncio
async def test_clone_never_touches_enrollments_or_groups():
    """BR-03: Cloning never copies student enrollments or project groups from template."""
    mock_db = AsyncMock()
    actor = _make_actor(role="ADMIN")
    template = _make_course(is_template=True, join_code=None, created_by=actor.id)
    now = datetime.now(timezone.utc)

    enrollments_created: list[CourseEnrollment] = []

    async def fake_create_course(c: Course) -> Course:
        c.id = uuid.uuid4()
        c.created_at = now
        c.updated_at = now
        return c

    async def fake_create_enrollment(e: CourseEnrollment) -> CourseEnrollment:
        enrollments_created.append(e)
        return e

    repo = MagicMock()
    repo.get_course_by_id = AsyncMock(return_value=template)
    repo.join_code_exists = AsyncMock(return_value=False)
    repo.create_course = AsyncMock(side_effect=fake_create_course)
    repo.create_enrollment = AsyncMock(side_effect=fake_create_enrollment)
    repo.list_los = AsyncMock(return_value=[])
    repo.replace_group_set = AsyncMock()
    repo.add_group_member = AsyncMock()

    service = CourseService(db=mock_db, repo=repo)
    detail = await service.clone_from_template(
        CourseCloneRequest(
            template_id=template.id,
            section_code="N02",
            semester="HK2-2026",
            start_date=date(2027, 1, 10),
            end_date=date(2027, 5, 10),
        ),
        actor,
    )

    assert detail.student_count == 0
    assert len(enrollments_created) == 1
    assert enrollments_created[0].user_id == actor.id
    assert enrollments_created[0].contextual_role == ContextualRole.INSTRUCTOR.value
    repo.replace_group_set.assert_not_called()
    repo.add_group_member.assert_not_called()


@pytest.mark.asyncio
async def test_clone_generates_new_join_code_and_clears_template_flag():
    """BR-03: Cloned course has is_template=False and a fresh valid 6-char join_code."""
    mock_db = AsyncMock()
    actor = _make_actor(role="ADMIN")
    template = _make_course(is_template=True, join_code="OLD234", created_by=actor.id)
    now = datetime.now(timezone.utc)

    async def fake_create_course(c: Course) -> Course:
        c.id = uuid.uuid4()
        c.created_at = now
        c.updated_at = now
        return c

    repo = MagicMock()
    repo.get_course_by_id = AsyncMock(return_value=template)
    repo.join_code_exists = AsyncMock(return_value=False)
    repo.create_course = AsyncMock(side_effect=fake_create_course)
    repo.create_enrollment = AsyncMock()
    repo.list_los = AsyncMock(return_value=[])

    service = CourseService(db=mock_db, repo=repo)
    detail = await service.clone_from_template(
        CourseCloneRequest(
            template_id=template.id,
            section_code="N03",
            semester="HK2-2026",
            start_date=date(2027, 1, 10),
            end_date=date(2027, 5, 10),
        ),
        actor,
    )

    assert detail.is_template is False
    assert detail.join_code is not None
    assert is_valid_join_code(detail.join_code) is True
    assert detail.join_code != template.join_code


@pytest.mark.asyncio
async def test_delete_lo_blocked_when_registered_checker_reports_usage():
    """BR-LO-01: Deleting an LO referenced by another module raises 409 E-LO-IN-USE."""
    mock_db = AsyncMock()
    actor = _make_actor(role="ADMIN")
    course = _make_course(created_by=actor.id)
    now = datetime.now(timezone.utc)
    lo = LearningObjective(
        id=uuid.uuid4(),
        course_id=course.id,
        code="LO-01",
        description="Chuan dau ra dang duoc su dung",
        bloom_level=BloomLevel.APPLY.value,
        order_index=1,
        created_at=now,
        updated_at=now,
    )

    registry = LoReferenceRegistry()

    async def checker(db, lo_id):
        return lo_id == lo.id

    registry.register("assessment", checker)

    repo = MagicMock()
    repo.get_course_by_id = AsyncMock(return_value=course)
    repo.get_lo_by_id = AsyncMock(return_value=lo)
    repo.delete_lo = AsyncMock()

    service = LearningObjectiveService(db=mock_db, repo=repo, ref_registry=registry)
    with pytest.raises(LoInUseException) as exc_info:
        await service.delete_lo(course.id, lo.id, actor)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "E-LO-IN-USE"
    repo.delete_lo.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_lo_allowed_without_references():
    """BR-LO-01: Deleting an unreferenced LO succeeds."""
    mock_db = AsyncMock()
    actor = _make_actor(role="ADMIN")
    course = _make_course(created_by=actor.id)
    now = datetime.now(timezone.utc)
    lo = LearningObjective(
        id=uuid.uuid4(),
        course_id=course.id,
        code="LO-02",
        description="Chuan dau ra chua duoc tham chieu",
        bloom_level=BloomLevel.UNDERSTAND.value,
        order_index=2,
        created_at=now,
        updated_at=now,
    )

    registry = LoReferenceRegistry()

    async def checker(db, lo_id):
        return False

    registry.register("assessment", checker)

    repo = MagicMock()
    repo.get_course_by_id = AsyncMock(return_value=course)
    repo.get_lo_by_id = AsyncMock(return_value=lo)
    repo.delete_lo = AsyncMock()

    service = LearningObjectiveService(db=mock_db, repo=repo, ref_registry=registry)
    await service.delete_lo(course.id, lo.id, actor)
    repo.delete_lo.assert_awaited_once_with(lo)


@pytest.mark.asyncio
async def test_join_code_format_alphabet_and_uniqueness_retry():
    """BR-ROSTER-02: Join code uses 31-char unambiguous alphabet and retries on collision."""
    code = generate_join_code()
    assert len(code) == JOIN_CODE_LENGTH
    assert all(ch in JOIN_CODE_ALPHABET for ch in code)
    for forbidden in ("0", "O", "1", "I", "L"):
        assert forbidden not in JOIN_CODE_ALPHABET

    mock_db = AsyncMock()
    repo = MagicMock()
    repo.join_code_exists = AsyncMock(side_effect=[True, True, False])
    service = CourseService(db=mock_db, repo=repo)

    unique_code = await service._generate_unique_join_code()
    assert is_valid_join_code(unique_code) is True
    assert repo.join_code_exists.await_count == 3


@pytest.mark.asyncio
async def test_join_rejected_when_enrollment_closed_or_unpublished():
    """BR-ROSTER-02: Joining a closed or unpublished course returns 403 E-JOIN-01."""
    mock_db = AsyncMock()
    student = _make_actor()

    closed_course = _make_course(status=CourseStatus.ENROLLMENT_CLOSED, is_enrollment_open=False)
    unpublished_course = _make_course(status=CourseStatus.UNPUBLISHED, is_enrollment_open=True)

    repo = MagicMock()
    service = RosterService(db=mock_db, repo=repo)

    for target_course in (closed_course, unpublished_course):
        repo.get_course_by_join_code = AsyncMock(return_value=target_course)
        with pytest.raises(JoinCodeInvalidException) as exc_info:
            await service.join_by_code(target_course.join_code or "ABC234", student)
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["code"] == "E-JOIN-01"


@pytest.mark.asyncio
async def test_join_is_idempotent_for_existing_member():
    """BR-ROSTER-01: Joining a course where user is already ACTIVE is idempotent."""
    mock_db = AsyncMock()
    student = _make_actor()
    course = _make_course(status=CourseStatus.PUBLISHED, is_enrollment_open=True)
    existing = CourseEnrollment(
        course_id=course.id,
        user_id=student.id,
        contextual_role=ContextualRole.STUDENT.value,
        enrollment_status=EnrollmentStatus.ACTIVE.value,
    )

    repo = MagicMock()
    repo.get_course_by_join_code = AsyncMock(return_value=course)
    repo.get_enrollment = AsyncMock(return_value=existing)
    repo.create_enrollment = AsyncMock()
    repo.count_course_metrics = AsyncMock(return_value=({course.id: 1}, {course.id: 2}))

    service = RosterService(db=mock_db, repo=repo)
    summary = await service.join_by_code(course.join_code or "ABC234", student)

    assert summary.id == course.id
    assert summary.my_role == ContextualRole.STUDENT
    repo.create_enrollment.assert_not_awaited()


def test_roster_missing_required_column_raises_e_roster_01():
    """E-ROSTER-01: Missing required header column raises 422 E-ROSTER-01 with column names."""
    csv_bytes = "MSSV,Ho va ten\nSV001,Nguyen Van A\n".encode("utf-8")
    with pytest.raises(RosterFormatException) as exc_info:
        parse_roster_bytes("roster.csv", csv_bytes)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "E-ROSTER-01"
    assert "Email" in exc_info.value.detail["missing_columns"]


def test_roster_vietnamese_and_english_header_aliases():
    """Header normalization supports both accented Vietnamese and English aliases."""
    assert normalize_header("Mã số sinh viên") == "ma so sinh vien"
    assert normalize_header("Họ và tên") == "ho va ten"
    assert normalize_header("student_code") == "student code"

    vn_csv = "Mã số sinh viên,Họ và tên,Địa chỉ Email\nSV202601,Tran Van A,sv01@adlas.edu.vn\n".encode("utf-8")
    en_csv = "student_code,full_name,email\nSV202601,Tran Van A,sv01@adlas.edu.vn\n".encode("utf-8")

    vn_res = parse_roster_bytes("vn.csv", vn_csv)
    en_res = parse_roster_bytes("en.csv", en_csv)

    assert vn_res.valid_count == 1
    assert en_res.valid_count == 1
    assert vn_res.valid_rows[0].user_code == en_res.valid_rows[0].user_code
    assert vn_res.valid_rows[0].email == en_res.valid_rows[0].email


def test_roster_csv_and_xlsx_equivalent():
    """CSV and XLSX parsers produce identical results for the same roster data."""
    rows = [
        ["MSSV", "Ho va ten", "Email"],
        ["SV001", "Nguyen Van A", "sv001@adlas.edu.vn"],
        ["SV002", "Le Thi B", "sv002@adlas.edu.vn"],
    ]
    csv_bytes = "\n".join(",".join(str(c) for c in r) for r in rows).encode("utf-8")
    xlsx_bytes = _build_xlsx_bytes(rows)

    csv_res = parse_roster_bytes("roster.csv", csv_bytes)
    xlsx_res = parse_roster_bytes("roster.xlsx", xlsx_bytes)

    assert csv_res.total_rows == xlsx_res.total_rows == 2
    assert csv_res.valid_count == xlsx_res.valid_count == 2
    assert [(r.user_code, r.email) for r in csv_res.valid_rows] == [
        (r.user_code, r.email) for r in xlsx_res.valid_rows
    ]


def test_roster_marks_in_course_and_in_file_duplicates():
    """E-ROSTER-02 / BR-ROSTER-01: Marks both existing course duplicates and intra-file duplicates."""
    csv_bytes = (
        "MSSV,Ho va ten,Email\n"
        "SV001,Nguyen Van A,sv001@adlas.edu.vn\n"
        "SV002,Le Thi B,sv002@adlas.edu.vn\n"
        "SV002,Le Thi B,sv002@adlas.edu.vn\n"
    ).encode("utf-8")

    res = parse_roster_bytes(
        "roster.csv",
        csv_bytes,
        existing_course_emails={"sv001@adlas.edu.vn"},
        existing_course_codes={"SV001"},
    )

    assert res.total_rows == 3
    assert res.valid_count == 1
    assert res.duplicate_count == 2
    assert res.preview_rows[0].status == RosterRowStatus.DUPLICATE_IN_COURSE
    assert res.preview_rows[1].status == RosterRowStatus.VALID
    assert res.preview_rows[2].status == RosterRowStatus.DUPLICATE_IN_FILE


def test_roster_preview_returns_first_five_rows_and_counts():
    """Roster preview returns at most 5 preview rows alongside full summary counts."""
    lines = ["MSSV,Ho va ten,Email"]
    for idx in range(1, 13):
        lines.append(f"SV{idx:03d},Sinh Vien {idx},sv{idx:03d}@adlas.edu.vn")
    csv_bytes = "\n".join(lines).encode("utf-8")

    res = parse_roster_bytes("roster12.csv", csv_bytes)
    assert res.total_rows == 12
    assert res.valid_count == 12
    assert len(res.preview_rows) == 5
    assert [r.user_code for r in res.preview_rows] == ["SV001", "SV002", "SV003", "SV004", "SV005"]


def test_partition_40_students_size_4_gives_10_groups_of_4():
    """AC-03: Partitioning 40 students with group_size=4 produces 10 groups of 4."""
    student_ids = [uuid.uuid4() for _ in range(40)]
    groups = partition_students_random(student_ids, group_size=4)

    assert len(groups) == 10
    assert all(len(members) == 4 for _, members in groups)
    flattened = [uid for _, members in groups for uid in members]
    assert set(flattened) == set(student_ids)


@pytest.mark.parametrize("n", [1, 2, 5, 10, 17, 25, 39, 40, 50])
@pytest.mark.parametrize("k", [2, 3, 4, 7, 10])
def test_partition_sizes_differ_by_at_most_one(n: int, k: int):
    """Group sizes across all generated groups differ by at most 1 for n in 1..50, k in 2..10."""
    student_ids = [uuid.uuid4() for _ in range(n)]
    groups = partition_students_random(student_ids, group_size=k)

    sizes = [len(members) for _, members in groups]
    assert sum(sizes) == n
    assert max(sizes) - min(sizes) <= 1


def test_group_set_save_rejects_member_in_two_groups():
    """Group integrity: A student cannot belong to two groups in the same group set."""
    s1, s2 = uuid.uuid4(), uuid.uuid4()
    with pytest.raises(Exception) as exc_info:
        validate_group_set_members(
            [("Nhom 1", [s1]), ("Nhom 2", [s1, s2])],
            active_student_ids={s1, s2},
        )
    assert getattr(exc_info.value, "status_code", None) == 422


@pytest.mark.asyncio
async def test_group_service_save_rejects_member_in_two_groups():
    """GroupService.save_group_set enforces single-group membership per group set."""
    mock_db = AsyncMock()
    actor = _make_actor(role="ADMIN")
    course = _make_course(created_by=actor.id)
    s1 = _make_actor()
    s2 = _make_actor()

    repo = MagicMock()
    repo.get_course_by_id = AsyncMock(return_value=course)
    repo.list_all_active_students = AsyncMock(return_value=[s1, s2])
    repo.replace_group_set = AsyncMock()

    from app.modules.course.schemas import GroupSaveItem, GroupSetSaveRequest

    service = GroupService(db=mock_db, repo=repo)
    payload = GroupSetSaveRequest(
        groups=[
            GroupSaveItem(name="Nhom 1", member_ids=[s1.id]),
            GroupSaveItem(name="Nhom 2", member_ids=[s1.id, s2.id]),
        ]
    )

    with pytest.raises(Exception) as exc_info:
        await service.save_group_set(course.id, "Do an cuoi ky", payload, actor)

    assert getattr(exc_info.value, "status_code", None) == 422
    repo.replace_group_set.assert_not_awaited()
