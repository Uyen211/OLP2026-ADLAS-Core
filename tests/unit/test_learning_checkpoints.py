# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Unit tests for Interactive Checkpoints, Video Spacing, and Strict Completion Gate (T2-P-M2-03)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest
from app.modules.course.enums import ContextualRole
from app.modules.course.public_api import CoursePublicService
from app.modules.learning.enums import MaterialType
from app.modules.learning.exceptions import (
    CheckpointSpacingException,
    UncompletedCheckpointsException,
)
from app.modules.learning.models import (
    LearningMaterial,
    LearningModule,
    MaterialCheckpoint,
    StudentCheckpointAttempt,
)
from app.modules.learning.repository import LearningRepository
from app.modules.learning.schemas import (
    CheckpointCreate,
    CheckpointInstructorResponse,
    CheckpointStudentResponse,
    CheckpointSubmitRequest,
)
from app.modules.learning.service import (
    LearningCheckpointService,
    LearningMaterialService,
)


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def ids():
    return {
        "course_id": uuid.uuid4(),
        "module_id": uuid.uuid4(),
        "material_id": uuid.uuid4(),
        "instructor_id": uuid.uuid4(),
        "student_id": uuid.uuid4(),
    }


def _mock_course_service(role: ContextualRole):
    svc = MagicMock(spec=CoursePublicService)
    svc.assert_course_role = AsyncMock(return_value=role)
    return svc


@pytest.mark.asyncio
async def test_create_video_checkpoint_success(mock_db, ids):
    """Instructor can create a valid video checkpoint."""
    repo = MagicMock(spec=LearningRepository)
    mod = LearningModule(id=ids["module_id"], course_id=ids["course_id"], title="Week 1")
    mat = LearningMaterial(
        id=ids["material_id"],
        module_id=ids["module_id"],
        title="Video Lecture",
        material_type=MaterialType.VIDEO.value,
    )
    repo.get_material = AsyncMock(return_value=mat)
    repo.get_module = AsyncMock(return_value=mod)
    repo.list_checkpoints = AsyncMock(return_value=[])

    async def mock_create(chk):
        chk.id = uuid.uuid4()
        chk.created_at = datetime.now(timezone.utc)
        return chk

    repo.create_checkpoint = AsyncMock(side_effect=mock_create)

    service = LearningCheckpointService(mock_db, repo=repo)
    service.course_service = _mock_course_service(ContextualRole.INSTRUCTOR)

    payload = CheckpointCreate(
        question_text="Khái niệm nào sau đây đúng với REST?",
        stop_time_seconds=10,
        options={"A": "Stateless", "B": "Stateful", "C": "Binary only", "D": "No HTTP"},
        correct_option="a",
        is_blocking=True,
    )
    res = await service.create_checkpoint(ids["course_id"], ids["material_id"], payload, ids["instructor_id"])
    assert isinstance(res, CheckpointInstructorResponse)
    assert res.correct_option == "A"
    assert res.stop_time_seconds == 10
    assert res.time_limit_seconds == 10
    assert res.rewind_seconds == 15


@pytest.mark.asyncio
async def test_checkpoint_spacing_rule_blocks_close_markers(mock_db, ids):
    """Creating two video checkpoints less than 5 seconds apart raises CheckpointSpacingException."""
    repo = MagicMock(spec=LearningRepository)
    mod = LearningModule(id=ids["module_id"], course_id=ids["course_id"], title="Week 1")
    mat = LearningMaterial(
        id=ids["material_id"],
        module_id=ids["module_id"],
        title="Video Lecture",
        material_type=MaterialType.VIDEO.value,
    )
    existing = MaterialCheckpoint(
        id=uuid.uuid4(),
        material_id=ids["material_id"],
        stop_time_seconds=10,
        question_text="Existing",
    )
    repo.get_material = AsyncMock(return_value=mat)
    repo.get_module = AsyncMock(return_value=mod)
    repo.list_checkpoints = AsyncMock(return_value=[existing])

    service = LearningCheckpointService(mock_db, repo=repo)
    service.course_service = _mock_course_service(ContextualRole.INSTRUCTOR)

    payload = CheckpointCreate(
        question_text="Too close question",
        stop_time_seconds=13,
        options={"A": "1", "B": "2", "C": "3", "D": "4"},
        correct_option="A",
    )
    with pytest.raises(CheckpointSpacingException):
        await service.create_checkpoint(ids["course_id"], ids["material_id"], payload, ids["instructor_id"])


@pytest.mark.asyncio
async def test_student_checkpoint_list_hides_correct_option(mock_db, ids):
    """Students receive CheckpointStudentResponse without correct_option and with is_passed status."""
    repo = MagicMock(spec=LearningRepository)
    mod = LearningModule(id=ids["module_id"], course_id=ids["course_id"], title="Week 1")
    mat = LearningMaterial(
        id=ids["material_id"],
        module_id=ids["module_id"],
        title="Video Lecture",
        material_type=MaterialType.VIDEO.value,
    )
    chk_id = uuid.uuid4()
    chk = MaterialCheckpoint(
        id=chk_id,
        material_id=ids["material_id"],
        stop_time_seconds=10,
        question_text="Question 1",
        question_type="MULTIPLE_CHOICE",
        options={"A": "1", "B": "2", "C": "3", "D": "4"},
        correct_option="B",
        is_blocking=True,
        time_limit_seconds=10,
        rewind_seconds=15,
        created_at=datetime.now(timezone.utc),
    )
    repo.get_material = AsyncMock(return_value=mat)
    repo.get_module = AsyncMock(return_value=mod)
    repo.list_checkpoints = AsyncMock(return_value=[chk])
    repo.get_student_attempts_for_checkpoints = AsyncMock(return_value={chk_id: True})

    service = LearningCheckpointService(mock_db, repo=repo)
    service.course_service = _mock_course_service(ContextualRole.STUDENT)

    res = await service.list_checkpoints(ids["course_id"], ids["material_id"], ids["student_id"])
    assert len(res) == 1
    assert isinstance(res[0], CheckpointStudentResponse)
    assert not hasattr(res[0], "correct_option")
    assert res[0].is_passed is True


@pytest.mark.asyncio
async def test_submit_checkpoint_correct_and_wrong(mock_db, ids):
    """Correct answer sets is_passed=True and rewind=0; wrong answer returns rewind_seconds=15."""
    repo = MagicMock(spec=LearningRepository)
    mod = LearningModule(id=ids["module_id"], course_id=ids["course_id"], title="Week 1")
    mat = LearningMaterial(
        id=ids["material_id"],
        module_id=ids["module_id"],
        title="Video Lecture",
        material_type=MaterialType.VIDEO.value,
    )
    chk = MaterialCheckpoint(
        id=uuid.uuid4(),
        material_id=ids["material_id"],
        stop_time_seconds=10,
        question_text="Question 1",
        correct_option="C",
        rewind_seconds=15,
    )
    repo.get_material = AsyncMock(return_value=mat)
    repo.get_module = AsyncMock(return_value=mod)
    repo.get_checkpoint = AsyncMock(return_value=chk)

    service = LearningCheckpointService(mock_db, repo=repo)
    service.course_service = _mock_course_service(ContextualRole.STUDENT)

    # Wrong answer
    repo.upsert_checkpoint_attempt = AsyncMock(
        return_value=StudentCheckpointAttempt(is_correct=False)
    )
    res_wrong = await service.submit_checkpoint(
        ids["course_id"], chk.id, CheckpointSubmitRequest(selected_option="A"), ids["student_id"]
    )
    assert res_wrong.is_correct is False
    assert res_wrong.is_passed is False
    assert res_wrong.rewind_seconds == 15

    # Correct answer
    repo.upsert_checkpoint_attempt = AsyncMock(
        return_value=StudentCheckpointAttempt(is_correct=True)
    )
    res_ok = await service.submit_checkpoint(
        ids["course_id"], chk.id, CheckpointSubmitRequest(selected_option="c"), ids["student_id"]
    )
    assert res_ok.is_correct is True
    assert res_ok.is_passed is True
    assert res_ok.rewind_seconds == 0


@pytest.mark.asyncio
async def test_complete_material_blocked_when_blocking_checkpoint_unpassed(mock_db, ids):
    """Strict gate: complete_material raises UncompletedCheckpointsException if blocking checkpoints are unpassed."""
    repo = MagicMock(spec=LearningRepository)
    mod = LearningModule(
        id=ids["module_id"],
        course_id=ids["course_id"],
        title="Week 1",
        is_published=True,
        unlock_at=None,
        prerequisite_module_id=None,
    )
    mat = LearningMaterial(
        id=ids["material_id"],
        module_id=ids["module_id"],
        title="Video Lecture",
        material_type=MaterialType.VIDEO.value,
        is_published=True,
    )
    repo.get_material = AsyncMock(return_value=mat)
    repo.get_module = AsyncMock(return_value=mod)
    repo.get_unpassed_blocking_checkpoints = AsyncMock(return_value=[uuid.uuid4()])
    repo.mark_material_completed = AsyncMock()

    service = LearningMaterialService(mock_db, repo=repo)
    service.course_service = _mock_course_service(ContextualRole.STUDENT)

    with pytest.raises(UncompletedCheckpointsException):
        await service.complete_material(ids["course_id"], ids["material_id"], ids["student_id"])

    repo.mark_material_completed.assert_not_awaited()


@pytest.mark.asyncio
async def test_complete_material_succeeds_after_all_checkpoints_passed(mock_db, ids):
    """Strict gate: complete_material succeeds once all blocking checkpoints are passed."""
    repo = MagicMock(spec=LearningRepository)
    mod = LearningModule(
        id=ids["module_id"],
        course_id=ids["course_id"],
        title="Week 1",
        is_published=True,
        unlock_at=None,
        prerequisite_module_id=None,
    )
    mat = LearningMaterial(
        id=ids["material_id"],
        module_id=ids["module_id"],
        title="Video Lecture",
        material_type=MaterialType.VIDEO.value,
        is_published=True,
    )
    repo.get_material = AsyncMock(return_value=mat)
    repo.get_module = AsyncMock(return_value=mod)
    repo.get_unpassed_blocking_checkpoints = AsyncMock(return_value=[])
    repo.mark_material_completed = AsyncMock()

    service = LearningMaterialService(mock_db, repo=repo)
    service.course_service = _mock_course_service(ContextualRole.STUDENT)

    await service.complete_material(ids["course_id"], ids["material_id"], ids["student_id"])
    repo.mark_material_completed.assert_awaited_once_with(ids["student_id"], ids["material_id"])
