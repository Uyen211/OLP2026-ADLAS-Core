# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""REST API router for Assignments, Submissions, AI Disclosure, and Viva Sandbox."""

import os
import shutil
import uuid
from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.assessment.schemas import (
    AssignmentDetailResponse,
    PresignedUploadUrlRequest,
    SubmissionCreateRequest,
    SubmissionResponse,
    VivaAnswerSubmitRequest,
    VivaAnswerSubmitResponse,
    VivaSecurityViolationRequest,
    VivaStartResponse,
)
from app.modules.assessment.service import AssessmentSubmissionService
from app.modules.assessment.viva_service import VivaSandboxService
from app.modules.identity.dependencies import CurrentUser, get_current_user

router = APIRouter(prefix="/api/v1/assessments", tags=["Assessment & Viva Sandbox"])
submission_service = AssessmentSubmissionService()
viva_service = VivaSandboxService()


@router.get("/assignments/{assignment_id}", response_model=AssignmentDetailResponse)
async def get_assignment_detail(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Retrieve assignment details, cutoff schedule, and student submission history."""
    return await submission_service.get_assignment_detail(
        db=db,
        assignment_id=assignment_id,
        user_id=current_user.user.id
    )


@router.post(
    "/assignments/{assignment_id}/submissions",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_submission(
    assignment_id: uuid.UUID,
    payload: SubmissionCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Submit an assignment with academic integrity pledge and AI usage disclosure."""
    return await submission_service.create_submission(
        db=db,
        assignment_id=assignment_id,
        user_id=current_user.user.id,
        payload=payload
    )


@router.post(
    "/submissions/{submission_id}/viva/start",
    response_model=VivaStartResponse
)
async def start_viva_session(
    submission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Enter or resume the isolated Viva defense sandbox session."""
    return await viva_service.start_session(
        db=db,
        submission_id=submission_id,
        user_id=current_user.user.id
    )


@router.post(
    "/submissions/{submission_id}/viva/answers",
    response_model=VivaAnswerSubmitResponse
)
async def submit_viva_answer(
    submission_id: uuid.UUID,
    payload: VivaAnswerSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Submit typed answer for current Viva question (enforcing >= 50 words)."""
    return await viva_service.submit_answer(
        db=db,
        submission_id=submission_id,
        user_id=current_user.user.id,
        payload=payload
    )


@router.post("/submissions/{submission_id}/viva/violations", status_code=status.HTTP_200_OK)
async def record_security_violation(
    submission_id: uuid.UUID,
    payload: VivaSecurityViolationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Record security violations such as PASTE_ATTEMPT (E-9) or WINDOW_BLUR (E-VIVA-01)."""
    recorded = await viva_service.record_security_violation(
        db=db,
        submission_id=submission_id,
        user_id=current_user.user.id,
        violation_type=payload.violation_type,
        details=payload.details or {}
    )
    return {"recorded": recorded, "violation_type": payload.violation_type}


UPLOAD_DIR = "/app/uploads/submissions"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_submission_file(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Directly save submission file (PDF, DOCX, ZIP) to server disk for ingestion."""
    safe_name = f"{uuid.uuid4()}-{file.filename}"
    local_path = os.path.join(UPLOAD_DIR, safe_name)
    with open(local_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {
        "file_url": local_path,
        "file_name": file.filename,
    }


@router.post("/presigned-upload-url")
async def generate_presigned_upload_url(
    payload: PresignedUploadUrlRequest,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Provide signed S3 upload URL for direct client multipart material upload."""
    unique_key = f"submissions/{current_user.id}/{uuid.uuid4()}-{payload.file_name}"
    # In local Docker without active MinIO TLS, return pre-configured upload endpoint
    return {
        "upload_url": f"http://localhost:9000/adlas-submissions/{unique_key}",
        "file_url": f"/storage/adlas-submissions/{unique_key}",
        "file_key": unique_key
    }
