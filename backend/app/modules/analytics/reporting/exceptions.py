# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Domain exceptions for academic grade report export (T2-P-M6-03)."""

from fastapi import status
from app.core.exceptions import ADLASException


class MissingGradesConfirmationRequiredException(ADLASException):
    """E-EXP-01: some students lack component grades; draft export needs explicit confirmation."""

    def __init__(self, missing_count: int):
        super().__init__(
            code="E-EXP-01",
            detail=(
                f"{missing_count} student(s) do not have all component grades yet. "
                "Confirm draft export (confirm_draft=true) to continue."
            ),
            status_code=status.HTTP_409_CONFLICT,
        )
        self.missing_count = missing_count


class ReportAccessDeniedException(ADLASException):
    """E-REP-01: only the course Instructor or an Admin may export grade reports."""

    def __init__(self):
        super().__init__(
            code="E-REP-01",
            detail="Only the course instructor or an administrator can export grade reports.",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class ReportDataUnavailableException(ADLASException):
    """E-REP-02: the course does not exist or has no gradebook data to export."""

    def __init__(self, detail: str = "No gradebook data is available for this course."):
        super().__init__(
            code="E-REP-02",
            detail=detail,
            status_code=status.HTTP_404_NOT_FOUND,
        )
