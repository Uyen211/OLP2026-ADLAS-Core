# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Business logic services for Learning Modules and Learning Materials."""

import os
from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.course.enums import ContextualRole
from app.modules.course.public_api import CoursePublicService
from app.modules.learning.enums import MaterialType
from app.modules.learning.exceptions import (
    CheckpointNotFoundException,
    CheckpointSpacingException,
    InvalidMaterialFormatException,
    LearningMaterialNotFoundException,
    LearningModuleNotFoundException,
    MaterialQuotaExceededException,
    ModuleCircularDependencyException,
    ModuleLockedException,
    UncompletedCheckpointsException,
)
from app.modules.learning.models import LearningMaterial, LearningModule, MaterialCheckpoint
from app.modules.learning.repository import LearningRepository
from app.modules.learning.schemas import (
    CheckpointCreate,
    CheckpointInstructorResponse,
    CheckpointStudentResponse,
    CheckpointSubmitRequest,
    CheckpointSubmitResponse,
    CheckpointUpdate,
    MaterialCreate,
    MaterialResponse,
    MaterialUpdate,
    MaterialUploadResponse,
    ModuleCreate,
    ModuleResponse,
    ModuleUpdate,
)
from app.modules.system.storage_service import StorageAdminService


class LearningModuleService:
    """Orchestrates course modules, ordering, and permissions."""

    def __init__(self, db: AsyncSession, repo: Optional[LearningRepository] = None):
        self.db = db
        self.repo = repo or LearningRepository(db)
        self.course_service = CoursePublicService(db)

    async def _assert_no_circular_dependency(
        self,
        course_id: uuid.UUID,
        module_id: Optional[uuid.UUID],
        prerequisite_id: Optional[uuid.UUID],
    ) -> None:
        """Prevent circular or self prerequisite dependency chains."""
        if not prerequisite_id:
            return

        if module_id and prerequisite_id == module_id:
            raise ModuleCircularDependencyException("Bài học không thể tự làm điều kiện tiên quyết cho chính nó.")

        all_modules = await self.repo.list_modules(course_id, is_published_only=False)
        prereq_graph: Dict[uuid.UUID, Optional[uuid.UUID]] = {
            m.id: m.prerequisite_module_id for m in all_modules
        }

        if prerequisite_id not in prereq_graph:
            raise LearningModuleNotFoundException("Bài học tiên quyết không tồn tại trong môn học này.")

        if module_id:
            prereq_graph[module_id] = prerequisite_id

        visited = set()
        curr = prerequisite_id
        while curr:
            if curr in visited or (module_id and curr == module_id):
                raise ModuleCircularDependencyException("Phát hiện điều kiện tiên quyết vòng tròn giữa các bài học.")
            visited.add(curr)
            curr = prereq_graph.get(curr)

    async def _resolve_student_lock(
        self,
        module: LearningModule,
        user_id: uuid.UUID,
        mod_map: Dict[uuid.UUID, str],
    ) -> tuple[bool, Optional[str]]:
        """Determine if a module is locked for a student and provide localized reason."""
        now = datetime.now(timezone.utc)
        if module.unlock_at and module.unlock_at > now:
            unlock_str = module.unlock_at.strftime("%d/%m/%Y %H:%M")
            return True, f"Bài học mở khóa vào lúc {unlock_str}."

        if module.prerequisite_module_id:
            is_completed = await self.repo.is_module_completed_by_user(
                module.prerequisite_module_id,
                user_id,
            )
            if not is_completed:
                prereq_title = mod_map.get(module.prerequisite_module_id, "bài học trước")
                return True, f"Cần hoàn thành '{prereq_title}' để mở khóa bài học này."

        return False, None

    async def list_modules(
        self,
        course_id: uuid.UUID,
        user_id: uuid.UUID,
        is_admin: bool = False,
    ) -> List[ModuleResponse]:
        """List all modules for a course with contextual role check."""
        role = await self.course_service.assert_course_role(
            course_id=course_id,
            user_id=user_id,
            allowed_roles=[ContextualRole.INSTRUCTOR, ContextualRole.STUDENT],
            is_admin=is_admin,
        )

        is_student = (role == ContextualRole.STUDENT and not is_admin)
        modules = await self.repo.list_modules(course_id, is_published_only=is_student)

        # Build LO code lookup cache for materials
        los = await self.course_service.get_learning_objectives(course_id)
        lo_map: Dict[uuid.UUID, str] = {lo.id: lo.code for lo in los}
        mod_map: Dict[uuid.UUID, str] = {m.id: m.title for m in modules}

        responses: List[ModuleResponse] = []
        for mod in modules:
            is_locked = False
            lock_reason = None
            if is_student:
                is_locked, lock_reason = await self._resolve_student_lock(mod, user_id, mod_map)

            # Filter materials for students (hide contents if locked)
            materials = mod.materials or []
            if is_student:
                if is_locked:
                    materials = []
                else:
                    materials = [mat for mat in materials if mat.is_published]

            mat_responses = [
                MaterialResponse(
                    id=mat.id,
                    module_id=mat.module_id,
                    lo_id=mat.lo_id,
                    lo_code=lo_map.get(mat.lo_id) if mat.lo_id else None,
                    title=mat.title,
                    material_type=mat.material_type,
                    file_url=mat.file_url,
                    is_mandatory=mat.is_mandatory,
                    est_duration_minutes=mat.est_duration_minutes or 30,
                    is_published=mat.is_published,
                    created_at=mat.created_at,
                )
                for mat in materials
            ]

            responses.append(
                ModuleResponse(
                    id=mod.id,
                    course_id=mod.course_id,
                    title=mod.title,
                    order_index=mod.order_index,
                    unlock_at=mod.unlock_at,
                    prerequisite_module_id=mod.prerequisite_module_id,
                    prerequisite_title=mod_map.get(mod.prerequisite_module_id) if mod.prerequisite_module_id else None,
                    is_published=mod.is_published,
                    is_locked=is_locked,
                    lock_reason=lock_reason,
                    created_at=mod.created_at,
                    materials=mat_responses,
                )
            )

        return responses

    async def get_module_detail(
        self,
        course_id: uuid.UUID,
        module_id: uuid.UUID,
        user_id: uuid.UUID,
        is_admin: bool = False,
    ) -> ModuleResponse:
        """Fetch module detail."""
        role = await self.course_service.assert_course_role(
            course_id=course_id,
            user_id=user_id,
            allowed_roles=[ContextualRole.INSTRUCTOR, ContextualRole.STUDENT],
            is_admin=is_admin,
        )

        mod = await self.repo.get_module(module_id)
        if not mod or mod.course_id != course_id:
            raise LearningModuleNotFoundException()

        is_student = (role == ContextualRole.STUDENT and not is_admin)
        if is_student and not mod.is_published:
            raise LearningModuleNotFoundException()

        prereq_title = None
        if mod.prerequisite_module_id:
            prereq = await self.repo.get_module(mod.prerequisite_module_id, include_materials=False)
            if prereq:
                prereq_title = prereq.title

        is_locked = False
        lock_reason = None
        if is_student:
            mod_map = {mod.id: mod.title}
            if mod.prerequisite_module_id and prereq_title:
                mod_map[mod.prerequisite_module_id] = prereq_title
            is_locked, lock_reason = await self._resolve_student_lock(mod, user_id, mod_map)
            if is_locked:
                raise ModuleLockedException(lock_reason or "Bài học đang tạm khóa.")

        los = await self.course_service.get_learning_objectives(course_id)
        lo_map: Dict[uuid.UUID, str] = {lo.id: lo.code for lo in los}

        materials = mod.materials or []
        if is_student:
            materials = [mat for mat in materials if mat.is_published]

        mat_responses = [
            MaterialResponse(
                id=mat.id,
                module_id=mat.module_id,
                lo_id=mat.lo_id,
                lo_code=lo_map.get(mat.lo_id) if mat.lo_id else None,
                title=mat.title,
                material_type=mat.material_type,
                file_url=mat.file_url,
                is_mandatory=mat.is_mandatory,
                est_duration_minutes=mat.est_duration_minutes or 30,
                is_published=mat.is_published,
                created_at=mat.created_at,
            )
            for mat in materials
        ]

        return ModuleResponse(
            id=mod.id,
            course_id=mod.course_id,
            title=mod.title,
            order_index=mod.order_index,
            unlock_at=mod.unlock_at,
            prerequisite_module_id=mod.prerequisite_module_id,
            prerequisite_title=prereq_title,
            is_published=mod.is_published,
            is_locked=is_locked,
            lock_reason=lock_reason,
            created_at=mod.created_at,
            materials=mat_responses,
        )

    async def create_module(
        self,
        course_id: uuid.UUID,
        payload: ModuleCreate,
        user_id: uuid.UUID,
        is_admin: bool = False,
    ) -> ModuleResponse:
        """Create a new module within course."""
        await self.course_service.assert_course_role(
            course_id=course_id,
            user_id=user_id,
            allowed_roles=[ContextualRole.INSTRUCTOR],
            is_admin=is_admin,
        )

        if payload.prerequisite_module_id:
            await self._assert_no_circular_dependency(course_id, None, payload.prerequisite_module_id)

        order_idx = payload.order_index
        if order_idx is None:
            max_idx = await self.repo.get_max_order_index(course_id)
            order_idx = max_idx + 1

        mod = LearningModule(
            course_id=course_id,
            title=payload.title.strip(),
            order_index=order_idx,
            unlock_at=payload.unlock_at,
            prerequisite_module_id=payload.prerequisite_module_id,
            is_published=payload.is_published,
        )

        mod = await self.repo.create_module(mod)
        return await self.get_module_detail(course_id, mod.id, user_id, is_admin=is_admin)

    async def update_module(
        self,
        course_id: uuid.UUID,
        module_id: uuid.UUID,
        payload: ModuleUpdate,
        user_id: uuid.UUID,
        is_admin: bool = False,
    ) -> ModuleResponse:
        """Update existing module metadata."""
        await self.course_service.assert_course_role(
            course_id=course_id,
            user_id=user_id,
            allowed_roles=[ContextualRole.INSTRUCTOR],
            is_admin=is_admin,
        )

        mod = await self.repo.get_module(module_id)
        if not mod or mod.course_id != course_id:
            raise LearningModuleNotFoundException()

        fields_set = payload.model_fields_set

        if "prerequisite_module_id" in fields_set:
            if payload.prerequisite_module_id is not None:
                await self._assert_no_circular_dependency(course_id, mod.id, payload.prerequisite_module_id)
            mod.prerequisite_module_id = payload.prerequisite_module_id

        if payload.title is not None:
            mod.title = payload.title.strip()
        if payload.order_index is not None:
            mod.order_index = payload.order_index
        if "unlock_at" in fields_set:
            mod.unlock_at = payload.unlock_at
        if payload.is_published is not None:
            mod.is_published = payload.is_published

        await self.repo.update_module(mod)
        return await self.get_module_detail(course_id, mod.id, user_id, is_admin=is_admin)

    async def delete_module(
        self,
        course_id: uuid.UUID,
        module_id: uuid.UUID,
        user_id: uuid.UUID,
        is_admin: bool = False,
    ) -> None:
        """Delete module and cascade remove all materials."""
        await self.course_service.assert_course_role(
            course_id=course_id,
            user_id=user_id,
            allowed_roles=[ContextualRole.INSTRUCTOR],
            is_admin=is_admin,
        )

        mod = await self.repo.get_module(module_id)
        if not mod or mod.course_id != course_id:
            raise LearningModuleNotFoundException()

        await self.repo.delete_module(mod)

    async def toggle_publish(
        self,
        course_id: uuid.UUID,
        module_id: uuid.UUID,
        is_published: bool,
        user_id: uuid.UUID,
        is_admin: bool = False,
    ) -> ModuleResponse:
        """Toggle publish status for module."""
        await self.course_service.assert_course_role(
            course_id=course_id,
            user_id=user_id,
            allowed_roles=[ContextualRole.INSTRUCTOR],
            is_admin=is_admin,
        )

        mod = await self.repo.get_module(module_id)
        if not mod or mod.course_id != course_id:
            raise LearningModuleNotFoundException()

        mod.is_published = is_published
        await self.repo.update_module(mod)
        return await self.get_module_detail(course_id, mod.id, user_id, is_admin=is_admin)

    async def reorder_modules(
        self,
        course_id: uuid.UUID,
        ordered_ids: List[uuid.UUID],
        user_id: uuid.UUID,
        is_admin: bool = False,
    ) -> List[ModuleResponse]:
        """Reorder modules sequentially."""
        await self.course_service.assert_course_role(
            course_id=course_id,
            user_id=user_id,
            allowed_roles=[ContextualRole.INSTRUCTOR],
            is_admin=is_admin,
        )

        await self.repo.reorder_modules(course_id, ordered_ids)
        return await self.list_modules(course_id, user_id, is_admin=is_admin)


class LearningMaterialService:
    """Manages digital learning resources inside modules."""

    def __init__(self, db: AsyncSession, repo: Optional[LearningRepository] = None):
        self.db = db
        self.repo = repo or LearningRepository(db)
        self.course_service = CoursePublicService(db)

    async def create_material(
        self,
        course_id: uuid.UUID,
        module_id: uuid.UUID,
        payload: MaterialCreate,
        user_id: uuid.UUID,
        is_admin: bool = False,
    ) -> MaterialResponse:
        """Create new material within a module."""
        await self.course_service.assert_course_role(
            course_id=course_id,
            user_id=user_id,
            allowed_roles=[ContextualRole.INSTRUCTOR],
            is_admin=is_admin,
        )

        mod = await self.repo.get_module(module_id)
        if not mod or mod.course_id != course_id:
            raise LearningModuleNotFoundException()

        lo_code = None
        if payload.lo_id:
            los = await self.course_service.get_learning_objectives(course_id)
            matching_lo = next((lo for lo in los if lo.id == payload.lo_id), None)
            if not matching_lo:
                raise LearningMaterialNotFoundException("Chuẩn đầu ra không tồn tại trong môn học.")
            lo_code = matching_lo.code

        mat = LearningMaterial(
            module_id=module_id,
            lo_id=payload.lo_id,
            title=payload.title.strip(),
            material_type=payload.material_type.value,
            file_url=payload.file_url,
            is_mandatory=payload.is_mandatory,
            est_duration_minutes=payload.est_duration_minutes,
            is_published=payload.is_published,
        )

        mat = await self.repo.create_material(mat)
        return MaterialResponse(
            id=mat.id,
            module_id=mat.module_id,
            lo_id=mat.lo_id,
            lo_code=lo_code,
            title=mat.title,
            material_type=mat.material_type,
            file_url=mat.file_url,
            is_mandatory=mat.is_mandatory,
            est_duration_minutes=mat.est_duration_minutes,
            is_published=mat.is_published,
            created_at=mat.created_at,
        )

    async def get_material_detail(
        self,
        course_id: uuid.UUID,
        material_id: uuid.UUID,
        user_id: uuid.UUID,
        is_admin: bool = False,
    ) -> MaterialResponse:
        """Fetch material detail with permission check."""
        role = await self.course_service.assert_course_role(
            course_id=course_id,
            user_id=user_id,
            allowed_roles=[ContextualRole.INSTRUCTOR, ContextualRole.STUDENT],
            is_admin=is_admin,
        )

        mat = await self.repo.get_material(material_id)
        if not mat:
            raise LearningMaterialNotFoundException()

        mod = await self.repo.get_module(mat.module_id)
        if not mod or mod.course_id != course_id:
            raise LearningMaterialNotFoundException()

        is_student = (role == ContextualRole.STUDENT and not is_admin)
        if is_student and (not mat.is_published or not mod.is_published):
            raise LearningMaterialNotFoundException()

        lo_code = None
        if mat.lo_id:
            los = await self.course_service.get_learning_objectives(course_id)
            matching_lo = next((lo for lo in los if lo.id == mat.lo_id), None)
            if matching_lo:
                lo_code = matching_lo.code

        return MaterialResponse(
            id=mat.id,
            module_id=mat.module_id,
            lo_id=mat.lo_id,
            lo_code=lo_code,
            title=mat.title,
            material_type=mat.material_type,
            file_url=mat.file_url,
            is_mandatory=mat.is_mandatory,
            est_duration_minutes=mat.est_duration_minutes,
            is_published=mat.is_published,
            created_at=mat.created_at,
        )

    async def update_material(
        self,
        course_id: uuid.UUID,
        material_id: uuid.UUID,
        payload: MaterialUpdate,
        user_id: uuid.UUID,
        is_admin: bool = False,
    ) -> MaterialResponse:
        """Update existing material."""
        await self.course_service.assert_course_role(
            course_id=course_id,
            user_id=user_id,
            allowed_roles=[ContextualRole.INSTRUCTOR],
            is_admin=is_admin,
        )

        mat = await self.repo.get_material(material_id)
        if not mat:
            raise LearningMaterialNotFoundException()

        mod = await self.repo.get_module(mat.module_id)
        if not mod or mod.course_id != course_id:
            raise LearningMaterialNotFoundException()

        fields_set = payload.model_fields_set

        if payload.title is not None:
            mat.title = payload.title.strip()
        if payload.material_type is not None:
            mat.material_type = payload.material_type.value
        if "lo_id" in fields_set:
            if payload.lo_id is not None:
                los = await self.course_service.get_learning_objectives(course_id)
                if not any(lo.id == payload.lo_id for lo in los):
                    raise LearningMaterialNotFoundException("Chuẩn đầu ra không tồn tại trong môn học.")
            mat.lo_id = payload.lo_id
        if "file_url" in fields_set:
            mat.file_url = payload.file_url
        if payload.is_mandatory is not None:
            mat.is_mandatory = payload.is_mandatory
        if payload.est_duration_minutes is not None:
            mat.est_duration_minutes = payload.est_duration_minutes
        if payload.is_published is not None:
            mat.is_published = payload.is_published

        await self.repo.update_material(mat)
        return await self.get_material_detail(course_id, mat.id, user_id, is_admin=is_admin)

    async def delete_material(
        self,
        course_id: uuid.UUID,
        material_id: uuid.UUID,
        user_id: uuid.UUID,
        is_admin: bool = False,
    ) -> None:
        """Delete material from module."""
        await self.course_service.assert_course_role(
            course_id=course_id,
            user_id=user_id,
            allowed_roles=[ContextualRole.INSTRUCTOR],
            is_admin=is_admin,
        )

        mat = await self.repo.get_material(material_id)
        if not mat:
            raise LearningMaterialNotFoundException()

        mod = await self.repo.get_module(mat.module_id)
        if not mod or mod.course_id != course_id:
            raise LearningMaterialNotFoundException()

        await self.repo.delete_material(mat)

    async def toggle_publish(
        self,
        course_id: uuid.UUID,
        material_id: uuid.UUID,
        is_published: bool,
        user_id: uuid.UUID,
        is_admin: bool = False,
    ) -> MaterialResponse:
        """Toggle publish status for material."""
        await self.course_service.assert_course_role(
            course_id=course_id,
            user_id=user_id,
            allowed_roles=[ContextualRole.INSTRUCTOR],
            is_admin=is_admin,
        )

        mat = await self.repo.get_material(material_id)
        if not mat:
            raise LearningMaterialNotFoundException()

        mod = await self.repo.get_module(mat.module_id)
        if not mod or mod.course_id != course_id:
            raise LearningMaterialNotFoundException()

        mat.is_published = is_published
        await self.repo.update_material(mat)
        return await self.get_material_detail(course_id, mat.id, user_id, is_admin=is_admin)

    @staticmethod
    def detect_material_type(filename: str) -> MaterialType:
        """Detect MaterialType from filename extension."""
        ext = os.path.splitext(filename)[1].lower()
        if ext in {".pdf"}:
            return MaterialType.PDF
        if ext in {".ppt", ".pptx"}:
            return MaterialType.SLIDE
        if ext in {".mp4", ".webm", ".mov", ".mkv"}:
            return MaterialType.VIDEO
        if ext in {".docx", ".doc", ".txt", ".md"}:
            return MaterialType.DOCUMENT
        raise InvalidMaterialFormatException(
            f"Định dạng tệp '{ext}' không được hỗ trợ. Vui lòng tải lên PDF, PPT/PPTX, MP4/WEBM, DOCX, TXT hoặc Markdown."
        )

    @staticmethod
    def _resolve_base_upload_dir() -> str:
        """Resolve the base upload directory for the current runtime environment."""
        base_upload_dir = os.getenv("UPLOAD_DIR")
        if base_upload_dir:
            return base_upload_dir
        if os.path.exists("/app"):
            return "/app/uploads"
        return os.path.join(os.path.expanduser("~"), ".adlas", "uploads")

    @classmethod
    def _resolve_local_path(cls, raw_path: str) -> str:
        """Resolve a stored file_url (relative 'materials/...' or legacy OS path) to local filesystem path."""
        if not raw_path:
            return raw_path
        normalized = raw_path.replace("\\", "/")
        if normalized.startswith("http://") or normalized.startswith("https://"):
            return raw_path

        base_dir = cls._resolve_base_upload_dir()
        if normalized.startswith("materials/"):
            return os.path.join(base_dir, normalized)

        marker = "/materials/"
        if marker in normalized:
            rel_part = "materials/" + normalized.split(marker, 1)[1]
            return os.path.join(base_dir, rel_part)

        return raw_path

    async def upload_material_file(
        self,
        course_id: uuid.UUID,
        module_id: uuid.UUID,
        file: UploadFile,
        user_id: uuid.UUID,
        is_admin: bool = False,
    ) -> MaterialUploadResponse:
        """Upload learning material file with BR-STORAGE-02 quota enforcement."""
        await self.course_service.assert_course_role(
            course_id=course_id,
            user_id=user_id,
            allowed_roles=[ContextualRole.INSTRUCTOR],
            is_admin=is_admin,
        )

        mod = await self.repo.get_module(module_id)
        if not mod or mod.course_id != course_id:
            raise LearningModuleNotFoundException()

        filename = os.path.basename(file.filename or "material")
        mat_type = self.detect_material_type(filename)

        storage_admin = StorageAdminService(self.db)
        quotas = await storage_admin.get_global_quotas()

        if mat_type == MaterialType.VIDEO:
            max_bytes = quotas.max_video_mb * 1024 * 1024
            quota_label = f"{quotas.max_video_mb}MB"
        else:
            max_bytes = quotas.max_slide_mb * 1024 * 1024
            quota_label = f"{quotas.max_slide_mb}MB"

        base_upload_dir = self._resolve_base_upload_dir()
        upload_dir = os.path.join(base_upload_dir, "materials")
        os.makedirs(upload_dir, exist_ok=True)
        safe_filename = f"{uuid.uuid4()}-{filename}"
        local_path = os.path.join(upload_dir, safe_filename)
        relative_path = f"materials/{safe_filename}"

        total_written = 0
        try:
            with open(local_path, "wb") as buffer:
                while chunk := await file.read(1024 * 1024):
                    total_written += len(chunk)
                    if total_written > max_bytes:
                        buffer.close()
                        if os.path.exists(local_path):
                            os.remove(local_path)
                        raise MaterialQuotaExceededException(
                            f"Tệp học liệu '{filename}' ({round(total_written / (1024 * 1024), 2)}MB) vượt quá hạn ngạch tối đa {quota_label} (Quy tắc BR-STORAGE-02)."
                        )
                    buffer.write(chunk)
        except Exception:
            if os.path.exists(local_path):
                try:
                    os.remove(local_path)
                except OSError:
                    pass
            raise

        return MaterialUploadResponse(
            file_url=relative_path,
            file_name=filename,
            size_bytes=total_written,
            material_type=mat_type,
        )

    async def get_material_file_path(
        self,
        course_id: uuid.UUID,
        material_id: uuid.UUID,
        user_id: uuid.UUID,
        is_admin: bool = False,
        mark_completed: bool = True,
    ) -> str:
        """Validate permissions and return local file path for download/preview."""
        role = await self.course_service.assert_course_role(
            course_id=course_id,
            user_id=user_id,
            allowed_roles=[ContextualRole.INSTRUCTOR, ContextualRole.STUDENT],
            is_admin=is_admin,
        )

        mat = await self.repo.get_material(material_id)
        if not mat or not mat.file_url:
            raise LearningMaterialNotFoundException()

        mod = await self.repo.get_module(mat.module_id)
        if not mod or mod.course_id != course_id:
            raise LearningMaterialNotFoundException()

        is_student = (role == ContextualRole.STUDENT and not is_admin)
        if is_student:
            if not mat.is_published or not mod.is_published:
                raise LearningMaterialNotFoundException()

            mod_map = {mod.id: mod.title}
            if mod.prerequisite_module_id:
                prereq_obj = await self.repo.get_module(mod.prerequisite_module_id, include_materials=False)
                if prereq_obj:
                    mod_map[prereq_obj.id] = prereq_obj.title
            is_locked, lock_reason = await LearningModuleService(self.db, self.repo)._resolve_student_lock(
                mod, user_id, mod_map
            )
            if is_locked:
                raise ModuleLockedException(lock_reason or "Bài học đang tạm khóa.")

        resolved_path = self._resolve_local_path(mat.file_url)
        if not resolved_path or not os.path.exists(resolved_path):
            raise LearningMaterialNotFoundException("Tệp học liệu vật lý không tồn tại trên máy chủ lưu trữ.")

        if is_student and mark_completed:
            await self.repo.mark_material_completed(user_id, material_id)

        return resolved_path

    def _pdf_cache_dir(self, material_id: uuid.UUID) -> str:
        cache_dir = os.path.join(self._resolve_base_upload_dir(), ".preview_cache", str(material_id))
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir

    def _extract_pdf_pages(self, file_path: str, course_id: uuid.UUID, material_id: uuid.UUID) -> list[dict]:
        import fitz

        doc = fitz.open(file_path)
        cache_dir = self._pdf_cache_dir(material_id)
        items: list[dict] = []
        try:
            for idx, page in enumerate(doc, start=1):
                img_path = os.path.join(cache_dir, f"page_{idx}.png")
                if not os.path.exists(img_path) or os.path.getmtime(file_path) > os.path.getmtime(img_path):
                    pix = page.get_pixmap(dpi=130)
                    pix.save(img_path)
                raw_lines = [ln.strip() for ln in page.get_text("text").splitlines() if ln.strip()]
                title = raw_lines[0][:90] if raw_lines else f"Trang {idx}"
                items.append(
                    {
                        "index": idx,
                        "title": title,
                        "content_lines": raw_lines[:6],
                        "image_url": f"/courses/{course_id}/learning/materials/{material_id}/pages/{idx}/image",
                    }
                )
        finally:
            doc.close()
        return items

    def _extract_pptx_slides(self, file_path: str) -> list[dict]:
        from pptx import Presentation

        prs = Presentation(file_path)
        items: list[dict] = []
        for idx, slide in enumerate(prs.slides, start=1):
            title_text = ""
            if slide.shapes.title and slide.shapes.title.text:
                title_text = slide.shapes.title.text.strip()
            lines: list[str] = []
            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue
                if slide.shapes.title and shape == slide.shapes.title:
                    continue
                for para in shape.text_frame.paragraphs:
                    txt = para.text.strip()
                    if txt:
                        lines.append(txt)
            items.append(
                {
                    "index": idx,
                    "title": title_text or f"Slide {idx}",
                    "content_lines": lines,
                    "image_url": None,
                }
            )
        return items

    def _extract_docx_sections(self, file_path: str) -> list[dict]:
        from docx import Document

        doc = Document(file_path)
        sections: list[dict] = []
        current_title = "Nội dung tài liệu"
        current_lines: list[str] = []

        for para in doc.paragraphs:
            txt = para.text.strip()
            if not txt:
                continue
            style_name = (para.style.name or "").lower() if para.style else ""
            if "heading" in style_name:
                if current_lines:
                    sections.append(
                        {
                            "index": len(sections) + 1,
                            "title": current_title,
                            "content_lines": current_lines,
                            "image_url": None,
                        }
                    )
                    current_lines = []
                current_title = txt
            else:
                current_lines.append(txt)

        if current_lines or not sections:
            sections.append(
                {
                    "index": len(sections) + 1,
                    "title": current_title,
                    "content_lines": current_lines or ["(Tài liệu chưa có nội dung văn bản)"],
                    "image_url": None,
                }
            )
        return sections

    def _extract_markdown_sections(self, file_path: str) -> list[dict]:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()

        sections: list[dict] = []
        current_title = "Giới thiệu"
        current_lines: list[str] = []

        for line in raw.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                heading_text = stripped.lstrip("#").strip()
                if current_lines:
                    sections.append(
                        {
                            "index": len(sections) + 1,
                            "title": current_title,
                            "content_lines": current_lines,
                            "image_url": None,
                        }
                    )
                    current_lines = []
                current_title = heading_text or current_title
            elif stripped:
                current_lines.append(stripped)

        if current_lines or not sections:
            sections.append(
                {
                    "index": len(sections) + 1,
                    "title": current_title,
                    "content_lines": current_lines or ["(Tài liệu trống)"],
                    "image_url": None,
                }
            )
        return sections

    async def get_material_structured_content(
        self,
        course_id: uuid.UUID,
        material_id: uuid.UUID,
        user_id: uuid.UUID,
        is_admin: bool = False,
    ) -> dict:
        """Extract paginated/sectioned structure for PDF, PPTX, DOCX, and Markdown materials."""
        file_path = await self.get_material_file_path(
            course_id=course_id,
            material_id=material_id,
            user_id=user_id,
            is_admin=is_admin,
            mark_completed=False,
        )
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            items = self._extract_pdf_pages(file_path, course_id, material_id)
            kind = "PDF_PAGES"
        elif ext in (".pptx", ".ppt"):
            items = self._extract_pptx_slides(file_path)
            kind = "SLIDE_DECK"
        elif ext in (".docx", ".doc"):
            items = self._extract_docx_sections(file_path)
            kind = "DOC_SECTIONS"
        elif ext in (".md", ".txt"):
            items = self._extract_markdown_sections(file_path)
            kind = "DOC_SECTIONS"
        else:
            items = []
            kind = "UNSUPPORTED"

        return {
            "material_id": material_id,
            "content_kind": kind,
            "total_items": len(items),
            "items": items,
        }

    async def get_pdf_page_image_path(
        self,
        course_id: uuid.UUID,
        material_id: uuid.UUID,
        page_index: int,
        user_id: uuid.UUID,
        is_admin: bool = False,
    ) -> str:
        """Return rendered PNG file path for a specific 1-based PDF page."""
        file_path = await self.get_material_file_path(
            course_id=course_id,
            material_id=material_id,
            user_id=user_id,
            is_admin=is_admin,
            mark_completed=False,
        )
        if os.path.splitext(file_path)[1].lower() != ".pdf":
            raise LearningMaterialNotFoundException("Học liệu không phải định dạng PDF.")

        cache_dir = self._pdf_cache_dir(material_id)
        img_path = os.path.join(cache_dir, f"page_{page_index}.png")
        if not os.path.exists(img_path):
            self._extract_pdf_pages(file_path, course_id, material_id)
        if not os.path.exists(img_path):
            raise LearningMaterialNotFoundException(f"Không tìm thấy trang {page_index}.")
        return img_path

    async def complete_material(
        self,
        course_id: uuid.UUID,
        material_id: uuid.UUID,
        user_id: uuid.UUID,
        is_admin: bool = False,
    ) -> None:
        """Mark a learning material as completed by the student to unlock downstream modules."""
        role = await self.course_service.assert_course_role(
            course_id=course_id,
            user_id=user_id,
            allowed_roles=[ContextualRole.INSTRUCTOR, ContextualRole.STUDENT],
            is_admin=is_admin,
        )

        mat = await self.repo.get_material(material_id)
        if not mat:
            raise LearningMaterialNotFoundException()

        mod = await self.repo.get_module(mat.module_id)
        if not mod or mod.course_id != course_id:
            raise LearningMaterialNotFoundException()

        is_student = (role == ContextualRole.STUDENT and not is_admin)
        if is_student:
            if not mat.is_published or not mod.is_published:
                raise LearningMaterialNotFoundException()
            mod_map = {mod.id: mod.title}
            if mod.prerequisite_module_id:
                prereq_obj = await self.repo.get_module(mod.prerequisite_module_id, include_materials=False)
                if prereq_obj:
                    mod_map[prereq_obj.id] = prereq_obj.title
            is_locked, lock_reason = await LearningModuleService(self.db, self.repo)._resolve_student_lock(
                mod, user_id, mod_map
            )
            if is_locked:
                raise ModuleLockedException(lock_reason or "Bài học đang tạm khóa.")

            unpassed_ids = await self.repo.get_unpassed_blocking_checkpoints(material_id, user_id)
            if unpassed_ids:
                raise UncompletedCheckpointsException(
                    f"Cần vượt qua {len(unpassed_ids)} mốc kiểm tra bắt buộc trước khi hoàn thành học liệu."
                )

        await self.repo.mark_material_completed(user_id, material_id)


class LearningCheckpointService:
    """Manages interactive checkpoints on video timelines and document sections (Task T2-P-M2-03)."""

    def __init__(self, db: AsyncSession, repo: Optional[LearningRepository] = None):
        self.db = db
        self.repo = repo or LearningRepository(db)
        self.course_service = CoursePublicService(db)

    async def _get_material_in_course(self, course_id: uuid.UUID, material_id: uuid.UUID) -> LearningMaterial:
        mat = await self.repo.get_material(material_id)
        if not mat:
            raise LearningMaterialNotFoundException()
        mod = await self.repo.get_module(mat.module_id, include_materials=False)
        if not mod or mod.course_id != course_id:
            raise LearningMaterialNotFoundException()
        return mat

    async def _assert_video_spacing(
        self,
        material_id: uuid.UUID,
        stop_time_seconds: Optional[int],
        exclude_checkpoint_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Ensure video checkpoints are at least 5 seconds apart."""
        if stop_time_seconds is None:
            return
        existing = await self.repo.list_checkpoints(material_id)
        for chk in existing:
            if exclude_checkpoint_id and chk.id == exclude_checkpoint_id:
                continue
            if chk.stop_time_seconds is not None and abs(chk.stop_time_seconds - stop_time_seconds) < 5:
                raise CheckpointSpacingException()

    async def list_checkpoints(
        self,
        course_id: uuid.UUID,
        material_id: uuid.UUID,
        user_id: uuid.UUID,
        is_admin: bool = False,
    ) -> List[CheckpointInstructorResponse] | List[CheckpointStudentResponse]:
        """List checkpoints for a material. Instructors see answers; students see pass status."""
        role = await self.course_service.assert_course_role(
            course_id=course_id,
            user_id=user_id,
            allowed_roles=[ContextualRole.INSTRUCTOR, ContextualRole.STUDENT],
            is_admin=is_admin,
        )
        await self._get_material_in_course(course_id, material_id)
        checkpoints = await self.repo.list_checkpoints(material_id)

        if role == ContextualRole.INSTRUCTOR or is_admin:
            return [CheckpointInstructorResponse.model_validate(c) for c in checkpoints]

        attempt_map = await self.repo.get_student_attempts_for_checkpoints(
            [c.id for c in checkpoints], user_id
        )
        results: List[CheckpointStudentResponse] = []
        for c in checkpoints:
            item = CheckpointStudentResponse.model_validate(c)
            item.is_passed = bool(attempt_map.get(c.id, False))
            results.append(item)
        return results

    async def create_checkpoint(
        self,
        course_id: uuid.UUID,
        material_id: uuid.UUID,
        payload: CheckpointCreate,
        user_id: uuid.UUID,
        is_admin: bool = False,
    ) -> CheckpointInstructorResponse:
        """Create an interactive checkpoint on a material (Instructor only)."""
        await self.course_service.assert_course_role(
            course_id=course_id,
            user_id=user_id,
            allowed_roles=[ContextualRole.INSTRUCTOR],
            is_admin=is_admin,
        )
        await self._get_material_in_course(course_id, material_id)
        await self._assert_video_spacing(material_id, payload.stop_time_seconds)

        chk = MaterialCheckpoint(
            material_id=material_id,
            lo_id=payload.lo_id,
            stop_time_seconds=payload.stop_time_seconds,
            section_index=payload.section_index,
            question_text=payload.question_text,
            question_type=payload.question_type,
            options=payload.options,
            correct_option=payload.correct_option.strip().upper(),
            expected_concept=payload.expected_concept or payload.question_text[:200],
            is_blocking=payload.is_blocking,
            time_limit_seconds=payload.time_limit_seconds,
            rewind_seconds=payload.rewind_seconds,
        )
        created = await self.repo.create_checkpoint(chk)
        return CheckpointInstructorResponse.model_validate(created)

    async def update_checkpoint(
        self,
        course_id: uuid.UUID,
        checkpoint_id: uuid.UUID,
        payload: CheckpointUpdate,
        user_id: uuid.UUID,
        is_admin: bool = False,
    ) -> CheckpointInstructorResponse:
        """Update an existing checkpoint (Instructor only)."""
        await self.course_service.assert_course_role(
            course_id=course_id,
            user_id=user_id,
            allowed_roles=[ContextualRole.INSTRUCTOR],
            is_admin=is_admin,
        )
        chk = await self.repo.get_checkpoint(checkpoint_id)
        if not chk:
            raise CheckpointNotFoundException()
        await self._get_material_in_course(course_id, chk.material_id)

        fields = payload.model_fields_set
        if "stop_time_seconds" in fields:
            await self._assert_video_spacing(
                chk.material_id, payload.stop_time_seconds, exclude_checkpoint_id=chk.id
            )
            chk.stop_time_seconds = payload.stop_time_seconds
        if "section_index" in fields:
            chk.section_index = payload.section_index
        if "question_text" in fields and payload.question_text is not None:
            chk.question_text = payload.question_text
        if "options" in fields and payload.options is not None:
            chk.options = payload.options
        if "correct_option" in fields and payload.correct_option is not None:
            chk.correct_option = payload.correct_option.strip().upper()
        if "expected_concept" in fields:
            chk.expected_concept = payload.expected_concept
        if "is_blocking" in fields and payload.is_blocking is not None:
            chk.is_blocking = payload.is_blocking
        if "time_limit_seconds" in fields and payload.time_limit_seconds is not None:
            chk.time_limit_seconds = payload.time_limit_seconds
        if "rewind_seconds" in fields and payload.rewind_seconds is not None:
            chk.rewind_seconds = payload.rewind_seconds
        if "lo_id" in fields:
            chk.lo_id = payload.lo_id

        updated = await self.repo.update_checkpoint(chk)
        return CheckpointInstructorResponse.model_validate(updated)

    async def delete_checkpoint(
        self,
        course_id: uuid.UUID,
        checkpoint_id: uuid.UUID,
        user_id: uuid.UUID,
        is_admin: bool = False,
    ) -> None:
        """Delete a checkpoint (Instructor only)."""
        await self.course_service.assert_course_role(
            course_id=course_id,
            user_id=user_id,
            allowed_roles=[ContextualRole.INSTRUCTOR],
            is_admin=is_admin,
        )
        chk = await self.repo.get_checkpoint(checkpoint_id)
        if not chk:
            raise CheckpointNotFoundException()
        await self._get_material_in_course(course_id, chk.material_id)
        await self.repo.delete_checkpoint(chk)

    async def submit_checkpoint(
        self,
        course_id: uuid.UUID,
        checkpoint_id: uuid.UUID,
        payload: CheckpointSubmitRequest,
        user_id: uuid.UUID,
        is_admin: bool = False,
    ) -> CheckpointSubmitResponse:
        """Evaluate student answer to a checkpoint and record pass status."""
        await self.course_service.assert_course_role(
            course_id=course_id,
            user_id=user_id,
            allowed_roles=[ContextualRole.INSTRUCTOR, ContextualRole.STUDENT],
            is_admin=is_admin,
        )
        chk = await self.repo.get_checkpoint(checkpoint_id)
        if not chk:
            raise CheckpointNotFoundException()
        await self._get_material_in_course(course_id, chk.material_id)

        selected = payload.selected_option.strip().upper()
        expected = (chk.correct_option or "").strip().upper()
        is_correct = bool(expected and selected == expected)

        attempt = await self.repo.upsert_checkpoint_attempt(
            user_id=user_id,
            checkpoint_id=chk.id,
            selected_option=selected,
            is_correct=is_correct,
        )

        if is_correct:
            msg = "Chính xác! Bạn đã vượt qua mốc kiểm tra này."
        else:
            msg = f"Chưa chính xác! Hệ thống sẽ lùi lại {chk.rewind_seconds} giây để bạn ôn lại kiến thức."

        return CheckpointSubmitResponse(
            checkpoint_id=chk.id,
            is_correct=is_correct,
            is_passed=attempt.is_correct,
            rewind_seconds=0 if is_correct else chk.rewind_seconds,
            message=msg,
        )
