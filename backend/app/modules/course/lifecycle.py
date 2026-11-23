# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Pure finite state machine (FSM) governing course lifecycle transitions."""

from typing import Dict, Set
from app.modules.course.enums import CourseStatus
from app.modules.course.exceptions import InvalidCourseStateException

ALLOWED_TRANSITIONS: Dict[CourseStatus, Set[CourseStatus]] = {
    CourseStatus.UNPUBLISHED: {CourseStatus.PUBLISHED},
    CourseStatus.PUBLISHED: {CourseStatus.ENROLLMENT_CLOSED, CourseStatus.ARCHIVED},
    CourseStatus.ENROLLMENT_CLOSED: {CourseStatus.PUBLISHED, CourseStatus.ARCHIVED},
    CourseStatus.ARCHIVED: set(),
}


def can_transition(current: CourseStatus, target: CourseStatus) -> bool:
    """Return True if transitioning from `current` to `target` is permitted."""
    return target in ALLOWED_TRANSITIONS.get(current, set())


def assert_transition(current: CourseStatus, target: CourseStatus) -> None:
    """Validate course lifecycle transition or raise E-COURSE-STATE."""
    if not can_transition(current, target):
        raise InvalidCourseStateException(
            f"Khong the chuyen trang thai mon hoc tu '{current.value}' sang '{target.value}'."
        )


def assert_mutable(current: CourseStatus) -> None:
    """Reject mutations on ARCHIVED courses (read-only permanently)."""
    if current == CourseStatus.ARCHIVED:
        raise InvalidCourseStateException(
            "Mon hoc da duoc luu tru (ARCHIVED) va o che do chi doc vinh vien."
        )


def sync_enrollment_open(target: CourseStatus) -> bool:
    """Derive synchronized `is_enrollment_open` flag for a target lifecycle status."""
    if target == CourseStatus.PUBLISHED:
        return True
    if target in {CourseStatus.ENROLLMENT_CLOSED, CourseStatus.ARCHIVED}:
        return False
    return True
