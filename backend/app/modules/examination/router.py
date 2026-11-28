# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""REST API router for Examination Context (T2-P-M4-01 & T2-P-M4-02)."""

from typing import Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.examination.schemas import (
    ActiveSessionResponse,
    AttemptResultResponse,
    AttemptStartRequest,
    AttemptStartResponse,
    AutosaveRequest,
    AutosaveResponse,
    ExtractionBatchSaveRequest,
    ExtractionPreviewResponse,
    PasscodeRegenerateResponse,
    PublishGradesResponse,
    QuestionBankCreate,
    QuestionBankResponse,
    QuestionCreate,
    QuestionDeleteResponse,
    QuestionFolderCreate,
    QuestionFolderResponse,
    QuestionResponse,
    QuestionUpdate,
    QuizCreate,
    QuizDetailResponse,
    QuizSettingsUpdate,
    QuizSummaryResponse,
    RegradeCreateRequest,
    RegradeReviewRequest,
    RegradeReviewResponse,
    RegradeSummaryResponse,
    SubmitAttemptRequest,
    SubmitAttemptResponse,
)
from app.modules.examination.service import ExaminationService
from app.modules.identity.dependencies import CurrentUser, get_current_user

router = APIRouter(prefix="/api/v1/examinations", tags=["Examination & CBT Engine"])


def _extract_client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


# ------------------------------------------------------------------
# Question Folders (TV3 Feature)
# ------------------------------------------------------------------
@router.get(
    "/courses/{course_id}/folders",
    response_model=List[QuestionFolderResponse],
)
async def list_question_folders(
    course_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[QuestionFolderResponse]:
    return await ExaminationService(db).list_question_folders(course_id, current.user)


@router.post(
    "/courses/{course_id}/folders",
    response_model=QuestionFolderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_question_folder(
    course_id: uuid.UUID,
    payload: QuestionFolderCreate,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuestionFolderResponse:
    return await ExaminationService(db).create_question_folder(course_id, payload, current.user)


@router.delete(
    "/folders/{folder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_question_folder(
    folder_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await ExaminationService(db).delete_question_folder(folder_id, current.user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------------
# 1-Click Extraction (TV3 Feature)
# ------------------------------------------------------------------
@router.post(
    "/courses/{course_id}/extract-text",
    response_model=ExtractionPreviewResponse,
)
async def extract_questions_from_text(
    course_id: uuid.UUID,
    body: Dict[str, str],
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExtractionPreviewResponse:
    text = body.get("text", "")
    return ExaminationService(db).preview_extract_from_text(text)


@router.post(
    "/courses/{course_id}/extract-upload",
    response_model=ExtractionPreviewResponse,
)
async def extract_questions_from_upload(
    course_id: uuid.UUID,
    file: UploadFile = File(...),
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExtractionPreviewResponse:
    content = await file.read()
    return ExaminationService(db).preview_extract_from_bytes(content, filename=file.filename or "file.txt")


@router.post(
    "/courses/{course_id}/batch-save-questions",
    response_model=List[QuestionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def batch_save_questions(
    course_id: uuid.UUID,
    payload: ExtractionBatchSaveRequest,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[QuestionResponse]:
    return await ExaminationService(db).batch_save_extracted_questions(course_id, payload, current.user)


# ------------------------------------------------------------------
# Question Banks (T2-P-M4-01)
# ------------------------------------------------------------------
@router.get(
    "/courses/{course_id}/question-banks",
    response_model=List[QuestionBankResponse],
)
async def list_question_banks(
    course_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[QuestionBankResponse]:
    return await ExaminationService(db).list_question_banks(course_id, current.user)


@router.post(
    "/courses/{course_id}/question-banks",
    response_model=QuestionBankResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_question_bank(
    course_id: uuid.UUID,
    payload: QuestionBankCreate,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuestionBankResponse:
    return await ExaminationService(db).create_question_bank(course_id, payload, current.user)


@router.delete(
    "/question-banks/{bank_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_question_bank(
    bank_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await ExaminationService(db).delete_question_bank(bank_id, current.user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------------
# Questions (T2-P-M4-01)
# ------------------------------------------------------------------
@router.get(
    "/courses/{course_id}/questions",
    response_model=List[QuestionResponse],
)
async def list_questions(
    course_id: uuid.UUID,
    bank_id: Optional[uuid.UUID] = Query(None, description="Filter by question bank ID"),
    lo_id: Optional[uuid.UUID] = Query(None, description="Filter by Learning Objective ID"),
    bloom_level: Optional[str] = Query(None, description="Filter by Bloom cognitive level"),
    q: Optional[str] = Query(None, description="Search keyword in question text"),
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[QuestionResponse]:
    return await ExaminationService(db).list_questions(
        course_id=course_id,
        actor=current.user,
        bank_id=bank_id,
        lo_id=lo_id,
        bloom_level=bloom_level,
        search_query=q,
    )


@router.post(
    "/courses/{course_id}/questions",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_question(
    course_id: uuid.UUID,
    payload: QuestionCreate,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuestionResponse:
    return await ExaminationService(db).create_question(course_id, payload, current.user)


@router.put(
    "/questions/{question_id}",
    response_model=QuestionResponse,
)
async def update_question(
    question_id: uuid.UUID,
    payload: QuestionUpdate,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuestionResponse:
    return await ExaminationService(db).update_question(question_id, payload, current.user)


@router.delete(
    "/questions/{question_id}",
    response_model=QuestionDeleteResponse,
)
async def delete_question(
    question_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuestionDeleteResponse:
    return await ExaminationService(db).delete_question(question_id, current.user)


# ------------------------------------------------------------------
# Quizzes, Snapshots & Room Security Settings (T2-P-M4-01..02)
# ------------------------------------------------------------------
@router.get(
    "/courses/{course_id}/quizzes",
    response_model=List[QuizSummaryResponse],
)
async def list_quizzes(
    course_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[QuizSummaryResponse]:
    return await ExaminationService(db).list_quizzes(course_id, current.user)


@router.post(
    "/courses/{course_id}/quizzes",
    response_model=QuizDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_quiz(
    course_id: uuid.UUID,
    payload: QuizCreate,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuizDetailResponse:
    return await ExaminationService(db).create_quiz(course_id, payload, current.user)


@router.get(
    "/quizzes/{quiz_id}",
    response_model=QuizDetailResponse,
)
async def get_quiz_detail(
    quiz_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuizDetailResponse:
    return await ExaminationService(db).get_quiz_detail(quiz_id, current.user)


@router.put(
    "/quizzes/{quiz_id}/settings",
    response_model=QuizDetailResponse,
)
async def update_quiz_settings(
    quiz_id: uuid.UUID,
    payload: QuizSettingsUpdate,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuizDetailResponse:
    return await ExaminationService(db).update_quiz_settings(quiz_id, payload, current.user)


@router.post(
    "/quizzes/{quiz_id}/publish",
    response_model=QuizDetailResponse,
)
async def publish_quiz(
    quiz_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuizDetailResponse:
    return await ExaminationService(db).publish_quiz(quiz_id, current.user)


@router.post(
    "/quizzes/{quiz_id}/passcode/regenerate",
    response_model=PasscodeRegenerateResponse,
)
async def regenerate_passcode(
    quiz_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PasscodeRegenerateResponse:
    return await ExaminationService(db).regenerate_passcode(quiz_id, current.user)


@router.post(
    "/quizzes/{quiz_id}/publish-grades",
    response_model=PublishGradesResponse,
)
async def publish_grades(
    quiz_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PublishGradesResponse:
    return await ExaminationService(db).publish_grades(quiz_id, current.user)


# ------------------------------------------------------------------
# Exam Taking, Resume Exam, Autosave & Active Session (T2-P-M4-03)
# ------------------------------------------------------------------
@router.post(
    "/quizzes/{quiz_id}/attempts/start",
    response_model=AttemptStartResponse,
)
async def start_or_resume_attempt(
    quiz_id: uuid.UUID,
    request: Request,
    payload: Optional[AttemptStartRequest] = None,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AttemptStartResponse:
    body = payload or AttemptStartRequest()
    return await ExaminationService(db).start_attempt(
        quiz_id=quiz_id,
        payload=body,
        actor=current.user,
        client_ip=_extract_client_ip(request),
    )


@router.post(
    "/attempts/{submission_id}/autosave",
    response_model=AutosaveResponse,
)
async def autosave_attempt(
    submission_id: uuid.UUID,
    payload: AutosaveRequest,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AutosaveResponse:
    return await ExaminationService(db).autosave_attempt(
        submission_id=submission_id,
        payload=payload,
        actor=current.user,
    )


@router.post(
    "/attempts/{submission_id}/submit",
    response_model=SubmitAttemptResponse,
)
async def submit_attempt(
    submission_id: uuid.UUID,
    payload: Optional[SubmitAttemptRequest] = None,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmitAttemptResponse:
    return await ExaminationService(db).submit_attempt(
        submission_id=submission_id,
        payload=payload,
        actor=current.user,
    )


@router.get(
    "/quizzes/{quiz_id}/active-session",
    response_model=ActiveSessionResponse,
)
async def get_active_session(
    quiz_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ActiveSessionResponse:
    return await ExaminationService(db).get_active_session(quiz_id, current.user)


# ------------------------------------------------------------------
# Results & 48-Hour Regrade Workflow (T2-P-M4-04)
# ------------------------------------------------------------------
@router.get(
    "/attempts/{submission_id}/result",
    response_model=AttemptResultResponse,
)
async def get_attempt_result(
    submission_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AttemptResultResponse:
    return await ExaminationService(db).get_attempt_result(submission_id, current.user)


@router.post(
    "/attempts/{submission_id}/regrades",
    response_model=RegradeSummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_regrade_request(
    submission_id: uuid.UUID,
    payload: RegradeCreateRequest,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RegradeSummaryResponse:
    return await ExaminationService(db).create_regrade_request(
        submission_id=submission_id,
        payload=payload,
        actor=current.user,
    )


@router.get(
    "/quizzes/{quiz_id}/regrades",
    response_model=List[RegradeSummaryResponse],
)
async def list_quiz_regrades(
    quiz_id: uuid.UUID,
    regrade_status: Optional[str] = Query(None, alias="status"),
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[RegradeSummaryResponse]:
    return await ExaminationService(db).list_quiz_regrades(
        quiz_id=quiz_id,
        actor=current.user,
        status_filter=regrade_status,
    )


@router.post(
    "/regrades/{regrade_id}/review",
    response_model=RegradeReviewResponse,
)
async def review_regrade_request(
    regrade_id: uuid.UUID,
    payload: RegradeReviewRequest,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RegradeReviewResponse:
    return await ExaminationService(db).review_regrade_request(
        regrade_id=regrade_id,
        payload=payload,
        actor=current.user,
    )
