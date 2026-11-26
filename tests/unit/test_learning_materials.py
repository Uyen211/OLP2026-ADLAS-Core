# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Unit tests for Learning Modules, Materials, BR-STORAGE-02 Quotas, and BR-LO-01 Guard."""

from datetime import datetime, timedelta, timezone
import io
from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest
from app.modules.course.enums import BloomLevel, ContextualRole
from app.modules.course.lo_references import lo_reference_registry
from app.modules.course.public_api import LODTO, CoursePublicService
from app.modules.learning import is_lo_referenced_by_learning
from app.modules.learning.enums import MaterialType
from app.modules.learning.exceptions import (
    InvalidMaterialFormatException,
    LearningMaterialNotFoundException,
    LearningModuleNotFoundException,
    MaterialQuotaExceededException,
    ModuleCircularDependencyException,
    ModuleLockedException,
)
from app.modules.learning.models import LearningMaterial, LearningModule
from app.modules.learning.repository import LearningRepository
from app.modules.learning.schemas import (
    MaterialCreate,
    MaterialUpdate,
    ModuleCreate,
    ModuleUpdate,
)
from app.modules.learning.service import (
    LearningMaterialService,
    LearningModuleService,
)
from app.modules.system.storage_schemas import GlobalQuotaConfig


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def course_id():
    return uuid.uuid4()


@pytest.fixture
def instructor_id():
    return uuid.uuid4()


@pytest.fixture
def student_id():
    return uuid.uuid4()


@pytest.fixture
def mock_course_service(monkeypatch):
    """Mock CoursePublicService to verify contextual roles and LO lists."""
    mock_service = MagicMock(spec=CoursePublicService)

    async def mock_assert_course_role(course_id, user_id, allowed_roles, is_admin=False):
        if is_admin:
            return ContextualRole.INSTRUCTOR
        if ContextualRole.INSTRUCTOR in allowed_roles:
            return ContextualRole.INSTRUCTOR
        return ContextualRole.STUDENT

    mock_service.assert_course_role = AsyncMock(side_effect=mock_assert_course_role)
    mock_service.get_learning_objectives = AsyncMock(return_value=[
        LODTO(
            id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            course_id=uuid.uuid4(),
            code="LO1",
            description="Hiểu kiến trúc phân tán",
            bloom_level=BloomLevel.UNDERSTAND,
            order_index=1,
        ),
        LODTO(
            id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            course_id=uuid.uuid4(),
            code="LO2",
            description="Áp dụng pgvector và HNSW",
            bloom_level=BloomLevel.APPLY,
            order_index=2,
        ),
    ])
    return mock_service


@pytest.mark.asyncio
async def test_module_create_auto_increments_order(mock_db, course_id, instructor_id, mock_course_service):
    """Test creating a module automatically sets order_index if not supplied."""
    repo = MagicMock(spec=LearningRepository)
    repo.get_max_order_index = AsyncMock(return_value=3)

    created_mod = None

    async def mock_create(mod):
        nonlocal created_mod
        created_mod = mod
        mod.id = uuid.uuid4()
        mod.created_at = datetime.now(timezone.utc)
        mod.materials = []
        return mod

    repo.create_module = AsyncMock(side_effect=mock_create)
    repo.get_module = AsyncMock(side_effect=lambda mid, **kw: created_mod if created_mod and created_mod.id == mid else None)

    service = LearningModuleService(mock_db, repo=repo)
    service.course_service = mock_course_service

    payload = ModuleCreate(title="Chương 4: Động cơ Socratic AI", is_published=True)
    res = await service.create_module(course_id, payload, instructor_id)

    assert res.title == "Chương 4: Động cơ Socratic AI"
    assert res.order_index == 4
    assert res.is_published is True


@pytest.mark.asyncio
async def test_module_circular_dependency_self_reference(mock_db, course_id, instructor_id, mock_course_service):
    """BR: Module cannot set itself as prerequisite."""
    repo = MagicMock(spec=LearningRepository)
    mod_id = uuid.uuid4()
    mod = LearningModule(id=mod_id, course_id=course_id, title="Module 1", prerequisite_module_id=None)
    repo.get_module = AsyncMock(return_value=mod)
    repo.list_modules = AsyncMock(return_value=[mod])

    service = LearningModuleService(mock_db, repo=repo)
    service.course_service = mock_course_service

    update_payload = ModuleUpdate(prerequisite_module_id=mod_id)

    with pytest.raises(ModuleCircularDependencyException) as exc_info:
        await service.update_module(course_id, mod_id, update_payload, instructor_id)
    assert "tự làm điều kiện tiên quyết" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_module_circular_dependency_chain(mock_db, course_id, instructor_id, mock_course_service):
    """BR: Circular dependency A -> B -> A must be blocked."""
    mod_a_id = uuid.uuid4()
    mod_b_id = uuid.uuid4()

    mod_a = LearningModule(id=mod_a_id, course_id=course_id, title="Module A", prerequisite_module_id=None)
    mod_b = LearningModule(id=mod_b_id, course_id=course_id, title="Module B", prerequisite_module_id=mod_a_id)

    repo = MagicMock(spec=LearningRepository)
    repo.get_module = AsyncMock(return_value=mod_a)
    repo.list_modules = AsyncMock(return_value=[mod_a, mod_b])

    service = LearningModuleService(mock_db, repo=repo)
    service.course_service = mock_course_service

    # Module A tries to set Module B as prerequisite (creating loop A -> B -> A)
    update_payload = ModuleUpdate(prerequisite_module_id=mod_b_id)

    with pytest.raises(ModuleCircularDependencyException) as exc_info:
        await service.update_module(course_id, mod_a_id, update_payload, instructor_id)
    assert "vòng tròn" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_student_locked_module_by_unlock_at(mock_db, course_id, student_id, mock_course_service):
    """Student viewing future unlock_at module sees it marked locked with hidden materials."""
    future_time = datetime.now(timezone.utc) + timedelta(days=3)
    mod = LearningModule(
        id=uuid.uuid4(),
        course_id=course_id,
        title="Chương tương lai",
        order_index=1,
        unlock_at=future_time,
        prerequisite_module_id=None,
        is_published=True,
        created_at=datetime.now(timezone.utc),
    )
    mat = LearningMaterial(
        id=uuid.uuid4(),
        module_id=mod.id,
        title="Tài liệu bí mật",
        material_type="PDF",
        is_published=True,
        created_at=datetime.now(timezone.utc),
    )
    mod.materials = [mat]

    repo = MagicMock(spec=LearningRepository)
    repo.list_modules = AsyncMock(return_value=[mod])

    # Switch role to STUDENT
    mock_course_service.assert_course_role = AsyncMock(return_value=ContextualRole.STUDENT)

    service = LearningModuleService(mock_db, repo=repo)
    service.course_service = mock_course_service

    modules = await service.list_modules(course_id, student_id)
    assert len(modules) == 1
    assert modules[0].is_locked is True
    assert "mở khóa vào lúc" in (modules[0].lock_reason or "").lower()
    # Materials must be hidden when module is locked
    assert len(modules[0].materials) == 0


@pytest.mark.asyncio
async def test_student_locked_module_by_prerequisite(mock_db, course_id, student_id, mock_course_service):
    """Student viewing module whose prerequisite is not completed sees it locked."""
    prereq_id = uuid.uuid4()
    mod = LearningModule(
        id=uuid.uuid4(),
        course_id=course_id,
        title="Chương nâng cao",
        order_index=2,
        unlock_at=None,
        prerequisite_module_id=prereq_id,
        is_published=True,
        created_at=datetime.now(timezone.utc),
    )
    mod.materials = []

    repo = MagicMock(spec=LearningRepository)
    repo.list_modules = AsyncMock(return_value=[mod])
    repo.is_module_completed_by_user = AsyncMock(return_value=False)

    mock_course_service.assert_course_role = AsyncMock(return_value=ContextualRole.STUDENT)

    service = LearningModuleService(mock_db, repo=repo)
    service.course_service = mock_course_service

    modules = await service.list_modules(course_id, student_id)
    assert len(modules) == 1
    assert modules[0].is_locked is True
    assert "Cần hoàn thành" in (modules[0].lock_reason or "")


@pytest.mark.asyncio
async def test_material_create_with_invalid_lo_rejects(mock_db, course_id, instructor_id, mock_course_service):
    """Associating material with an LO not in this course must raise 404."""
    mod = LearningModule(id=uuid.uuid4(), course_id=course_id, title="Module 1")
    repo = MagicMock(spec=LearningRepository)
    repo.get_module = AsyncMock(return_value=mod)

    service = LearningMaterialService(mock_db, repo=repo)
    service.course_service = mock_course_service

    unrelated_lo = uuid.uuid4()
    payload = MaterialCreate(
        title="Slide giới thiệu",
        material_type=MaterialType.SLIDE,
        lo_id=unrelated_lo,
    )

    with pytest.raises(LearningMaterialNotFoundException) as exc_info:
        await service.create_material(course_id, mod.id, payload, instructor_id)
    assert "Chuẩn đầu ra không tồn tại" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_material_quota_check_slide_exceeded_br_storage_02(mock_db, course_id, instructor_id, mock_course_service, monkeypatch):
    """Uploading a Slide/PDF exceeding max_slide_mb (50MB) raises MaterialQuotaExceededException (BR-STORAGE-02)."""
    mod = LearningModule(id=uuid.uuid4(), course_id=course_id, title="Module 1")
    repo = MagicMock(spec=LearningRepository)
    repo.get_module = AsyncMock(return_value=mod)

    service = LearningMaterialService(mock_db, repo=repo)
    service.course_service = mock_course_service

    # Mock storage quotas returning max_slide_mb=50
    from app.modules.system.storage_service import StorageAdminService
    monkeypatch.setattr(
        StorageAdminService,
        "get_global_quotas",
        AsyncMock(return_value=GlobalQuotaConfig(max_slide_mb=50, max_video_mb=500)),
    )

    # Create mock UploadFile with 51MB of data
    mock_file = MagicMock()
    mock_file.filename = "large_lecture_slide.pptx"
    # Stream returns 51 * 1MB chunks
    chunks = [b"x" * (1024 * 1024)] * 51
    chunk_iter = iter(chunks)

    async def mock_read(size):
        try:
            return next(chunk_iter)
        except StopIteration:
            return b""

    mock_file.read = AsyncMock(side_effect=mock_read)

    with pytest.raises(MaterialQuotaExceededException) as exc_info:
        await service.upload_material_file(course_id, mod.id, mock_file, instructor_id)
    assert "vượt quá hạn ngạch tối đa 50MB" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_material_unsupported_format_rejects(mock_db, course_id, instructor_id, mock_course_service):
    """Executable or forbidden extensions must be rejected with 422 format error."""
    mod = LearningModule(id=uuid.uuid4(), course_id=course_id, title="Module 1")
    repo = MagicMock(spec=LearningRepository)
    repo.get_module = AsyncMock(return_value=mod)

    service = LearningMaterialService(mock_db, repo=repo)
    service.course_service = mock_course_service

    mock_file = MagicMock()
    mock_file.filename = "malicious_script.exe"

    with pytest.raises(InvalidMaterialFormatException) as exc_info:
        await service.upload_material_file(course_id, mod.id, mock_file, instructor_id)
    assert "không được hỗ trợ" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_br_lo_01_hook_blocks_lo_deletion(mock_db):
    """BR-LO-01: Hook registered with Course Context returns True if LO is used by learning materials."""
    test_lo_id = uuid.uuid4()

    # Mock repo to return True for is_lo_referenced
    mock_db.execute = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = uuid.uuid4()
    mock_db.execute.return_value = mock_result

    is_referenced = await is_lo_referenced_by_learning(mock_db, test_lo_id)
    assert is_referenced is True

    # Test via registry
    is_in_use = await lo_reference_registry.is_lo_referenced(mock_db, test_lo_id)
    assert is_in_use is True


def test_router_is_admin_resolves_from_system_role():
    """Verify router _is_admin helper checks User.system_role instead of non-existent is_admin attribute."""
    from app.modules.identity.dependencies import CurrentUser
    from app.modules.learning.router import _is_admin
    from app.modules.system.models import User

    admin_user = User(id=uuid.uuid4(), email="admin@adlas.edu.vn", full_name="Admin", password_hash="x", system_role="ADMIN")
    teacher_user = User(id=uuid.uuid4(), email="teacher@adlas.edu.vn", full_name="Teacher", password_hash="x", system_role="USER")
    none_role_user = User(id=uuid.uuid4(), email="user@adlas.edu.vn", full_name="User", password_hash="x", system_role=None)

    assert _is_admin(CurrentUser(user=admin_user, token="tok")) is True
    assert _is_admin(CurrentUser(user=teacher_user, token="tok")) is False
    assert _is_admin(CurrentUser(user=none_role_user, token="tok")) is False


def test_resolve_local_path_handles_relative_and_legacy_paths(monkeypatch):
    """Relative 'materials/...' and legacy OS paths resolve consistently to active base dir."""
    import os
    monkeypatch.setenv("UPLOAD_DIR", "/tmp/adlas_uploads")

    assert LearningMaterialService._resolve_local_path("materials/guide.pdf") == os.path.join("/tmp/adlas_uploads", "materials/guide.pdf")
    assert LearningMaterialService._resolve_local_path(
        "C:\\Users\\DELL\\.adlas\\uploads\\materials\\guide.pdf"
    ) == os.path.join("/tmp/adlas_uploads", "materials/guide.pdf")
    assert LearningMaterialService._resolve_local_path("https://youtube.com/watch?v=123") == "https://youtube.com/watch?v=123"


def test_router_resolve_media_type():
    """Verify inline preview MIME media_type resolution for supported learning formats."""
    from app.modules.learning.router import _resolve_media_type

    assert _resolve_media_type("lecture.pdf") == "application/pdf"
    assert _resolve_media_type("demo.mp4") == "video/mp4"
    assert _resolve_media_type("handbook.md") == "text/markdown; charset=utf-8"
    assert "presentationml" in _resolve_media_type("slides.pptx")


@pytest.mark.asyncio
async def test_update_module_clears_prerequisite_and_unlock_at_when_null_sent(
    mock_db, course_id, instructor_id, mock_course_service
):
    """Explicitly passing None for prerequisite_module_id and unlock_at clears them in DB."""
    from datetime import datetime, timezone
    from app.modules.learning.schemas import ModuleUpdate

    mod = LearningModule(
        id=uuid.uuid4(),
        course_id=course_id,
        title="Chương 2",
        order_index=2,
        prerequisite_module_id=uuid.uuid4(),
        unlock_at=datetime.now(timezone.utc),
        is_published=True,
        created_at=datetime.now(timezone.utc),
        materials=[],
    )
    repo = MagicMock(spec=LearningRepository)
    repo.get_module = AsyncMock(return_value=mod)
    repo.update_module = AsyncMock(return_value=mod)

    service = LearningModuleService(mock_db, repo=repo)
    service.course_service = mock_course_service

    payload = ModuleUpdate.model_validate({"prerequisite_module_id": None, "unlock_at": None})
    await service.update_module(course_id, mod.id, payload, instructor_id)

    assert mod.prerequisite_module_id is None
    assert mod.unlock_at is None


@pytest.mark.asyncio
async def test_update_material_clears_lo_id_and_file_url_when_null_sent(
    mock_db, course_id, instructor_id, mock_course_service
):
    """Explicitly passing None for lo_id and file_url clears them in DB."""
    from datetime import datetime, timezone
    from app.modules.learning.models import LearningMaterial
    from app.modules.learning.schemas import MaterialUpdate

    mod = LearningModule(id=uuid.uuid4(), course_id=course_id, title="Chương 1", is_published=True)
    mat = LearningMaterial(
        id=uuid.uuid4(),
        module_id=mod.id,
        lo_id=uuid.uuid4(),
        title="Tài liệu cũ",
        material_type=MaterialType.PDF.value,
        file_url="materials/old.pdf",
        is_mandatory=True,
        est_duration_minutes=30,
        is_published=True,
        created_at=datetime.now(timezone.utc),
    )
    repo = MagicMock(spec=LearningRepository)
    repo.get_material = AsyncMock(return_value=mat)
    repo.get_module = AsyncMock(return_value=mod)
    repo.update_material = AsyncMock(return_value=mat)

    service = LearningMaterialService(mock_db, repo=repo)
    service.course_service = mock_course_service

    payload = MaterialUpdate.model_validate({"lo_id": None, "file_url": None})
    await service.update_material(course_id, mat.id, payload, instructor_id)

    assert mat.lo_id is None
    assert mat.file_url is None
