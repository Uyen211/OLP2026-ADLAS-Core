# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Unit tests for Gradebook Structure (T2-P-M5-01), Muted Policy & Poka-Yoke Lock (T2-P-M5-05)."""

from decimal import Decimal
import uuid
from unittest.mock import AsyncMock
import pytest
from app.modules.gradebook.exceptions import (
    GradebookGroupNotEmptyException,
    GradebookHasMutedColumnsException,
    GradebookLockedException,
    GradebookPokaYokeInvalidException,
    GradebookSumInvalidException,
)
from app.modules.gradebook.models import (
    CourseGradebookLock,
    GradebookColumn,
    GradebookGroup,
    GradeEntry,
)
from app.modules.gradebook.schemas import (
    EmergencyUnlockRequest,
    GradebookLockRequest,
    GradebookStructureSaveRequest,
    GradeGroupInput,
    PostGradesRequest,
)
from app.modules.gradebook.sealing_service import GradebookSealingService
from app.modules.gradebook.structure_service import GradebookStructureService


def _make_mock_repo():
    repo = AsyncMock()
    repo.is_course_locked.return_value = False
    repo.get_course_lock.return_value = None
    repo.list_groups_with_columns.return_value = []
    repo.list_columns_by_course.return_value = []
    repo.list_grades_for_student.return_value = []
    repo.count_grades_in_group.return_value = 0
    repo.count_graded_entries_in_column.return_value = 5
    repo.get_user_display_name.return_value = "TS. Nguyen Minh Tuan"
    return repo


@pytest.mark.asyncio
async def test_save_structure_invalid_sum_raises_e11():
    db = AsyncMock()
    repo = _make_mock_repo()
    svc = GradebookStructureService(db, repo)

    payload = GradebookStructureSaveRequest(
        groups=[
            GradeGroupInput(group_name="Chuyen can", weight_percent=20),
            GradeGroupInput(group_name="Cuoi ky", weight_percent=60),
        ]
    )
    with pytest.raises(GradebookSumInvalidException) as exc:
        await svc.save_structure(uuid.uuid4(), payload, uuid.uuid4())
    assert exc.value.detail["code"] == "E-11"


@pytest.mark.asyncio
async def test_save_structure_when_locked_raises_e14():
    db = AsyncMock()
    repo = _make_mock_repo()
    repo.is_course_locked.return_value = True
    svc = GradebookStructureService(db, repo)

    payload = GradebookStructureSaveRequest(
        groups=[GradeGroupInput(group_name="Tong", weight_percent=100)]
    )
    with pytest.raises(GradebookLockedException) as exc:
        await svc.save_structure(uuid.uuid4(), payload, uuid.uuid4())
    assert exc.value.detail["code"] == "E-14"


@pytest.mark.asyncio
async def test_delete_group_with_data_requires_xoa_e_gb_01():
    db = AsyncMock()
    repo = _make_mock_repo()
    course_id = uuid.uuid4()
    group_id = uuid.uuid4()
    repo.get_group_by_id.return_value = GradebookGroup(
        id=group_id, course_id=course_id, group_name="Bai tap", weight_percent=30
    )
    repo.count_grades_in_group.return_value = 12
    svc = GradebookStructureService(db, repo)

    with pytest.raises(GradebookGroupNotEmptyException) as exc:
        await svc.delete_group(course_id, group_id, confirmation_text="ok", actor_id=uuid.uuid4())
    assert exc.value.detail["code"] == "E-GB-01"

    await svc.delete_group(course_id, group_id, confirmation_text="XOA", actor_id=uuid.uuid4())
    repo.delete_group.assert_awaited_once()


@pytest.mark.asyncio
async def test_student_my_grades_withholds_muted_columns_br09():
    db = AsyncMock()
    repo = _make_mock_repo()
    course_id = uuid.uuid4()
    student_id = uuid.uuid4()
    g1 = GradebookGroup(id=uuid.uuid4(), course_id=course_id, group_name="Do an", weight_percent=100, is_hurdle=False)
    col_muted = GradebookColumn(
        id=uuid.uuid4(), course_id=course_id, group_id=g1.id, item_type="ASSIGNMENT", title="Do an 1", max_points=Decimal("10.0"), is_muted=True
    )
    col_pub = GradebookColumn(
        id=uuid.uuid4(), course_id=course_id, group_id=g1.id, item_type="ASSIGNMENT", title="Do an 2", max_points=Decimal("10.0"), is_muted=False
    )
    g1.columns = [col_muted, col_pub]
    repo.list_groups_with_columns.return_value = [g1]
    repo.list_grades_for_student.return_value = [
        GradeEntry(column_id=col_muted.id, user_id=student_id, official_score=Decimal("9.5"), instructor_feedback="Secret"),
        GradeEntry(column_id=col_pub.id, user_id=student_id, official_score=Decimal("8.0"), instructor_feedback="Good"),
    ]

    svc = GradebookStructureService(db, repo)
    res = await svc.get_student_my_grades(course_id, student_id)
    by_title = {item.title: item for item in res.items}
    assert by_title["Do an 1"].is_muted is True
    assert by_title["Do an 1"].official_score is None
    assert by_title["Do an 1"].instructor_feedback is None
    assert by_title["Do an 2"].official_score == Decimal("8.0")
    assert by_title["Do an 2"].instructor_feedback == "Good"


@pytest.mark.asyncio
async def test_poka_yoke_lock_validation_and_success():
    db = AsyncMock()
    repo = _make_mock_repo()
    course_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    svc = GradebookSealingService(db, repo)

    # Wrong phrase (lowercase) -> E-LOCK-01
    with pytest.raises(GradebookPokaYokeInvalidException) as exc_phrase:
        await svc.lock_course_gradebook(course_id, GradebookLockRequest(confirmation_text="khoa diem"), actor_id)
    assert exc_phrase.value.detail["code"] == "E-LOCK-01"

    # Muted column still present -> E-GB-06
    repo.list_columns_by_course.return_value = [
        GradebookColumn(id=uuid.uuid4(), course_id=course_id, group_id=uuid.uuid4(), item_type="ASSIGNMENT", title="Do an giua ky", is_muted=True)
    ]
    with pytest.raises(GradebookHasMutedColumnsException) as exc_muted:
        await svc.lock_course_gradebook(course_id, GradebookLockRequest(confirmation_text="KHOA DIEM"), actor_id)
    assert exc_muted.value.detail["code"] == "E-GB-06"

    # All unmuted -> lock succeeds
    repo.list_columns_by_course.return_value = [
        GradebookColumn(id=uuid.uuid4(), course_id=course_id, group_id=uuid.uuid4(), item_type="ASSIGNMENT", title="Do an giua ky", is_muted=False)
    ]
    locked = await svc.lock_course_gradebook(course_id, GradebookLockRequest(confirmation_text="KHOA DIEM"), actor_id)
    assert locked.is_locked is True
    repo.save_course_lock.assert_awaited_once()
    repo.emit_outbox_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_post_grades_unmutes_and_queues_outbox():
    db = AsyncMock()
    repo = _make_mock_repo()
    course_id = uuid.uuid4()
    col_id = uuid.uuid4()
    col = GradebookColumn(id=col_id, course_id=course_id, group_id=uuid.uuid4(), item_type="ASSIGNMENT", title="Lab 1", is_muted=True)
    repo.get_column_by_id.return_value = col

    svc = GradebookSealingService(db, repo)
    res = await svc.post_column_grades(course_id, col_id, PostGradesRequest(send_notification=True), uuid.uuid4())
    assert res.is_muted is False
    assert res.notification_queued is True
    assert col.is_muted is False
    repo.emit_outbox_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_emergency_unlock_subflow_a1():
    db = AsyncMock()
    repo = _make_mock_repo()
    course_id = uuid.uuid4()
    lock = CourseGradebookLock(course_id=course_id, is_locked=True)
    repo.get_course_lock.return_value = lock

    svc = GradebookSealingService(db, repo)
    res = await svc.emergency_unlock_gradebook(
        course_id,
        EmergencyUnlockRequest(
            decision_code="QD-2026-11",
            reason="Mo khoa khan cap theo cong van phuc khao chinh thuc cua Ban Chu nhiem Khoa.",
        ),
        uuid.uuid4(),
    )
    assert res.is_locked is False
    assert lock.unlock_decision_code == "QD-2026-11"
