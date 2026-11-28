# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""REST API router for Course, Syllabus, Learning Objectives, Roster, and Groups."""

from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.course.public_api import provide_course_roles_for_identity
from app.modules.course.roster_ingestion import build_roster_template_xlsx
from app.modules.course.schemas import (
    CourseCloneRequest,
    CourseCreate,
    CourseDetail,
    CourseStatusUpdateRequest,
    CourseSummary,
    GroupPartitionPreviewRequest,
    GroupSetResponse,
    GroupSetSaveRequest,
    JoinCodeResponse,
    JoinCodeSettingsRequest,
    JoinCourseRequest,
    LOCreate,
    LOOrderUpdateRequest,
    LOResponse,
    LOUpdate,
    RosterImportResult,
    RosterItemResponse,
    RosterPageResponse,
    RosterPreviewResponse,
    RosterStudentCreate,
    SyllabusImportTemplateRequest,
    SyllabusImportTemplateResponse,
    SyllabusUpdate,
)
from app.modules.course.service import (
    CourseService,
    GroupService,
    LearningObjectiveService,
    RosterService,
)
from app.modules.identity.dependencies import CurrentUser, get_current_user
from app.modules.identity.service import register_course_roles_provider

# Wire cross-context callback so identity JWT & /me populate contextual course_roles
register_course_roles_provider(provide_course_roles_for_identity)

router = APIRouter(prefix="/api/v1/courses", tags=["Course & Roster Management"])


# ------------------------------------------------------------------
# Static routes (declared before /{course_id} to prevent UUID clash)
# ------------------------------------------------------------------
@router.get("", response_model=List[CourseSummary])
async def list_courses(
    role: Optional[str] = Query(None, description="Filter by contextual role: INSTRUCTOR or STUDENT"),
    course_status: Optional[str] = Query(None, alias="status", description="Filter by lifecycle status"),
    q: Optional[str] = Query(None, description="Search by course name or code"),
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[CourseSummary]:
    return await CourseService(db).list_courses(
        actor=current.user,
        role_filter=role,
        status_filter=course_status,
        search_query=q,
    )


@router.post("", response_model=CourseDetail, status_code=status.HTTP_201_CREATED)
async def create_course(
    payload: CourseCreate,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CourseDetail:
    return await CourseService(db).create_course(payload, current.user)


@router.get("/templates", response_model=List[CourseSummary])
async def list_templates(
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[CourseSummary]:
    return await CourseService(db).list_templates(current.user)


@router.post("/clone", response_model=CourseDetail, status_code=status.HTTP_201_CREATED)
async def clone_course_template(
    payload: CourseCloneRequest,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CourseDetail:
    return await CourseService(db).clone_from_template(payload, current.user)


@router.post("/join", response_model=CourseSummary)
async def join_course_by_code(
    payload: JoinCourseRequest,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CourseSummary:
    return await RosterService(db).join_by_code(payload.join_code, current.user)


@router.get("/roster/template")
async def download_roster_template(
    current: CurrentUser = Depends(get_current_user),
) -> Response:
    """Download standard .xlsx template for student roster import."""
    _ = current
    content = build_roster_template_xlsx()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="adlas-roster-template.xlsx"'
        },
    )


# ------------------------------------------------------------------
# Course detail, syllabus & lifecycle
# ------------------------------------------------------------------
@router.get("/{course_id}", response_model=CourseDetail)
async def get_course_detail(
    course_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CourseDetail:
    return await CourseService(db).get_course_detail(course_id, current.user)


@router.put("/{course_id}/syllabus", response_model=CourseDetail)
async def update_syllabus(
    course_id: uuid.UUID,
    payload: SyllabusUpdate,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CourseDetail:
    return await CourseService(db).update_syllabus(course_id, payload, current.user)


@router.post("/{course_id}/syllabus/import-template", response_model=SyllabusImportTemplateResponse)
async def import_syllabus_template(
    course_id: uuid.UUID,
    payload: SyllabusImportTemplateRequest,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SyllabusImportTemplateResponse:
    return await CourseService(db).import_syllabus_from_template(
        course_id=course_id,
        template_id=payload.template_id,
        actor=current.user,
    )


@router.post("/{course_id}/status", response_model=CourseDetail)
async def transition_course_status(
    course_id: uuid.UUID,
    payload: CourseStatusUpdateRequest,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CourseDetail:
    return await CourseService(db).transition_status(
        course_id=course_id,
        target_status=payload.target_status,
        actor=current.user,
    )


# ------------------------------------------------------------------
# Learning Objectives (LOs)
# ------------------------------------------------------------------
@router.get("/{course_id}/learning-objectives", response_model=List[LOResponse])
async def list_learning_objectives(
    course_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[LOResponse]:
    return await LearningObjectiveService(db).list_los(course_id, current.user)


@router.post(
    "/{course_id}/learning-objectives",
    response_model=LOResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_learning_objective(
    course_id: uuid.UUID,
    payload: LOCreate,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LOResponse:
    return await LearningObjectiveService(db).create_lo(course_id, payload, current.user)


@router.put("/{course_id}/learning-objectives/order", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_learning_objectives(
    course_id: uuid.UUID,
    payload: LOOrderUpdateRequest,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await LearningObjectiveService(db).reorder_los(course_id, payload.ordered_ids, current.user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{course_id}/learning-objectives/{lo_id}", response_model=LOResponse)
async def update_learning_objective(
    course_id: uuid.UUID,
    lo_id: uuid.UUID,
    payload: LOUpdate,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LOResponse:
    return await LearningObjectiveService(db).update_lo(course_id, lo_id, payload, current.user)


@router.delete(
    "/{course_id}/learning-objectives/{lo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_learning_objective(
    course_id: uuid.UUID,
    lo_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await LearningObjectiveService(db).delete_lo(course_id, lo_id, current.user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------------
# Join Code & Roster Management
# ------------------------------------------------------------------
@router.get("/{course_id}/join-code", response_model=JoinCodeResponse)
async def get_join_code(
    course_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JoinCodeResponse:
    return await RosterService(db).get_join_code(course_id, current.user)


@router.post("/{course_id}/join-code/regenerate", response_model=JoinCodeResponse)
async def regenerate_join_code(
    course_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JoinCodeResponse:
    return await RosterService(db).regenerate_join_code(course_id, current.user)


@router.put("/{course_id}/join-code/settings", response_model=CourseDetail)
async def update_join_code_settings(
    course_id: uuid.UUID,
    payload: JoinCodeSettingsRequest,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CourseDetail:
    return await RosterService(db).update_join_code_settings(
        course_id=course_id,
        is_enrollment_open=payload.is_enrollment_open,
        actor=current.user,
    )


@router.get("/{course_id}/roster", response_model=RosterPageResponse)
async def list_roster(
    course_id: uuid.UUID,
    q: Optional[str] = Query(None, description="Search by student name, MSSV, or email"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RosterPageResponse:
    return await RosterService(db).list_roster(
        course_id=course_id,
        actor=current.user,
        search_query=q,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{course_id}/roster/students",
    response_model=RosterItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_single_student(
    course_id: uuid.UUID,
    payload: RosterStudentCreate,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RosterItemResponse:
    return await RosterService(db).add_single_student(course_id, payload, current.user)


@router.delete("/{course_id}/roster/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_student_from_roster(
    course_id: uuid.UUID,
    user_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await RosterService(db).remove_student(course_id, user_id, current.user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{course_id}/roster/preview", response_model=RosterPreviewResponse)
async def preview_roster_upload(
    course_id: uuid.UUID,
    file: UploadFile = File(...),
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RosterPreviewResponse:
    content = await file.read()
    return await RosterService(db).preview_roster_file(
        course_id=course_id,
        filename=file.filename or "",
        content=content,
        actor=current.user,
    )


@router.post("/{course_id}/roster/confirm", response_model=RosterImportResult)
async def confirm_roster_upload(
    course_id: uuid.UUID,
    file: UploadFile = File(...),
    send_notification: bool = Form(False),
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RosterImportResult:
    content = await file.read()
    return await RosterService(db).confirm_roster_file(
        course_id=course_id,
        filename=file.filename or "",
        content=content,
        send_notification=send_notification,
        actor=current.user,
    )


@router.get("/{course_id}/roster/export-xlsx")
async def export_roster_xlsx(
    course_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Export active student roster to .xlsx with formula injection protection (T2-P-M1-03)."""
    content, filename = await RosterService(db).export_roster_xlsx(course_id, current.user)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


# ------------------------------------------------------------------
# Groups & Partitioning
# ------------------------------------------------------------------
@router.get("/{course_id}/groups", response_model=List[GroupSetResponse])
async def list_course_groups(
    course_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[GroupSetResponse]:
    return await GroupService(db).list_group_sets(course_id, current.user)


@router.post("/{course_id}/groups/partition/preview", response_model=GroupSetResponse)
async def preview_group_partition(
    course_id: uuid.UUID,
    payload: GroupPartitionPreviewRequest,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupSetResponse:
    return await GroupService(db).preview_partition(course_id, payload, current.user)


@router.put("/{course_id}/groups/sets/{group_set_name}", response_model=GroupSetResponse)
async def save_group_set(
    course_id: uuid.UUID,
    group_set_name: str,
    payload: GroupSetSaveRequest,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupSetResponse:
    return await GroupService(db).save_group_set(
        course_id=course_id,
        group_set_name=group_set_name,
        payload=payload,
        actor=current.user,
    )


@router.post("/{course_id}/groups/{group_id}/join", status_code=status.HTTP_204_NO_CONTENT)
async def student_join_group(
    course_id: uuid.UUID,
    group_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await GroupService(db).student_join_group(course_id, group_id, current.user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
