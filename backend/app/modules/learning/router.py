# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""REST API router for Learning Modules, Materials, and File Uploads."""

import mimetypes
import os
from typing import List, Union
import uuid
from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.identity.dependencies import CurrentUser, get_current_user
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
    ModuleReorderRequest,
    ModuleResponse,
    ModuleUpdate,
    PublishToggleRequest,
)
from app.modules.learning.service import (
    LearningCheckpointService,
    LearningMaterialService,
    LearningModuleService,
)

router = APIRouter(
    prefix="/api/v1/courses/{course_id}/learning",
    tags=["Learning Materials & Socratic AI"],
)


def _is_admin(current_user: CurrentUser) -> bool:
    """Resolve system admin privileges safely from User.system_role."""
    return (getattr(current_user.user, "system_role", "") or "").upper() == "ADMIN"


_MEDIA_TYPE_MAP = {
    ".pdf": "application/pdf",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".md": "text/markdown; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".ppt": "application/vnd.ms-powerpoint",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
}


def _resolve_media_type(file_path: str) -> str:
    """Resolve MIME media_type for inline material streaming."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in _MEDIA_TYPE_MAP:
        return _MEDIA_TYPE_MAP[ext]
    guessed, _ = mimetypes.guess_type(file_path)
    return guessed or "application/octet-stream"


# -----------------------------------------------------------------------------
# Module Routes
# -----------------------------------------------------------------------------
@router.get("/modules", response_model=List[ModuleResponse])
async def list_course_modules(
    course_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List all modules for a course. Instructors see all; students see published and unlocked."""
    service = LearningModuleService(db)
    return await service.list_modules(
        course_id=course_id,
        user_id=current_user.user.id,
        is_admin=_is_admin(current_user),
    )


@router.post("/modules", response_model=ModuleResponse, status_code=status.HTTP_201_CREATED)
async def create_course_module(
    course_id: uuid.UUID,
    payload: ModuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Create a new chapter/module in course (Instructor only)."""
    service = LearningModuleService(db)
    return await service.create_module(
        course_id=course_id,
        payload=payload,
        user_id=current_user.user.id,
        is_admin=_is_admin(current_user),
    )


@router.put("/modules/reorder", response_model=List[ModuleResponse])
async def reorder_course_modules(
    course_id: uuid.UUID,
    payload: ModuleReorderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Batch reorder module sequence index (Instructor only)."""
    service = LearningModuleService(db)
    return await service.reorder_modules(
        course_id=course_id,
        ordered_ids=payload.module_ids,
        user_id=current_user.user.id,
        is_admin=_is_admin(current_user),
    )


@router.get("/modules/{module_id}", response_model=ModuleResponse)
async def get_module_detail(
    course_id: uuid.UUID,
    module_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get single module detail (enforces lock guards for students)."""
    service = LearningModuleService(db)
    return await service.get_module_detail(
        course_id=course_id,
        module_id=module_id,
        user_id=current_user.user.id,
        is_admin=_is_admin(current_user),
    )


@router.put("/modules/{module_id}", response_model=ModuleResponse)
async def update_module_metadata(
    course_id: uuid.UUID,
    module_id: uuid.UUID,
    payload: ModuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update module title, unlock date, or prerequisite (Instructor only)."""
    service = LearningModuleService(db)
    return await service.update_module(
        course_id=course_id,
        module_id=module_id,
        payload=payload,
        user_id=current_user.user.id,
        is_admin=_is_admin(current_user),
    )


@router.delete("/modules/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course_module(
    course_id: uuid.UUID,
    module_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Delete module and cascade remove all materials (Instructor only)."""
    service = LearningModuleService(db)
    await service.delete_module(
        course_id=course_id,
        module_id=module_id,
        user_id=current_user.user.id,
        is_admin=_is_admin(current_user),
    )


@router.patch("/modules/{module_id}/publish", response_model=ModuleResponse)
async def toggle_module_publish_status(
    course_id: uuid.UUID,
    module_id: uuid.UUID,
    payload: PublishToggleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Toggle module published visibility (Instructor only)."""
    service = LearningModuleService(db)
    return await service.toggle_publish(
        course_id=course_id,
        module_id=module_id,
        is_published=payload.is_published,
        user_id=current_user.user.id,
        is_admin=_is_admin(current_user),
    )


# -----------------------------------------------------------------------------
# Learning Material Routes
# -----------------------------------------------------------------------------
@router.post("/modules/{module_id}/materials", response_model=MaterialResponse, status_code=status.HTTP_201_CREATED)
async def create_learning_material(
    course_id: uuid.UUID,
    module_id: uuid.UUID,
    payload: MaterialCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Add a learning material to a module (Instructor only)."""
    service = LearningMaterialService(db)
    return await service.create_material(
        course_id=course_id,
        module_id=module_id,
        payload=payload,
        user_id=current_user.user.id,
        is_admin=_is_admin(current_user),
    )


@router.post("/modules/{module_id}/materials/upload", response_model=MaterialUploadResponse)
async def upload_material_file(
    course_id: uuid.UUID,
    module_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Upload material file with BR-STORAGE-02 quota checking (Instructor only)."""
    service = LearningMaterialService(db)
    return await service.upload_material_file(
        course_id=course_id,
        module_id=module_id,
        file=file,
        user_id=current_user.user.id,
        is_admin=_is_admin(current_user),
    )


@router.get("/materials/{material_id}", response_model=MaterialResponse)
async def get_material_detail(
    course_id: uuid.UUID,
    material_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get single learning material detail."""
    service = LearningMaterialService(db)
    return await service.get_material_detail(
        course_id=course_id,
        material_id=material_id,
        user_id=current_user.user.id,
        is_admin=_is_admin(current_user),
    )


@router.get("/materials/{material_id}/download")
async def download_material_file(
    course_id: uuid.UUID,
    material_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Download physical file for a learning material (enforces lock guards for students)."""
    service = LearningMaterialService(db)
    file_path = await service.get_material_file_path(
        course_id=course_id,
        material_id=material_id,
        user_id=current_user.user.id,
        is_admin=_is_admin(current_user),
    )
    return FileResponse(
        path=file_path,
        filename=os.path.basename(file_path),
    )


@router.get("/materials/{material_id}/preview")
async def preview_material_file(
    course_id: uuid.UUID,
    material_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Stream physical file inline for browser preview (enforces lock guards for students)."""
    service = LearningMaterialService(db)
    file_path = await service.get_material_file_path(
        course_id=course_id,
        material_id=material_id,
        user_id=current_user.user.id,
        is_admin=_is_admin(current_user),
    )
    filename = os.path.basename(file_path)
    media_type = _resolve_media_type(file_path)
    return FileResponse(
        path=file_path,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.put("/materials/{material_id}", response_model=MaterialResponse)
async def update_material_metadata(
    course_id: uuid.UUID,
    material_id: uuid.UUID,
    payload: MaterialUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update learning material metadata (Instructor only)."""
    service = LearningMaterialService(db)
    return await service.update_material(
        course_id=course_id,
        material_id=material_id,
        payload=payload,
        user_id=current_user.user.id,
        is_admin=_is_admin(current_user),
    )


@router.delete("/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_learning_material(
    course_id: uuid.UUID,
    material_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Delete learning material (Instructor only)."""
    service = LearningMaterialService(db)
    await service.delete_material(
        course_id=course_id,
        material_id=material_id,
        user_id=current_user.user.id,
        is_admin=_is_admin(current_user),
    )


@router.patch("/materials/{material_id}/publish", response_model=MaterialResponse)
async def toggle_material_publish_status(
    course_id: uuid.UUID,
    material_id: uuid.UUID,
    payload: PublishToggleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Toggle material published visibility (Instructor only)."""
    service = LearningMaterialService(db)
    return await service.toggle_publish(
        course_id=course_id,
        material_id=material_id,
        is_published=payload.is_published,
        user_id=current_user.user.id,
        is_admin=_is_admin(current_user),
    )


@router.post("/materials/{material_id}/complete")
async def complete_learning_material(
    course_id: uuid.UUID,
    material_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Record material completion for student to satisfy module prerequisites."""
    service = LearningMaterialService(db)
    await service.complete_material(
        course_id=course_id,
        material_id=material_id,
        user_id=current_user.user.id,
        is_admin=_is_admin(current_user),
    )
    return {"status": "completed", "material_id": str(material_id)}


# -----------------------------------------------------------------------------
# Interactive Checkpoint Routes (Task T2-P-M2-03)
# -----------------------------------------------------------------------------
@router.get(
    "/materials/{material_id}/checkpoints",
    response_model=Union[List[CheckpointInstructorResponse], List[CheckpointStudentResponse]],
)
async def list_material_checkpoints(
    course_id: uuid.UUID,
    material_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List checkpoints for a material. Students receive pass status without correct_option."""
    service = LearningCheckpointService(db)
    return await service.list_checkpoints(
        course_id=course_id,
        material_id=material_id,
        user_id=current_user.user.id,
        is_admin=_is_admin(current_user),
    )


@router.post(
    "/materials/{material_id}/checkpoints",
    response_model=CheckpointInstructorResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_material_checkpoint(
    course_id: uuid.UUID,
    material_id: uuid.UUID,
    payload: CheckpointCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Create a new interactive checkpoint on a video or document (Instructor only)."""
    service = LearningCheckpointService(db)
    return await service.create_checkpoint(
        course_id=course_id,
        material_id=material_id,
        payload=payload,
        user_id=current_user.user.id,
        is_admin=_is_admin(current_user),
    )


@router.put("/checkpoints/{checkpoint_id}", response_model=CheckpointInstructorResponse)
async def update_material_checkpoint(
    course_id: uuid.UUID,
    checkpoint_id: uuid.UUID,
    payload: CheckpointUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update an existing checkpoint (Instructor only)."""
    service = LearningCheckpointService(db)
    return await service.update_checkpoint(
        course_id=course_id,
        checkpoint_id=checkpoint_id,
        payload=payload,
        user_id=current_user.user.id,
        is_admin=_is_admin(current_user),
    )


@router.delete("/checkpoints/{checkpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material_checkpoint(
    course_id: uuid.UUID,
    checkpoint_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Delete an interactive checkpoint (Instructor only)."""
    service = LearningCheckpointService(db)
    await service.delete_checkpoint(
        course_id=course_id,
        checkpoint_id=checkpoint_id,
        user_id=current_user.user.id,
        is_admin=_is_admin(current_user),
    )


@router.post("/checkpoints/{checkpoint_id}/submit", response_model=CheckpointSubmitResponse)
async def submit_checkpoint_answer(
    course_id: uuid.UUID,
    checkpoint_id: uuid.UUID,
    payload: CheckpointSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Submit student answer to a checkpoint and record pass status."""
    service = LearningCheckpointService(db)
    return await service.submit_checkpoint(
        course_id=course_id,
        checkpoint_id=checkpoint_id,
        payload=payload,
        user_id=current_user.user.id,
        is_admin=_is_admin(current_user),
    )
