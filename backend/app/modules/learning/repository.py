# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Asynchronous database repository for Learning Modules, Materials, and LO Reference checks."""

from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.modules.learning.models import (
    LearningMaterial,
    LearningModule,
    MaterialCheckpoint,
    StudentCheckpointAttempt,
)


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

    # -------------------------------------------------------------------------
    # Material Checkpoints (Task T2-P-M2-03)
    # -------------------------------------------------------------------------
    async def get_checkpoint(self, checkpoint_id: uuid.UUID) -> Optional[MaterialCheckpoint]:
        """Fetch checkpoint by id."""
        stmt = select(MaterialCheckpoint).where(MaterialCheckpoint.id == checkpoint_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_checkpoints(self, material_id: uuid.UUID) -> List[MaterialCheckpoint]:
        """List all checkpoints for a learning material ordered by time/section."""
        stmt = (
            select(MaterialCheckpoint)
            .where(MaterialCheckpoint.material_id == material_id)
            .order_by(MaterialCheckpoint.stop_time_seconds.asc().nulls_last(), MaterialCheckpoint.section_index.asc().nulls_last())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_checkpoint(self, checkpoint: MaterialCheckpoint) -> MaterialCheckpoint:
        """Insert a new checkpoint."""
        self.db.add(checkpoint)
        await self.db.flush()
        return checkpoint

    async def update_checkpoint(self, checkpoint: MaterialCheckpoint) -> MaterialCheckpoint:
        """Update an existing checkpoint."""
        await self.db.flush()
        return checkpoint

    async def delete_checkpoint(self, checkpoint: MaterialCheckpoint) -> None:
        """Delete a checkpoint."""
        await self.db.delete(checkpoint)
        await self.db.flush()

    async def get_student_attempts_for_checkpoints(
        self,
        checkpoint_ids: List[uuid.UUID],
        user_id: uuid.UUID,
    ) -> Dict[uuid.UUID, bool]:
        """Return dict of checkpoint_id -> is_passed for a student."""
        if not checkpoint_ids:
            return {}
        stmt = select(StudentCheckpointAttempt.checkpoint_id, StudentCheckpointAttempt.is_correct).where(
            StudentCheckpointAttempt.user_id == user_id,
            StudentCheckpointAttempt.checkpoint_id.in_(checkpoint_ids),
        )
        result = await self.db.execute(stmt)
        return {row[0]: row[1] for row in result.fetchall()}

    async def upsert_checkpoint_attempt(
        self,
        user_id: uuid.UUID,
        checkpoint_id: uuid.UUID,
        selected_option: str,
        is_correct: bool,
    ) -> StudentCheckpointAttempt:
        """Record student attempt and preserve pass status if previously passed."""
        stmt = select(StudentCheckpointAttempt).where(
            StudentCheckpointAttempt.user_id == user_id,
            StudentCheckpointAttempt.checkpoint_id == checkpoint_id,
        )
        result = await self.db.execute(stmt)
        attempt = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if attempt:
            attempt.attempt_count += 1
            attempt.selected_option = selected_option
            attempt.updated_at = now
            if is_correct or attempt.is_correct:
                attempt.is_correct = True
                if not attempt.passed_at:
                    attempt.passed_at = now
        else:
            attempt = StudentCheckpointAttempt(
                user_id=user_id,
                checkpoint_id=checkpoint_id,
                selected_option=selected_option,
                is_correct=is_correct,
                attempt_count=1,
                passed_at=now if is_correct else None,
                updated_at=now,
            )
            self.db.add(attempt)

        await self.db.flush()
        return attempt

    async def get_unpassed_blocking_checkpoints(
        self,
        material_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> List[uuid.UUID]:
        """Return list of blocking checkpoint IDs that student has not yet passed."""
        # Find all blocking checkpoints for this material
        chk_stmt = select(MaterialCheckpoint.id).where(
            MaterialCheckpoint.material_id == material_id,
            MaterialCheckpoint.is_blocking.is_(True),
        )
        chk_res = await self.db.execute(chk_stmt)
        blocking_ids = [row[0] for row in chk_res.fetchall()]

        if not blocking_ids:
            return []

        # Find which blocking checkpoints have is_correct = True
        pass_stmt = select(StudentCheckpointAttempt.checkpoint_id).where(
            StudentCheckpointAttempt.user_id == user_id,
            StudentCheckpointAttempt.checkpoint_id.in_(blocking_ids),
            StudentCheckpointAttempt.is_correct.is_(True),
        )
        pass_res = await self.db.execute(pass_stmt)
        passed_ids = set(row[0] for row in pass_res.fetchall())

        return [cid for cid in blocking_ids if cid not in passed_ids]
