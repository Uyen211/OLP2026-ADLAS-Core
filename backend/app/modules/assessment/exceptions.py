# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Domain exceptions for Assessment, Submission, and Viva Sandbox contexts."""

from fastapi import status
from app.core.exceptions import ADLASException


class AssessmentNotFoundException(ADLASException):
    def __init__(self, assignment_id: str):
        super().__init__(
            code="E-ASSESSMENT-01",
            detail=f"Assignment with ID '{assignment_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND
        )


class SubmissionCutoffExceededException(ADLASException):
    def __init__(self):
        super().__init__(
            code="E-8",
            detail="The absolute submission deadline (Until Date) has passed. Submissions are closed.",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class InvalidSubmissionPayloadException(ADLASException):
    def __init__(self, message: str):
        super().__init__(
            code="E-7",
            detail=message,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class PublicGitRepositoryException(ADLASException):
    def __init__(self, repo_url: str):
        super().__init__(
            code="E-GIT-01",
            detail=f"Cannot access public git repository at '{repo_url}'. Please check repository visibility.",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class AIDisclosureValidationException(ADLASException):
    def __init__(self, message: str = "Please provide at least 20 characters explaining your AI usage."):
        super().__init__(
            code="E-1",
            detail=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class VivaSessionNotFoundException(ADLASException):
    def __init__(self, submission_id: str):
        super().__init__(
            code="E-VIVA-02",
            detail=f"Viva Sandbox session for submission '{submission_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND
        )


class VivaSessionCompletedException(ADLASException):
    def __init__(self):
        super().__init__(
            code="E-VIVA-03",
            detail="Viva Sandbox session has already been completed and sealed.",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class VivaAnswerWordCountException(ADLASException):
    def __init__(self, word_count: int, min_words: int = 50):
        super().__init__(
            code="E-1",
            detail=f"Your answer is too short ({word_count} words). Minimum requirement is {min_words} words.",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class VivaTimeoutException(ADLASException):
    def __init__(self):
        super().__init__(
            code="E-VIVA-04",
            detail="Viva Sandbox session time limit has expired. Answers have been automatically retrieved.",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class IntegrityPledgeRequiredException(ADLASException):
    def __init__(self):
        super().__init__(
            code="E-1",
            detail="Academic integrity pledge must be signed before submitting.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class VivaSessionPreparingException(ADLASException):
    def __init__(self):
        super().__init__(
            code="E-VIVA-PREPARING",
            detail="Viva defense questions are still being prepared. Please retry in a few seconds.",
            status_code=status.HTTP_409_CONFLICT
        )


class VivaQuestionMismatchException(ADLASException):
    def __init__(self):
        super().__init__(
            code="E-2",
            detail="Submitted question_id does not match the active Viva question.",
            status_code=status.HTTP_400_BAD_REQUEST
        )
