# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Domain enumerations for Examination Context (Module 4)."""

from enum import Enum


class QuestionType(str, Enum):
    """Supported objective question formats in examination.questions."""

    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    MULTI_SELECT = "MULTI_SELECT"


class QuizStatus(str, Enum):
    """Lifecycle states of a quiz/exam."""

    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CLOSED = "CLOSED"


class SecurityMode(str, Enum):
    """Proctoring and environment restriction mode of a quiz."""

    CONTROLLED = "CONTROLLED"
    REMOTE_PROCTORED = "REMOTE_PROCTORED"
    PRACTICE = "PRACTICE"


class GradeReleasePolicy(str, Enum):
    """Determines when exam scores and explanations become visible and 48h regrade starts."""

    IMMEDIATE = "IMMEDIATE"
    AFTER_CLOSE = "AFTER_CLOSE"
    MANUAL = "MANUAL"


class SubmissionStatus(str, Enum):
    """State machine states for a student's quiz attempt."""

    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    TIMED_OUT = "TIMED_OUT"
    AUTO_GRADED = "AUTO_GRADED"
    REGRADE_PENDING = "REGRADE_PENDING"
    REGRADE_RESOLVED = "REGRADE_RESOLVED"
    FINALIZED = "FINALIZED"


class RegradeStatus(str, Enum):
    """Lifecycle states of a 48-hour regrade request."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RegradeScope(str, Enum):
    """Scope of score recalculation when an instructor approves a regrade request."""

    SINGLE_STUDENT = "SINGLE_STUDENT"
    ENTIRE_CLASS = "ENTIRE_CLASS"
