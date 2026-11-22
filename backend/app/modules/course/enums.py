# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Domain enumerations for Course Context."""

from enum import Enum


class CourseStatus(str, Enum):
    """Lifecycle states of a course section."""

    UNPUBLISHED = "UNPUBLISHED"
    PUBLISHED = "PUBLISHED"
    ENROLLMENT_CLOSED = "ENROLLMENT_CLOSED"
    ARCHIVED = "ARCHIVED"


class ContextualRole(str, Enum):
    """Per-course contextual role assigned to a user (BR-01)."""

    INSTRUCTOR = "INSTRUCTOR"
    STUDENT = "STUDENT"
    TA = "TA"


class EnrollmentStatus(str, Enum):
    """Membership state of a user within a course."""

    ACTIVE = "ACTIVE"
    DROPPED = "DROPPED"
    COMPLETED = "COMPLETED"


class BloomLevel(str, Enum):
    """Six-tier Bloom cognitive taxonomy stored in course.learning_objectives."""

    REMEMBER = "REMEMBER"
    UNDERSTAND = "UNDERSTAND"
    APPLY = "APPLY"
    ANALYZE = "ANALYZE"
    EVALUATE = "EVALUATE"
    CREATE = "CREATE"


class GroupingMode(str, Enum):
    """Group partitioning strategies (T2-P-M1-03 Subflow A-1)."""

    RANDOM = "RANDOM"
    SELF_SIGNUP = "SELF_SIGNUP"
    MANUAL = "MANUAL"


class RosterRowStatus(str, Enum):
    """Validation status for a single row during Excel/CSV roster preview."""

    VALID = "VALID"
    DUPLICATE_IN_COURSE = "DUPLICATE_IN_COURSE"
    DUPLICATE_IN_FILE = "DUPLICATE_IN_FILE"
    INVALID = "INVALID"
