# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Pure student group partitioning algorithm using secrets.SystemRandom."""

import math
import secrets
from typing import List, Sequence, Set, Tuple
import uuid
from app.modules.course.exceptions import CourseValidationException


def partition_students_random(
    student_ids: Sequence[uuid.UUID],
    group_size: int,
) -> List[Tuple[str, List[uuid.UUID]]]:
    """
    Randomly partition students into balanced groups using `secrets.SystemRandom`.
    Group sizes differ by at most 1 (e.g., 40 students with size 4 => 10 groups of 4).
    """
    if group_size < 2 or group_size > 10:
        raise CourseValidationException(
            detail="So luong sinh vien moi nhom phai tu 2 den 10.",
            field="group_size",
        )

    total = len(student_ids)
    if total == 0:
        return []

    shuffled = list(student_ids)
    secrets.SystemRandom().shuffle(shuffled)

    num_groups = max(1, math.ceil(total / group_size))
    base_size, remainder = divmod(total, num_groups)

    groups: List[Tuple[str, List[uuid.UUID]]] = []
    cursor = 0
    for idx in range(num_groups):
        size = base_size + (1 if idx < remainder else 0)
        members = shuffled[cursor : cursor + size]
        cursor += size
        groups.append((f"Nhom {idx + 1}", members))

    return groups


def validate_group_set_members(
    groups: Sequence[Tuple[str, Sequence[uuid.UUID]]],
    active_student_ids: Set[uuid.UUID],
) -> None:
    """
    Ensure every member in a group set belongs to the course's active roster
    and appears in at most one group within the set.
    """
    seen: Set[uuid.UUID] = set()
    for group_name, member_ids in groups:
        if not group_name.strip():
            raise CourseValidationException(
                detail="Ten nhom khong duoc de trong.",
                field="groups",
            )
        for uid in member_ids:
            if uid not in active_student_ids:
                raise CourseValidationException(
                    detail=f"Sinh vien '{uid}' khong nam trong danh sach dang hoat dong cua lop.",
                    field="groups",
                )
            if uid in seen:
                raise CourseValidationException(
                    detail=f"Sinh vien '{uid}' bi trung lap trong nhieu nhom cua cung bo nhom.",
                    field="groups",
                )
            seen.add(uid)
