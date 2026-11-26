# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Unit tests for Gradebook Phase 1 enums, domain exceptions, ORM models, and Pydantic schemas."""

from decimal import Decimal
import uuid
import pytest
from pydantic import ValidationError
from app.modules.gradebook.enums import (
    EvidenceFlag,
    GradeItemType,
    GradingStatus,
    LetterGrade,
)
from app.modules.gradebook.exceptions import (
    GradebookGroupNotEmptyException,
    GradebookHasMutedColumnsException,
    GradebookLockedException,
    GradebookMutedAccessDeniedException,
    GradebookPokaYokeInvalidException,
    GradebookSumInvalidException,
    GradeOverrideReasonRequiredException,
    GradeScoreRangeException,
)
from app.modules.gradebook.models import (
    CourseGradebookLock,
    GradeAuditLog,
    GradebookColumn,
    GradebookGroup,
    GradeEntry,
)
from app.modules.gradebook.schemas import (
    CitationItemSchema,
    EmergencyUnlockRequest,
    GradebookStructureSaveRequest,
    GradeColumnCreateRequest,
    GradeGroupInput,
    SpeedGraderSaveGradeRequest,
)


def test_gradebook_exceptions_match_error_matrix():
    assert GradebookSumInvalidException(80).detail["code"] == "E-11"
    assert GradebookSumInvalidException(80).status_code == 400
    assert GradebookGroupNotEmptyException(3).detail["code"] == "E-GB-01"
    assert GradebookGroupNotEmptyException(3).status_code == 409
    assert GradeScoreRangeException(11).detail["code"] == "E-GB-02"
    assert GradebookPokaYokeInvalidException().detail["code"] == "E-LOCK-01"
    assert GradebookMutedAccessDeniedException().detail["code"] == "E-GB-05"
    assert GradebookMutedAccessDeniedException().status_code == 403
    assert GradebookHasMutedColumnsException(["Do an"]).detail["code"] == "E-GB-06"
    assert GradebookHasMutedColumnsException(["Do an"]).status_code == 422
    assert GradeOverrideReasonRequiredException(2.0).detail["code"] == "E-GB-07"
    assert GradebookLockedException().detail["code"] == "E-14"
    assert GradebookLockedException().status_code == 423


def test_gradebook_enums_completeness():
    assert {e.value for e in EvidenceFlag} == {
        "SUFFICIENT",
        "INSUFFICIENT",
        "CONFLICTING",
        "HUMAN_REVIEW",
    }
    assert {e.value for e in GradingStatus} == {
        "UNGRADED",
        "AI_PROPOSED",
        "INSTRUCTOR_REVIEWED",
    }
    assert GradeItemType.ASSIGNMENT.value == "ASSIGNMENT"
    assert LetterGrade.B_PLUS.value == "B+"


def test_gradebook_orm_table_schemas():
    assert GradebookGroup.__table__.schema == "gradebook"
    assert GradebookColumn.__table__.schema == "gradebook"
    assert GradeEntry.__table__.schema == "gradebook"
    assert CourseGradebookLock.__table__.schema == "gradebook"
    assert GradeAuditLog.__table__.schema == "gradebook"


def test_pydantic_schemas_validation_boundaries():
    # Valid group input
    req = GradebookStructureSaveRequest(
        groups=[
            GradeGroupInput(group_name="Chuyen can", weight_percent=10),
            GradeGroupInput(group_name="Thi cuoi ky", weight_percent=90, is_hurdle=True),
        ]
    )
    assert len(req.groups) == 2

    # Invalid blank group name
    with pytest.raises(ValidationError):
        GradeGroupInput(group_name="   ", weight_percent=50)

    # Invalid score > 10.0 in SpeedGraderSaveGradeRequest
    with pytest.raises(ValidationError):
        SpeedGraderSaveGradeRequest(official_score=Decimal("10.5"))

    # Valid citation source_type
    c = CitationItemSchema(source_type="VIVA", reference="Cau 1", excerpt="Sinh vien giai thich CRF...")
    assert c.source_type == "VIVA"

    with pytest.raises(ValidationError):
        CitationItemSchema(source_type="INVALID", reference="x", excerpt="y")

    # Emergency unlock requires reason >= 30 chars
    with pytest.raises(ValidationError):
        EmergencyUnlockRequest(decision_code="QD-01", reason="Qua ngan")

    valid_unlock = EmergencyUnlockRequest(
        decision_code="QD-2026-09",
        reason="Co quyet dinh phuc khao chinh thuc tu Ban Chu nhiem Khoa cho sinh vien SV2026001.",
    )
    assert valid_unlock.decision_code == "QD-2026-09"

    col = GradeColumnCreateRequest(
        group_id=uuid.uuid4(),
        title="Do an giua ky",
        item_type=GradeItemType.ASSIGNMENT,
    )
    assert col.is_muted is True
