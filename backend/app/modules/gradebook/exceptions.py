# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Domain exceptions for Gradebook & SpeedGrader mapped to ADLAS error matrix."""

from fastapi import status
from app.core.exceptions import ADLASException, GradebookLockedException

__all__ = [
    "GradebookLockedException",
    "GradebookSumInvalidException",
    "GradebookGroupNotEmptyException",
    "GradeScoreRangeException",
    "GradebookPokaYokeInvalidException",
    "GradebookMutedAccessDeniedException",
    "GradebookHasMutedColumnsException",
    "GradeOverrideReasonRequiredException",
    "GradebookNotFoundException",
    "GradebookForbiddenException",
    "GradebookInvalidVoiceFileException",
]


class GradebookSumInvalidException(ADLASException):
    """E-11: Total weight of gradebook groups does not equal 100%."""

    def __init__(self, current_sum: int):
        super().__init__(
            code="E-11",
            detail=(
                f"Tong trong so hien tai la {current_sum}%. "
                "Vui long dieu chinh cac nhom diem sao cho tong dung bang 100% truoc khi luu."
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class GradebookGroupNotEmptyException(ADLASException):
    """E-GB-01: Deleting a grade group containing existing scores requires 'XOA' confirmation."""

    def __init__(self, graded_count: int):
        super().__init__(
            code="E-GB-01",
            detail=(
                f"Nhom diem nay hien dang chua {graded_count} du lieu diem cua sinh vien. "
                "Vui long nhap chinh xac tu khoa XOA de xac nhan xoa."
            ),
            status_code=status.HTTP_409_CONFLICT,
        )


class GradeScoreRangeException(ADLASException):
    """E-GB-02 / E-CALC-02: Score must lie within [0.0, 10.0]."""

    def __init__(self, score: object):
        super().__init__(
            code="E-GB-02",
            detail=f"Diem so ({score}) khong hop le. Diem so phai la gia tri tu 0.0 den 10.0.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class GradebookPokaYokeInvalidException(ADLASException):
    """E-GB-04 / E-LOCK-01: Confirmation phrase does not match exact 'KHOA DIEM'."""

    def __init__(self):
        super().__init__(
            code="E-LOCK-01",
            detail="Cum tu nhap vao chua khop chinh xac. Vui long go dung chu in hoa: KHOA DIEM.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class GradebookMutedAccessDeniedException(ADLASException):
    """E-GB-05: Student attempted to access grades on a muted column (BR-09)."""

    def __init__(self):
        super().__init__(
            code="E-GB-05",
            detail="Cot diem nay dang o trang thai an (Muted) cho toi khi Giang vien cong bo.",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class GradebookHasMutedColumnsException(ADLASException):
    """E-GB-06: Cannot seal final gradebook while muted columns remain unpublished."""

    def __init__(self, muted_titles: list[str]):
        joined = ", ".join(muted_titles)
        super().__init__(
            code="E-GB-06",
            detail=(
                f"Khong the khoa so diem vi van con cot diem chua cong bo (Muted): {joined}. "
                "Vui long cong bo toan bo cot diem truoc khi khoa so."
            ),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class GradeOverrideReasonRequiredException(ADLASException):
    """E-GB-07: Large score override (> 1.5 pts vs AI proposal) requires an explicit reason (BR-07)."""

    def __init__(self, delta: float):
        super().__init__(
            code="E-GB-07",
            detail=(
                f"Diem chinh thuc chenh lech {delta:.2f} diem so voi de xuat cua AI (> 1.5 diem). "
                "Vui long nhap ly do ghi de (override_reason) de luu vet kiem toan."
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class GradebookNotFoundException(ADLASException):
    """Resource not found inside Gradebook context."""

    def __init__(self, resource: str = "Du lieu so diem"):
        super().__init__(
            code="E-GB-404",
            detail=f"Khong tim thay {resource} yeu cau.",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class GradebookForbiddenException(ADLASException):
    """Insufficient contextual course role for gradebook action."""

    def __init__(self):
        super().__init__(
            code="E-GB-403",
            detail="Ban khong co quyen thuc hien thao tac nay trong so diem mon hoc.",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class GradebookInvalidVoiceFileException(ADLASException):
    """E-7: Uploaded voice feedback file violates format or size constraint."""

    def __init__(self, reason: str):
        super().__init__(
            code="E-7",
            detail=reason,
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )
