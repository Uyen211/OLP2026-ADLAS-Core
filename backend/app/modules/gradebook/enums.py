# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Enumerations for Gradebook structure, TT08 conversion, AI evidence flags, and SpeedGrader."""

from enum import Enum


class GradeItemType(str, Enum):
    """Source type of a gradebook column."""

    ASSIGNMENT = "ASSIGNMENT"
    QUIZ = "QUIZ"
    PROGRESS_ATTENDANCE = "PROGRESS_ATTENDANCE"
    MANUAL = "MANUAL"


class EvidenceFlag(str, Enum):
    """Four standardized AI cross-evidence reliability flags (T2-I-M5-03)."""

    SUFFICIENT = "SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"
    CONFLICTING = "CONFLICTING"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class GradingStatus(str, Enum):
    """Lifecycle status of a single student grade entry (06-gradebook-module.md)."""

    UNGRADED = "UNGRADED"
    AI_PROPOSED = "AI_PROPOSED"
    INSTRUCTOR_REVIEWED = "INSTRUCTOR_REVIEWED"


class PostGradesScope(str, Enum):
    """Scope for publishing grades on a muted column (T2-P-M5-05)."""

    ALL = "ALL"
    GRADED_ONLY = "GRADED_ONLY"


class LetterGrade(str, Enum):
    """Vietnamese Higher Education credit scale (Circular 08/2021/TT-BGDDT)."""

    A = "A"
    B_PLUS = "B+"
    B = "B"
    C_PLUS = "C+"
    C = "C"
    D_PLUS = "D+"
    D = "D"
    F = "F"


class SpeedGraderFilter(str, Enum):
    """Instructor student filter options in SpeedGrader top navigation bar."""

    ALL = "ALL"
    NEEDS_GRADING = "NEEDS_GRADING"
    GRADED = "GRADED"
    CONFLICTING = "CONFLICTING"
