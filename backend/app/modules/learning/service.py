# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Business logic services for Learning Modules and Learning Materials."""

from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.course.enums import ContextualRole
from app.modules.course.public_api import CoursePublicService
from app.modules.learning.exceptions import (
    LearningMaterialNotFoundException,
    LearningModuleNotFoundException,
    ModuleCircularDependencyException,
    ModuleLockedException,
)
from app.modules.learning.models import LearningMaterial, LearningModule
from app.modules.learning.repository import LearningRepository
from app.modules.learning.schemas import (
    MaterialCreate,
    MaterialResponse,
    MaterialUpdate,
    ModuleCreate,
    ModuleResponse,
    ModuleUpdate,
)


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

        if payload.prerequisite_module_id is not None:
            await self._assert_no_circular_dependency(course_id, mod.id, payload.prerequisite_module_id)
            mod.prerequisite_module_id = payload.prerequisite_module_id

        if payload.title is not None:
            mod.title = payload.title.strip()
        if payload.order_index is not None:
            mod.order_index = payload.order_index
        if payload.unlock_at is not None:
            mod.unlock_at = payload.unlock_at
        if payload.prerequisite_module_id is not None:
            mod.prerequisite_module_id = payload.prerequisite_module_id
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

        if payload.title is not None:
            mat.title = payload.title.strip()
        if payload.material_type is not None:
            mat.material_type = payload.material_type.value
        if payload.lo_id is not None:
            los = await self.course_service.get_learning_objectives(course_id)
            if not any(lo.id == payload.lo_id for lo in los):
                raise LearningMaterialNotFoundException("Chuẩn đầu ra không tồn tại trong môn học.")
            mat.lo_id = payload.lo_id
        if payload.file_url is not None:
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
