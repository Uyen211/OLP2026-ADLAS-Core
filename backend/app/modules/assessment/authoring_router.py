# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""REST router for assignment authoring, rubric and integrity pledge (TV3)."""

import uuid
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.assessment.authoring_schemas import (
    AssignmentAuthoringResponse,
    AssignmentCreateRequest,
    AssignmentDeleteResponse,
    AssignmentUpdateRequest,
    PledgeSignRequest,
    PledgeSignResponse,
    PledgeStatusResponse,
    RubricResponse,
    RubricSaveRequest,
)
from app.modules.assessment.authoring_service import AssignmentAuthoringService
from app.modules.assessment.pledge_service import PledgeService
from app.modules.assessment.rubric_service import RubricService
from app.modules.identity.dependencies import CurrentUser, get_current_user

router = APIRouter(prefix="/api/v1/assessments", tags=["Assessment Authoring & Rubric"])


@router.post(
    "/courses/{course_id}/assignments",
    response_model=AssignmentAuthoringResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_assignment(
    course_id: uuid.UUID,
    payload: AssignmentCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await AssignmentAuthoringService(db).create_assignment(course_id, current_user.user, payload)


@router.put("/assignments/{assignment_id}", response_model=AssignmentAuthoringResponse)
async def update_assignment(
    assignment_id: uuid.UUID,
    payload: AssignmentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await AssignmentAuthoringService(db).update_assignment(assignment_id, current_user.user, payload)


@router.post("/assignments/{assignment_id}/publish", response_model=AssignmentAuthoringResponse)
async def publish_assignment(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await AssignmentAuthoringService(db).publish_assignment(assignment_id, current_user.user)


@router.delete("/assignments/{assignment_id}", response_model=AssignmentDeleteResponse)
async def delete_assignment(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await AssignmentAuthoringService(db).delete_assignment(assignment_id, current_user.user)


@router.get("/assignments/{assignment_id}/rubric", response_model=RubricResponse)
async def get_rubric(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await RubricService(db).get_rubric(assignment_id, current_user.user)


@router.put("/assignments/{assignment_id}/rubric", response_model=RubricResponse)
async def save_rubric(
    assignment_id: uuid.UUID,
    payload: RubricSaveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await RubricService(db).save_rubric(assignment_id, current_user.user, payload)


@router.get("/assignments/{assignment_id}/integrity-pledge", response_model=PledgeStatusResponse)
async def get_integrity_pledge(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await PledgeService(db).get_status(assignment_id, current_user.user)


@router.post(
    "/assignments/{assignment_id}/integrity-pledge",
    response_model=PledgeSignResponse,
    status_code=status.HTTP_201_CREATED,
)
async def sign_integrity_pledge(
    assignment_id: uuid.UUID,
    payload: PledgeSignRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    client_ip = request.client.host if request.client else None
    return await PledgeService(db).sign(
        assignment_id,
        current_user.user,
        payload,
        client_ip=client_ip,
        user_agent=request.headers.get("user-agent"),
    )
