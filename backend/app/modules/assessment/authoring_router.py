# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""REST router for assignment authoring, rubric and integrity pledge (TV3)."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.assessment.authoring_schemas import (
    AssignmentAuthoringResponse,
    AssignmentCreateRequest,
    AssignmentDeleteResponse,
    AssignmentUpdateRequest,
    MilestoneResponse,
    MilestonesBatchCreateRequest,
    PeerReviewResponse,
    PeerReviewSubmitRequest,
    PeerReviewSummaryResponse,
    PledgeSignRequest,
    PledgeSignResponse,
    PledgeStatusResponse,
    RubricResponse,
    RubricSaveRequest,
    StudentGroupCreateRequest,
    StudentGroupJoinRequest,
    StudentGroupResponse,
    TopicCreateRequest,
    TopicResponse,
    TopicSelectRequest,
)
from app.modules.assessment.authoring_service import AssignmentAuthoringService
from app.modules.assessment.group_service import GroupService
from app.modules.assessment.peer_review_service import PeerReviewService
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


# ----------------------------------------------------------------------
# Milestones Endpoints
# ----------------------------------------------------------------------
@router.post(
    "/assignments/{assignment_id}/milestones",
    response_model=list[MilestoneResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_milestones(
    assignment_id: uuid.UUID,
    payload: MilestonesBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await AssignmentAuthoringService(db).create_milestones(assignment_id, current_user.user, payload)


@router.get(
    "/assignments/{assignment_id}/milestones",
    response_model=list[MilestoneResponse],
)
async def list_milestones(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await AssignmentAuthoringService(db).list_milestones(assignment_id)


# ----------------------------------------------------------------------
# Topics & Groups Endpoints
# ----------------------------------------------------------------------
@router.post(
    "/assignments/{assignment_id}/topics",
    response_model=TopicResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_topic(
    assignment_id: uuid.UUID,
    payload: TopicCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await GroupService(db).create_topic(
        assignment_id=assignment_id,
        user=current_user.user,
        topic_code=payload.topic_code,
        title=payload.title,
        description=payload.description,
        max_groups=payload.max_groups,
    )


@router.get(
    "/assignments/{assignment_id}/topics",
    response_model=list[TopicResponse],
)
async def list_topics(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await GroupService(db).list_topics(assignment_id)


@router.post(
    "/assignments/{assignment_id}/groups",
    response_model=StudentGroupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_group(
    assignment_id: uuid.UUID,
    payload: StudentGroupCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    group = await GroupService(db).create_group(
        assignment_id=assignment_id,
        leader=current_user.user,
        group_name=payload.group_name,
        member_ids=payload.member_ids,
        topic_id=payload.topic_id,
    )
    return StudentGroupResponse(
        id=group.id,
        assignment_id=group.assignment_id,
        group_name=group.group_name,
        join_code=group.join_code,
        topic_id=group.topic_id,
        topic_code=group.topic.topic_code if group.topic else None,
        topic_title=group.topic.title if group.topic else None,
        leader_student_id=group.leader_student_id,
        is_finalized=group.is_finalized,
        created_at=group.created_at,
        updated_at=group.updated_at,
        members=[
            {
                "id": m.id,
                "group_id": m.group_id,
                "student_id": m.student_id,
                "student_name": f"{m.student.first_name} {m.student.last_name}" if m.student else None,
                "student_email": m.student.email if m.student else None,
                "role": m.role,
                "joined_at": m.joined_at,
            }
            for m in group.members
        ],
    )


@router.post(
    "/assignments/{assignment_id}/groups/join",
    response_model=StudentGroupResponse,
)
async def join_group_by_code(
    assignment_id: uuid.UUID,
    payload: StudentGroupJoinRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    group = await GroupService(db).join_group_by_code(
        assignment_id=assignment_id,
        user=current_user.user,
        join_code=payload.join_code,
    )
    return StudentGroupResponse(
        id=group.id,
        assignment_id=group.assignment_id,
        group_name=group.group_name,
        join_code=group.join_code,
        topic_id=group.topic_id,
        topic_code=group.topic.topic_code if group.topic else None,
        topic_title=group.topic.title if group.topic else None,
        leader_student_id=group.leader_student_id,
        is_finalized=group.is_finalized,
        created_at=group.created_at,
        updated_at=group.updated_at,
        members=[
            {
                "id": m.id,
                "group_id": m.group_id,
                "student_id": m.student_id,
                "student_name": f"{m.student.first_name} {m.student.last_name}" if m.student else None,
                "student_email": m.student.email if m.student else None,
                "role": m.role,
                "joined_at": m.joined_at,
            }
            for m in group.members
        ],
    )


@router.post(
    "/groups/{group_id}/topic",
    response_model=StudentGroupResponse,
)
async def select_group_topic(
    group_id: uuid.UUID,
    payload: TopicSelectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    group = await GroupService(db).select_topic(
        group_id=group_id,
        user=current_user.user,
        topic_id=payload.topic_id,
    )
    return StudentGroupResponse(
        id=group.id,
        assignment_id=group.assignment_id,
        group_name=group.group_name,
        join_code=group.join_code,
        topic_id=group.topic_id,
        topic_code=group.topic.topic_code if group.topic else None,
        topic_title=group.topic.title if group.topic else None,
        leader_student_id=group.leader_student_id,
        is_finalized=group.is_finalized,
        created_at=group.created_at,
        updated_at=group.updated_at,
        members=[
            {
                "id": m.id,
                "group_id": m.group_id,
                "student_id": m.student_id,
                "student_name": f"{m.student.first_name} {m.student.last_name}" if m.student else None,
                "student_email": m.student.email if m.student else None,
                "role": m.role,
                "joined_at": m.joined_at,
            }
            for m in group.members
        ],
    )


@router.post(
    "/assignments/{assignment_id}/groups/auto-assign",
    response_model=list[StudentGroupResponse],
)
async def auto_assign_groups(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    groups = await GroupService(db).auto_assign_orphan_students(
        assignment_id=assignment_id,
        instructor=current_user.user,
    )
    return [
        StudentGroupResponse(
            id=g.id,
            assignment_id=g.assignment_id,
            group_name=g.group_name,
            topic_id=g.topic_id,
            topic_code=g.topic.topic_code if g.topic else None,
            topic_title=g.topic.title if g.topic else None,
            leader_student_id=g.leader_student_id,
            is_finalized=g.is_finalized,
            created_at=g.created_at,
            updated_at=g.updated_at,
            members=[
                {
                    "id": m.id,
                    "group_id": m.group_id,
                    "student_id": m.student_id,
                    "student_name": f"{m.student.first_name} {m.student.last_name}" if m.student else None,
                    "student_email": m.student.email if m.student else None,
                    "role": m.role,
                    "joined_at": m.joined_at,
                }
                for m in g.members
            ],
        )
        for g in groups
    ]


# ----------------------------------------------------------------------
# Blind Peer Review Endpoints
# ----------------------------------------------------------------------
@router.post(
    "/assignments/{assignment_id}/peer-reviews",
    response_model=PeerReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_peer_review(
    assignment_id: uuid.UUID,
    payload: PeerReviewSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await PeerReviewService(db).submit_peer_review(
        assignment_id=assignment_id,
        reviewer=current_user.user,
        payload=payload,
    )


@router.get(
    "/assignments/{assignment_id}/groups/{group_id}/peer-reviews/factors",
    response_model=PeerReviewSummaryResponse,
)
async def get_peer_review_factors(
    assignment_id: uuid.UUID,
    group_id: uuid.UUID,
    milestone_id: Optional[uuid.UUID] = None,
    raw_group_grade: float = 10.0,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await PeerReviewService(db).calculate_peer_review_factors(
        assignment_id=assignment_id,
        group_id=group_id,
        milestone_id=milestone_id,
        raw_group_grade=raw_group_grade,
    )
