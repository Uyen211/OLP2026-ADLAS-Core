# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""REST API router for Gradebook Structure, TT08 Overview, AI Rubric Proposal, SpeedGrader, and Lock."""

import io
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.course.enums import ContextualRole
from app.modules.course.public_api import CoursePublicService
from app.modules.gradebook.ai_grader_service import AIGraderService
from app.modules.gradebook.enums import SpeedGraderFilter
from app.modules.gradebook.exceptions import GradebookForbiddenException, GradebookNotFoundException
from app.modules.gradebook.schemas import (
    CellGradeDTO,
    ClassGradebookOverviewResponse,
    EmergencyUnlockRequest,
    GradeAuditLogResponse,
    GradebookLockPreviewResponse,
    GradebookLockRequest,
    GradebookLockResponse,
    GradebookStructureResponse,
    GradebookStructureSaveRequest,
    GradeColumnCreateRequest,
    GradeColumnResponse,
    GradeGroupDeleteRequest,
    ManualGradeUpsertRequest,
    PostGradesRequest,
    PostGradesResponse,
    RubricProposalResponse,
    SpeedGraderDraftRequest,
    SpeedGraderSaveGradeRequest,
    SpeedGraderSubmissionListResponse,
    SpeedGraderWorkspaceResponse,
    StudentMyGradesResponse,
    VersionDiffResponse,
)
from app.modules.gradebook.sealing_service import GradebookSealingService
from app.modules.gradebook.speedgrader_service import SpeedGraderService
from app.modules.gradebook.structure_service import GradebookStructureService
from app.modules.identity.dependencies import CurrentUser, get_current_user

router = APIRouter(prefix="/api/v1/gradebook", tags=["Gradebook & SpeedGrader"])


def _is_admin(current_user: CurrentUser) -> bool:
    return (current_user.user.system_role or "").upper() in {"ADMIN", "SUPER_ADMIN"}


async def _require_instructor(
    db: AsyncSession,
    course_id: uuid.UUID,
    current_user: CurrentUser,
) -> None:
    await CoursePublicService(db).assert_course_role(
        course_id=course_id,
        user_id=current_user.user.id,
        allowed_roles=[ContextualRole.INSTRUCTOR],
        is_admin=_is_admin(current_user),
    )


async def _require_course_member(
    db: AsyncSession,
    course_id: uuid.UUID,
    current_user: CurrentUser,
) -> None:
    await CoursePublicService(db).assert_course_role(
        course_id=course_id,
        user_id=current_user.user.id,
        allowed_roles=[ContextualRole.INSTRUCTOR, ContextualRole.STUDENT],
        is_admin=_is_admin(current_user),
    )


# ---------------------------------------------------------------------------
# T2-P-M5-01: Dynamic Gradebook Structure
# ---------------------------------------------------------------------------
@router.get("/courses/{course_id}/structure", response_model=GradebookStructureResponse)
async def get_gradebook_structure(
    course_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    await _require_instructor(db, course_id, current_user)
    return await GradebookStructureService(db).get_structure(course_id)


@router.put("/courses/{course_id}/structure", response_model=GradebookStructureResponse)
async def save_gradebook_structure(
    course_id: uuid.UUID,
    payload: GradebookStructureSaveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    await _require_instructor(db, course_id, current_user)
    return await GradebookStructureService(db).save_structure(
        course_id=course_id,
        payload=payload,
        actor_id=current_user.user.id,
    )


@router.delete("/courses/{course_id}/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gradebook_group(
    course_id: uuid.UUID,
    group_id: uuid.UUID,
    payload: Optional[GradeGroupDeleteRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    await _require_instructor(db, course_id, current_user)
    await GradebookStructureService(db).delete_group(
        course_id=course_id,
        group_id=group_id,
        confirmation_text=payload.confirmation_text if payload else None,
        actor_id=current_user.user.id,
    )


@router.post(
    "/courses/{course_id}/columns",
    response_model=GradeColumnResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_gradebook_column(
    course_id: uuid.UUID,
    payload: GradeColumnCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    await _require_instructor(db, course_id, current_user)
    return await GradebookStructureService(db).create_column(
        course_id=course_id,
        payload=payload,
        actor_id=current_user.user.id,
    )


@router.post("/courses/{course_id}/sync-items")
async def sync_course_gradebook_items(
    course_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    await _require_instructor(db, course_id, current_user)
    return await GradebookStructureService(db).sync_course_items(
        course_id=course_id,
        actor_id=current_user.user.id,
    )


# ---------------------------------------------------------------------------
# T2-P-M5-02: Class Overview, Manual Entry & Student Muted View
# ---------------------------------------------------------------------------
@router.get("/courses/{course_id}/overview", response_model=ClassGradebookOverviewResponse)
async def get_class_gradebook_overview(
    course_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    await _require_instructor(db, course_id, current_user)
    return await GradebookStructureService(db).get_class_overview(course_id)


@router.get("/courses/{course_id}/my-grades", response_model=StudentMyGradesResponse)
async def get_student_my_grades(
    course_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    await _require_course_member(db, course_id, current_user)
    return await GradebookStructureService(db).get_student_my_grades(
        course_id=course_id,
        student_id=current_user.user.id,
    )


@router.put("/courses/{course_id}/columns/{column_id}/grades", response_model=CellGradeDTO)
async def upsert_manual_column_grade(
    course_id: uuid.UUID,
    column_id: uuid.UUID,
    payload: ManualGradeUpsertRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    await _require_instructor(db, course_id, current_user)
    return await GradebookStructureService(db).upsert_manual_grade(
        course_id=course_id,
        column_id=column_id,
        payload=payload,
        actor_id=current_user.user.id,
    )


# ---------------------------------------------------------------------------
# T2-P-M5-05: Muted Policy, Poka-Yoke Lock & Audit Logs
# ---------------------------------------------------------------------------
@router.post("/courses/{course_id}/columns/{column_id}/post-grades", response_model=PostGradesResponse)
async def post_column_grades(
    course_id: uuid.UUID,
    column_id: uuid.UUID,
    payload: PostGradesRequest = PostGradesRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    await _require_instructor(db, course_id, current_user)
    return await GradebookSealingService(db).post_column_grades(
        course_id=course_id,
        column_id=column_id,
        payload=payload,
        actor_id=current_user.user.id,
    )


@router.post("/courses/{course_id}/columns/{column_id}/mute", response_model=PostGradesResponse)
async def mute_column_grades(
    course_id: uuid.UUID,
    column_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    await _require_instructor(db, course_id, current_user)
    return await GradebookSealingService(db).mute_column_grades(
        course_id=course_id,
        column_id=column_id,
        actor_id=current_user.user.id,
    )


@router.get("/courses/{course_id}/lock-preview", response_model=GradebookLockPreviewResponse)
async def get_gradebook_lock_preview(
    course_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    await _require_instructor(db, course_id, current_user)
    return await GradebookSealingService(db).get_lock_preview(course_id)


@router.post("/courses/{course_id}/lock", response_model=GradebookLockResponse)
async def lock_course_gradebook(
    course_id: uuid.UUID,
    payload: GradebookLockRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    await _require_instructor(db, course_id, current_user)
    return await GradebookSealingService(db).lock_course_gradebook(
        course_id=course_id,
        payload=payload,
        actor_id=current_user.user.id,
    )


@router.post("/courses/{course_id}/emergency-unlock", response_model=GradebookLockResponse)
async def emergency_unlock_gradebook(
    course_id: uuid.UUID,
    payload: EmergencyUnlockRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise GradebookForbiddenException()
    return await GradebookSealingService(db).emergency_unlock_gradebook(
        course_id=course_id,
        payload=payload,
        actor_id=current_user.user.id,
    )


@router.get("/courses/{course_id}/audit-logs", response_model=List[GradeAuditLogResponse])
async def list_gradebook_audit_logs(
    course_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    await _require_instructor(db, course_id, current_user)
    return await GradebookSealingService(db).list_course_audit_logs(course_id)


# ---------------------------------------------------------------------------
# T2-I-M5-03 & T2-P-M5-04: SpeedGrader 3-Column Cockpit & AI Rubric Assistant
# ---------------------------------------------------------------------------
@router.get(
    "/assignments/{assignment_id}/speedgrader/submissions",
    response_model=SpeedGraderSubmissionListResponse,
)
async def list_speedgrader_submissions(
    assignment_id: uuid.UUID,
    filter_mode: SpeedGraderFilter = Query(SpeedGraderFilter.ALL),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    svc = SpeedGraderService(db)
    meta = await svc.assessment_public.get_assignment_meta(assignment_id)
    if meta is None:
        raise GradebookNotFoundException("bai tap")
    await _require_instructor(db, meta.course_id, current_user)
    return await svc.list_assignment_submissions(assignment_id, filter_mode=filter_mode)


@router.get("/speedgrader/submissions/{submission_id}", response_model=SpeedGraderWorkspaceResponse)
async def get_speedgrader_workspace(
    submission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    svc = SpeedGraderService(db)
    bundle = await svc.assessment_public.get_submission_bundle(submission_id)
    if bundle is None:
        raise GradebookNotFoundException("bai nop sinh vien")
    await _require_instructor(db, bundle.course_id, current_user)
    return await svc.get_workspace(submission_id)


@router.post("/speedgrader/submissions/{submission_id}/ai-propose", response_model=RubricProposalResponse)
async def generate_ai_rubric_proposal(
    submission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    ai_svc = AIGraderService(db)
    bundle = await ai_svc.assessment_public.get_submission_bundle(submission_id)
    if bundle is None:
        raise GradebookNotFoundException("bai nop sinh vien")
    await _require_instructor(db, bundle.course_id, current_user)
    return await ai_svc.generate_rubric_proposal(submission_id, actor_id=current_user.user.id)


@router.post("/speedgrader/submissions/{submission_id}/grade", response_model=SpeedGraderWorkspaceResponse)
async def save_speedgrader_grade(
    submission_id: uuid.UUID,
    payload: SpeedGraderSaveGradeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    svc = SpeedGraderService(db)
    bundle = await svc.assessment_public.get_submission_bundle(submission_id)
    if bundle is None:
        raise GradebookNotFoundException("bai nop sinh vien")
    await _require_instructor(db, bundle.course_id, current_user)
    return await svc.save_official_grade(submission_id, payload, actor_id=current_user.user.id)


@router.patch("/speedgrader/submissions/{submission_id}/draft")
async def save_speedgrader_draft(
    submission_id: uuid.UUID,
    payload: SpeedGraderDraftRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    svc = SpeedGraderService(db)
    bundle = await svc.assessment_public.get_submission_bundle(submission_id)
    if bundle is None:
        raise GradebookNotFoundException("bai nop sinh vien")
    await _require_instructor(db, bundle.course_id, current_user)
    return await svc.save_feedback_draft(submission_id, payload, actor_id=current_user.user.id)


@router.get("/speedgrader/submissions/{submission_id}/preview")
async def preview_submission_artifact(
    submission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    svc = SpeedGraderService(db)
    bundle = await svc.assessment_public.get_submission_bundle(submission_id)
    if bundle is None:
        raise GradebookNotFoundException("bai nop sinh vien")
    await _require_instructor(db, bundle.course_id, current_user)
    return await svc.get_submission_preview(submission_id)


@router.get("/speedgrader/submissions/{submission_id}/download")
async def download_submission_artifact(
    submission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    svc = SpeedGraderService(db)
    bundle = await svc.assessment_public.get_submission_bundle(submission_id)
    if bundle is None:
        raise GradebookNotFoundException("bai nop sinh vien")
    await _require_instructor(db, bundle.course_id, current_user)
    data, content_type, filename = await svc.download_submission_bytes(submission_id)
    return StreamingResponse(
        io.BytesIO(data),
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/speedgrader/submissions/{submission_id}/diff", response_model=VersionDiffResponse)
async def get_submission_version_diff(
    submission_id: uuid.UUID,
    compare_to: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    svc = SpeedGraderService(db)
    bundle = await svc.assessment_public.get_submission_bundle(submission_id)
    if bundle is None:
        raise GradebookNotFoundException("bai nop sinh vien")
    await _require_instructor(db, bundle.course_id, current_user)
    return await svc.get_versions_diff(submission_id, compare_to_id=compare_to)


@router.post("/voice-feedback/upload")
async def upload_voice_feedback(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    from app.modules.gradebook.exceptions import GradebookInvalidVoiceFileException
    from app.modules.gradebook.speedgrader_service import MAX_VOICE_BYTES

    chunks: List[bytes] = []
    total_size = 0
    while True:
        chunk = await file.read(65536)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > MAX_VOICE_BYTES:
            raise GradebookInvalidVoiceFileException(
                "Tep ghi am vuot qua dung luong toi da 10MB (E-7)."
            )
        chunks.append(chunk)
    raw_bytes = b"".join(chunks)
    return await SpeedGraderService(db).upload_voice_feedback(
        data=raw_bytes,
        filename=file.filename or "voice-feedback.webm",
        content_type=file.content_type or "audio/webm",
        actor_id=current_user.user.id,
    )


@router.get("/voice-feedback/{object_key:path}")
async def stream_voice_feedback(
    object_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    data, content_type = await SpeedGraderService(db).download_voice_feedback(
        object_key,
        actor_id=current_user.user.id,
        is_admin=_is_admin(current_user),
        course_role_checker=lambda cid: _require_instructor(db, cid, current_user),
    )
    return StreamingResponse(io.BytesIO(data), media_type=content_type)
