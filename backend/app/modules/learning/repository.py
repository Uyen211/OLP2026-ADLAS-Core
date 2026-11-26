# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Asynchronous database repository for Learning Modules, Materials, and LO Reference checks."""

from typing import List, Optional
import uuid
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.modules.learning.models import LearningMaterial, LearningModule


class LearningRepository:
    """Encapsulates async SQL queries for learning schema."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # -------------------------------------------------------------------------
    # Modules
    # -------------------------------------------------------------------------
    async def get_module(
        self,
        module_id: uuid.UUID,
        include_materials: bool = True,
    ) -> Optional[LearningModule]:
        """Fetch module by id with optional eager loading of materials."""
        stmt = select(LearningModule).where(LearningModule.id == module_id)
        if include_materials:
            stmt = stmt.options(selectinload(LearningModule.materials))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_modules(
        self,
        course_id: uuid.UUID,
        is_published_only: bool = False,
    ) -> List[LearningModule]:
        """List all modules for a course, ordered by order_index and created_at."""
        stmt = (
            select(LearningModule)
            .where(LearningModule.course_id == course_id)
            .options(selectinload(LearningModule.materials))
            .order_by(LearningModule.order_index.asc(), LearningModule.created_at.asc())
        )
        if is_published_only:
            stmt = stmt.where(LearningModule.is_published.is_(True))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_module(self, module: LearningModule) -> LearningModule:
        """Insert new module into learning.modules."""
        self.db.add(module)
        await self.db.flush()
        return module

    async def update_module(self, module: LearningModule) -> LearningModule:
        """Update existing module."""
        await self.db.flush()
        return module

    async def delete_module(self, module: LearningModule) -> None:
        """Delete module and cascade delete materials."""
        await self.db.delete(module)
        await self.db.flush()

    async def get_max_order_index(self, course_id: uuid.UUID) -> int:
        """Get highest current order_index in a course, default 0."""
        stmt = select(func.coalesce(func.max(LearningModule.order_index), 0)).where(
            LearningModule.course_id == course_id
        )
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def reorder_modules(
        self,
        course_id: uuid.UUID,
        ordered_ids: List[uuid.UUID],
    ) -> None:
        """Batch update order_index for a course's modules."""
        for idx, mod_id in enumerate(ordered_ids, start=1):
            stmt = (
                select(LearningModule)
                .where(
                    LearningModule.id == mod_id,
                    LearningModule.course_id == course_id,
                )
            )
            res = await self.db.execute(stmt)
            mod = res.scalar_one_or_none()
            if mod:
                mod.order_index = idx
        await self.db.flush()

    # -------------------------------------------------------------------------
    # Learning Materials
    # -------------------------------------------------------------------------
    async def get_material(self, material_id: uuid.UUID) -> Optional[LearningMaterial]:
        """Fetch learning material by id."""
        stmt = select(LearningMaterial).where(LearningMaterial.id == material_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_materials(
        self,
        module_id: uuid.UUID,
        is_published_only: bool = False,
    ) -> List[LearningMaterial]:
        """List materials in a module."""
        stmt = (
            select(LearningMaterial)
            .where(LearningMaterial.module_id == module_id)
            .order_by(LearningMaterial.created_at.asc())
        )
        if is_published_only:
            stmt = stmt.where(LearningMaterial.is_published.is_(True))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_material(self, material: LearningMaterial) -> LearningMaterial:
        """Insert new material into learning.learning_materials."""
        self.db.add(material)
        await self.db.flush()
        return material

    async def update_material(self, material: LearningMaterial) -> LearningMaterial:
        """Update existing material."""
        await self.db.flush()
        return material

    async def delete_material(self, material: LearningMaterial) -> None:
        """Delete material from database."""
        await self.db.delete(material)
        await self.db.flush()

    # -------------------------------------------------------------------------
    # Cross-Context Reference Check (BR-LO-01)
    # -------------------------------------------------------------------------
    async def is_lo_referenced(self, lo_id: uuid.UUID) -> bool:
        """Check if an LO is linked to any learning material (BR-LO-01 guard)."""
        stmt = select(LearningMaterial.id).where(LearningMaterial.lo_id == lo_id).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    # -------------------------------------------------------------------------
    # Student Progress & Module Completion Check
    # -------------------------------------------------------------------------
    async def is_module_completed_by_user(
        self,
        module_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """
        Check if student has completed all mandatory materials in a module.
        If module has no mandatory materials, it is treated as completed.
        """
        # Fetch mandatory published materials
        mat_stmt = select(LearningMaterial.id).where(
            LearningMaterial.module_id == module_id,
            LearningMaterial.is_mandatory.is_(True),
            LearningMaterial.is_published.is_(True),
        )
        mat_res = await self.db.execute(mat_stmt)
        mandatory_ids = [row[0] for row in mat_res.fetchall()]

        if not mandatory_ids:
            return True

        # Check completed count in student_material_progress
        prog_stmt = text("""
            SELECT COUNT(DISTINCT material_id)
            FROM learning.student_material_progress
            WHERE user_id = :user_id
              AND material_id = ANY(:mat_ids)
              AND is_completed = TRUE
        """)
        prog_res = await self.db.execute(
            prog_stmt,
            {"user_id": str(user_id), "mat_ids": [str(m) for m in mandatory_ids]},
        )
        completed_count = prog_res.scalar() or 0
        return completed_count >= len(mandatory_ids)

    async def mark_material_completed(
        self,
        user_id: uuid.UUID,
        material_id: uuid.UUID,
    ) -> None:
        """Upsert student material completion in learning.student_material_progress."""
        stmt = text("""
            INSERT INTO learning.student_material_progress (user_id, material_id, is_completed, completed_at)
            VALUES (:user_id, :material_id, TRUE, NOW())
            ON CONFLICT (user_id, material_id)
            DO UPDATE SET is_completed = TRUE, completed_at = NOW()
        """)
        await self.db.execute(stmt, {"user_id": str(user_id), "material_id": str(material_id)})
        await self.db.flush()
