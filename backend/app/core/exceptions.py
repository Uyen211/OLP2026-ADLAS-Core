# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

from fastapi import HTTPException, status


class ADLASException(HTTPException):
    def __init__(self, code: str, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail={"code": code, "message": detail})


# Standard System Exceptions (E-1 to E-14)
class ValidationRequiredException(ADLASException):
    def __init__(self, field: str):
        super().__init__(code="E-1", detail=f"Field '{field}' is required and cannot be empty.", status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


class ValidationFormatException(ADLASException):
    def __init__(self, detail: str = "Invalid format provided."):
        super().__init__(code="E-2", detail=detail, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


class AuthInvalidCredentialsException(ADLASException):
    def __init__(self):
        super().__init__(code="E-5", detail="Invalid username or password.", status_code=status.HTTP_401_UNAUTHORIZED)


class AuthRateLimitedException(ADLASException):
    def __init__(self):
        super().__init__(code="E-6", detail="Account temporarily locked due to too many failed attempts.", status_code=status.HTTP_429_TOO_MANY_REQUESTS)


class SubmissionClosedException(ADLASException):
    def __init__(self):
        super().__init__(code="E-8", detail="The submission deadline (Until Date) has passed.", status_code=status.HTTP_403_FORBIDDEN)


class IntegrityPasteBlockedException(ADLASException):
    def __init__(self):
        super().__init__(code="E-9", detail="Paste operations are strictly disabled in Viva Sandbox.", status_code=status.HTTP_400_BAD_REQUEST)


class GradebookLockedException(ADLASException):
    def __init__(self):
        super().__init__(code="E-14", detail="Gradebook is locked and cannot be modified without formal authorization.", status_code=status.HTTP_423_LOCKED)
