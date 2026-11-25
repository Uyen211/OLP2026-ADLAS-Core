# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Domain exceptions for Examination Context inheriting core ADLASException."""

from typing import Optional
from fastapi import status
from app.core.exceptions import ADLASException


class InsufficientQuestionsException(ADLASException):
    """E-EXAM-03: Question bank lacks enough active questions for the requested matrix."""

    def __init__(
        self,
        detail: str = "Ngan hang cau hoi khong du so luong cau hoi hop le theo ma tran de thi.",
        requested: Optional[int] = None,
        available: Optional[int] = None,
    ):
        super().__init__(
            code="E-EXAM-03",
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
        if isinstance(self.detail, dict):
            if requested is not None:
                self.detail["requested"] = requested
            if available is not None:
                self.detail["available"] = available


class InvalidExamWindowException(ADLASException):
    """E-SEC-01: Exam availability window is shorter than time_limit_mins or invalid."""

    def __init__(
        self,
        detail: str = "Khung gio mo de thi phai lon hon hoac bang thoi luong lam bai quy dinh.",
    ):
        super().__init__(
            code="E-SEC-01",
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class InvalidPasscodeException(ADLASException):
    """E-SEC-02: Student provided an incorrect room passcode."""

    def __init__(self, detail: str = "Mat khau phong thi khong chinh xac."):
        super().__init__(
            code="E-SEC-02",
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class IpNotAllowedException(ADLASException):
    """E-SEC-03: Client IP address is outside the configured lab CIDR allowlist."""

    def __init__(
        self,
        detail: str = "Dia chi IP may tram khong thuoc dai IP phong may duoc phep du thi.",
    ):
        super().__init__(
            code="E-SEC-03",
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class ExamClosedException(ADLASException):
    """E-EXAM-CLOSED: Exam is outside availability window or past submission grace period."""

    def __init__(
        self,
        detail: str = "Ky thi chua mo, da dong hoac da qua thoi han nop bai cho phep.",
    ):
        super().__init__(
            code="E-EXAM-CLOSED",
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class RegradeWindowExpiredException(ADLASException):
    """E-REG-01: Regrade submission exceeds the 48-hour window after grade release (BR-REG-02)."""

    def __init__(
        self,
        detail: str = "Da qua thoi han 48 gio gui don phuc khao ke tu thoi diem cong bo diem.",
    ):
        super().__init__(
            code="E-REG-01",
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class ExamAiLockedException(ADLASException):
    """E-13: Learning materials and Socratic AI tutor are locked during an active exam."""

    def __init__(
        self,
        detail: str = "Tai lieu hoc tap va Gia su AI dang tam khoa trong thoi gian lam bai thi.",
    ):
        super().__init__(
            code="E-13",
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class ExaminationNotFoundException(ADLASException):
    """404: Requested question bank, question, quiz, submission, or regrade does not exist."""

    def __init__(self, detail: str = "Khong tim thay du lieu khao thi yeu cau."):
        super().__init__(
            code="E-EXAM-NOT-FOUND",
            detail=detail,
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ExaminationForbiddenException(ADLASException):
    """403: Actor lacks permission to perform the requested examination action."""

    def __init__(
        self,
        detail: str = "Ban khong co quyen thuc hien thao tac nay trong phan he khao thi.",
    ):
        super().__init__(
            code="E-EXAM-FORBIDDEN",
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class ExaminationValidationException(ADLASException):
    """E-2: Invalid examination payload format or invariant violation."""

    def __init__(self, detail: str, field: Optional[str] = None):
        super().__init__(
            code="E-2",
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
        if field and isinstance(self.detail, dict):
            self.detail["field"] = field


class ExaminationStateException(ADLASException):
    """409: Conflicting examination state transition or duplicate action."""

    def __init__(self, detail: str):
        super().__init__(
            code="E-EXAM-STATE",
            detail=detail,
            status_code=status.HTTP_409_CONFLICT,
        )
