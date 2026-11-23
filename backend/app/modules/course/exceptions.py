# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Domain exceptions for Course Context inheriting core ADLASException."""

from typing import List, Optional
from fastapi import status
from app.core.exceptions import ADLASException


class DuplicateResourceException(ADLASException):
    """E-4: Duplicate course section in semester or duplicate LO code in course."""

    def __init__(self, detail: str, field: Optional[str] = None):
        super().__init__(
            code="E-4",
            detail=detail,
            status_code=status.HTTP_409_CONFLICT,
        )
        if field and isinstance(self.detail, dict):
            self.detail["field"] = field


class LoInUseException(ADLASException):
    """BR-LO-01: Learning objective is referenced by assessments/materials and cannot be deleted."""

    def __init__(self, lo_code: Optional[str] = None):
        msg = (
            f"Chuan dau ra '{lo_code}' dang duoc su dung trong bai giang hoac de thi, khong the xoa."
            if lo_code
            else "Chuan dau ra dang duoc tham chieu, chi cho phep chinh sua mo ta."
        )
        super().__init__(
            code="E-LO-IN-USE",
            detail=msg,
            status_code=status.HTTP_409_CONFLICT,
        )


class InvalidCourseStateException(ADLASException):
    """E-COURSE-STATE: Forbidden lifecycle transition or write on ARCHIVED course."""

    def __init__(self, detail: str):
        super().__init__(
            code="E-COURSE-STATE",
            detail=detail,
            status_code=status.HTTP_409_CONFLICT,
        )


class JoinCodeInvalidException(ADLASException):
    """E-JOIN-01: Join code does not exist (404) or course enrollment is closed (403)."""

    def __init__(self, detail: str, status_code: int = status.HTTP_404_NOT_FOUND):
        super().__init__(
            code="E-JOIN-01",
            detail=detail,
            status_code=status_code,
        )


class JoinCodeRateLimitException(ADLASException):
    """E-JOIN-02: Too many join code attempts within one minute."""

    def __init__(self, retry_after_seconds: int = 60):
        super().__init__(
            code="E-JOIN-02",
            detail="Ban da thu nhap ma vao lop qua nhieu lan. Vui long thu lai sau 1 phut.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
        if isinstance(self.detail, dict):
            self.detail["retry_after_seconds"] = max(1, int(retry_after_seconds))


class RosterFormatException(ADLASException):
    """E-ROSTER-01: Uploaded Excel/CSV file is corrupted or missing required columns."""

    def __init__(self, detail: str, missing_columns: Optional[List[str]] = None):
        super().__init__(
            code="E-ROSTER-01",
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
        if missing_columns is not None and isinstance(self.detail, dict):
            self.detail["missing_columns"] = missing_columns


class RosterDuplicateException(ADLASException):
    """E-ROSTER-02: Student is already enrolled in the course (BR-ROSTER-01)."""

    def __init__(self, detail: str = "Sinh vien da co trong danh sach lop hoc."):
        super().__init__(
            code="E-ROSTER-02",
            detail=detail,
            status_code=status.HTTP_409_CONFLICT,
        )


class RosterFileTooLargeException(ADLASException):
    """E-7: Uploaded roster file exceeds the 5MB limit."""

    def __init__(self, max_mb: int = 5):
        super().__init__(
            code="E-7",
            detail=f"Tep tai len vuot qua dung luong toi da cho phep ({max_mb}MB).",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )


class CourseValidationException(ADLASException):
    """E-2: Invalid course or group payload format."""

    def __init__(self, detail: str, field: Optional[str] = None):
        super().__init__(
            code="E-2",
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
        if field and isinstance(self.detail, dict):
            self.detail["field"] = field


class CourseForbiddenException(ADLASException):
    """403: Actor lacks required contextual role in the target course."""

    def __init__(self, detail: str = "Ban khong co quyen thuc hien thao tac nay trong mon hoc."):
        super().__init__(
            code="E-COURSE-FORBIDDEN",
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class CourseNotFoundException(ADLASException):
    """404: Requested course, learning objective, or group does not exist."""

    def __init__(self, detail: str = "Khong tim thay du lieu mon hoc yeu cau."):
        super().__init__(
            code="E-COURSE-NOT-FOUND",
            detail=detail,
            status_code=status.HTTP_404_NOT_FOUND,
        )
