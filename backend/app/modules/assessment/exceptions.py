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


class AssessmentAccessDeniedException(ADLASException):
    def __init__(self, detail: str = "Instructor authorization is required to review course submissions."):
        super().__init__(
            code="E-ASSESSMENT-02",
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN
        )


class InvalidAssignmentScheduleException(ADLASException):
    def __init__(self, detail: str = "Invalid schedule: require available_from <= due_date <= until_date."):
        super().__init__(
            code="E-ASN-01",
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class AssignmentNotOpenException(ADLASException):
    def __init__(self):
        super().__init__(
            code="E-ASN-02",
            detail="This assignment is not open for submission yet (available_from has not been reached).",
            status_code=status.HTTP_403_FORBIDDEN
        )


class MaxAttemptsExceededException(ADLASException):
    def __init__(self, max_attempts: int):
        super().__init__(
            code="E-ASN-03",
            detail=f"Maximum number of submission attempts ({max_attempts}) has been reached.",
            status_code=status.HTTP_403_FORBIDDEN
        )


class InvalidRubricTotalPointsException(ADLASException):
    def __init__(self, total: str, expected: str = "10.0"):
        super().__init__(
            code="E-RUB-01",
            detail=f"Rubric criteria points must total exactly {expected} (current total: {total}).",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class RubricFrozenException(ADLASException):
    def __init__(self, submission_count: int = 0):
        super().__init__(
            code="E-RUB-02",
            detail=f"Rubric is frozen because it is already used for grading ({submission_count} submission(s)).",
            status_code=status.HTTP_409_CONFLICT
        )


class IntegrityPledgeNotSignedException(ADLASException):
    def __init__(self):
        super().__init__(
            code="E-PLG-01",
            detail="You must confirm the academic integrity pledge before continuing.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class AssignmentHasSubmissionsException(ADLASException):
    def __init__(self, submission_count: int = 0):
        super().__init__(
            code="E-ASN-04",
            detail=f"Assignment cannot be deleted because it already has {submission_count} submission(s).",
            status_code=status.HTTP_409_CONFLICT
        )


class InvalidRubricLearningObjectiveException(ADLASException):
    def __init__(self, lo_id: str):
        super().__init__(
            code="E-RUB-03",
            detail=f"Learning Objective '{lo_id}' does not belong to this course.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class GroupTopicFullException(ADLASException):
    def __init__(self, topic_code: str):
        super().__init__(
            code="E-GRP-01",
            detail=f"Project topic '{topic_code}' has reached its maximum group capacity.",
            status_code=status.HTTP_409_CONFLICT,
        )


class GroupFormationDeadlinePassedException(ADLASException):
    def __init__(self):
        super().__init__(
            code="E-GRP-02",
            detail="The group formation deadline for this assignment has passed.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class StudentGroupNotFoundException(ADLASException):
    def __init__(self, group_id: str):
        super().__init__(
            code="E-GRP-03",
            detail=f"Student group '{group_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ProjectTopicNotFoundException(ADLASException):
    def __init__(self, topic_id: str):
        super().__init__(
            code="E-GRP-04",
            detail=f"Project topic '{topic_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class InvalidMilestoneWeightsException(ADLASException):
    def __init__(self, current_total: float):
        super().__init__(
            code="E-MLS-01",
            detail=f"Milestone weights must total exactly 100.0% (current sum: {current_total}%).",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class InvalidMilestoneDatesException(ADLASException):
    def __init__(self, detail: str = "Milestone due_date must be before until_date and within the assignment timeframe."):
        super().__init__(
            code="E-MLS-02",
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class AssignmentMilestoneNotFoundException(ADLASException):
    def __init__(self, milestone_id: str):
        super().__init__(
            code="E-MLS-03",
            detail=f"Milestone '{milestone_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class PeerReviewSelfNotAllowedException(ADLASException):
    def __init__(self):
        super().__init__(
            code="E-REV-01",
            detail="Self-evaluation is not permitted in peer review.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class PeerReviewNotMemberException(ADLASException):
    def __init__(self):
        super().__init__(
            code="E-REV-02",
            detail="Peer review can only be submitted for members within your own group.",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class StudentAlreadyInGroupException(ADLASException):
    def __init__(self):
        super().__init__(
            code="E-GRP-05",
            detail="Student is already a member of a group for this assignment.",
            status_code=status.HTTP_409_CONFLICT,
        )


class GroupFullException(ADLASException):
    def __init__(self):
        super().__init__(
            code="E-GRP-06",
            detail="Student group has reached its maximum member capacity.",
            status_code=status.HTTP_409_CONFLICT,
        )


class InvalidJoinCodeException(ADLASException):
    def __init__(self, code_val: str):
        super().__init__(
            code="E-GRP-07",
            detail=f"Invalid or expired group join code: '{code_val}'.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
