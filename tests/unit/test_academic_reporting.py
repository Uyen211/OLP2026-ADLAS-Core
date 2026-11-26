# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Pure unit tests for Academic Grade Reporting (T2-P-M6-03): Sanitizer, TT08, Excel, CSV, PDF."""

from datetime import datetime, timezone
from decimal import Decimal
import io
from unittest.mock import AsyncMock, MagicMock
import uuid
import fitz
import openpyxl
import pytest
from app.modules.analytics.reporting.csv_builder import build_csv
from app.modules.analytics.reporting.data_provider import (
    CourseGradeMatrixDTO,
    GradebookLockDTO,
    GradeCellDTO,
    GradeColumnDTO,
    LoCompetencyDTO,
)
from app.modules.analytics.reporting.excel_builder import build_excel
from app.modules.analytics.reporting.exceptions import (
    MissingGradesConfirmationRequiredException,
    ReportAccessDeniedException,
    ReportDataUnavailableException,
)
from app.modules.analytics.reporting.pdf_builder import build_pdf
from app.modules.analytics.reporting.sanitizer import (
    build_filename,
    convert_grade,
    round_score,
    sanitize_cell,
)
from app.modules.analytics.reporting.schemas import (
    SHEET_GRADES,
    SHEET_LO,
    WATERMARK_TEXT,
    ExportFormat,
    LoRow,
    ReportData,
    StudentGradeRow,
)
from app.modules.analytics.reporting.service import ReportingService, compute_student_rows
from app.modules.course.enums import BloomLevel
from app.modules.course.exceptions import CourseForbiddenException
from app.modules.course.public_api import CourseInfoDTO, CoursePublicService, LODTO, StudentEnrollmentDTO


def _sample_report(is_locked: bool = False) -> ReportData:
    return ReportData(
        course_code="IT3080",
        section_code="150245",
        course_name="Mạng máy tính",
        semester="2026-1",
        credits=3,
        is_locked=is_locked,
        locked_at=datetime.now(timezone.utc) if is_locked else None,
        group_names=["Quá trình", "Cuối kỳ"],
        rows=[
            StudentGradeRow(
                user_id=uuid.uuid4(),
                user_code="20220001",
                full_name="=SUM(A1:A2) Nguyễn Văn A",
                email="a@adlas.edu.vn",
                group_scores={"Quá trình": Decimal("8.5"), "Cuối kỳ": Decimal("9.0")},
                total_score=Decimal("8.8"),
                letter_grade="A",
                scale4=Decimal("4.0"),
                hurdle_failed=False,
                missing=False,
                lo_attainment={"LO1": Decimal("90.0")},
            ),
            StudentGradeRow(
                user_id=uuid.uuid4(),
                user_code="20220002",
                full_name="Trần Thị B",
                email="b@adlas.edu.vn",
                group_scores={"Quá trình": Decimal("9.0"), "Cuối kỳ": Decimal("2.0")},
                total_score=Decimal("5.5"),
                letter_grade="F",
                scale4=Decimal("0.0"),
                hurdle_failed=True,
                missing=False,
                lo_attainment={"LO1": Decimal("45.0")},
            ),
        ],
        lo_rows=[
            LoRow(
                code="LO1",
                description="Thiết kế giao thức tầng giao vận",
                bloom_level="APPLY",
                criterion_titles=("Phân tích gói tin",),
                max_points=Decimal("10.0"),
            )
        ],
    )


# ----------------------------------------------------------------------
# Sanitizer, Rounding & TT08 Conversion
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "payload",
    [
        "=cmd|'/C calc'!A0",
        "=SUM(A1:A10)",
        "+2+3",
        "-1+1",
        "@SUM(1,2)",
        "|cat /etc/passwd",
        "\t=1+1",
        "\r=1+1",
    ],
)
def test_formula_injection_sanitizer_prefixes_quote(payload: str):
    sanitized = sanitize_cell(payload)
    assert sanitized == "'" + payload


def test_sanitizer_preserves_safe_text_and_numbers():
    assert sanitize_cell("Nguyễn Văn An") == "Nguyễn Văn An"
    assert sanitize_cell(Decimal("8.5")) == Decimal("8.5")
    assert sanitize_cell(9.2) == 9.2
    assert sanitize_cell(None) == ""


def test_round_score_half_up_and_tt08_grade_table():
    assert round_score("8.25") == Decimal("8.3")
    assert round_score("8.45") == Decimal("8.5")
    assert round_score("3.95") == Decimal("4.0")
    assert round_score(None) is None

    expected = [
        ("8.5", "A", Decimal("4.0"), True),
        ("8.0", "B+", Decimal("3.5"), True),
        ("7.0", "B", Decimal("3.0"), True),
        ("6.5", "C+", Decimal("2.5"), True),
        ("5.5", "C", Decimal("2.0"), True),
        ("5.0", "D+", Decimal("1.5"), True),
        ("4.0", "D", Decimal("1.0"), True),
        ("3.9", "F", Decimal("0.0"), False),
    ]
    for raw, letter, s4, passed in expected:
        res = convert_grade(raw)
        assert (res.letter, res.scale4, res.passed) == (letter, s4, passed)

    # Hurdle failure forces F / 0.0 regardless of high weighted score
    hurdle_res = convert_grade("8.8", hurdle_failed=True)
    assert hurdle_res.score10 == Decimal("8.8")
    assert hurdle_res.letter == "F"
    assert hurdle_res.scale4 == Decimal("0.0")
    assert hurdle_res.passed is False


def test_ascii_safe_filename_generation():
    assert build_filename("CNTT-K67 Đ1", "IT 3080", True, "xlsx") == "CNTTK67D1_IT3080_BangDiem_ChinhThuc.xlsx"
    assert build_filename("150245", "IT3080", False, "pdf") == "150245_IT3080_BangDiem_DU_KIEN.pdf"


# ----------------------------------------------------------------------
# Excel (2-Sheet + Watermark), CSV (UTF-8 BOM), PDF (%PDF- A4 Landscape)
# ----------------------------------------------------------------------
def test_excel_builder_two_sheets_watermark_and_sanitization():
    # Unlocked -> has Watermark
    draft_bytes = build_excel(_sample_report(is_locked=False))
    wb = openpyxl.load_workbook(io.BytesIO(draft_bytes))
    assert wb.sheetnames == [SHEET_GRADES, SHEET_LO]
    ws_grades = wb[SHEET_GRADES]
    all_values = [cell.value for row in ws_grades.iter_rows() for cell in row if cell.value is not None]
    assert WATERMARK_TEXT in all_values
    assert "'=SUM(A1:A2) Nguyễn Văn A" in all_values
    wb.close()

    # Locked -> NO Watermark
    locked_bytes = build_excel(_sample_report(is_locked=True))
    wb_locked = openpyxl.load_workbook(io.BytesIO(locked_bytes))
    assert wb_locked.sheetnames == [SHEET_GRADES, SHEET_LO]
    locked_vals = [cell.value for row in wb_locked[SHEET_GRADES].iter_rows() for cell in row if cell.value is not None]
    assert WATERMARK_TEXT not in locked_vals
    wb_locked.close()


def test_csv_builder_utf8_bom_and_formula_sanitized():
    csv_bytes = build_csv(_sample_report(is_locked=False))
    assert csv_bytes.startswith(b"\xef\xbb\xbf")
    text = csv_bytes.decode("utf-8-sig")
    assert "'=SUM(A1:A2) Nguyễn Văn A" in text
    assert "DU_KIEN" in text


def test_pdf_builder_valid_a4_landscape_and_watermark():
    draft_pdf = build_pdf(_sample_report(is_locked=False))
    assert draft_pdf.startswith(b"%PDF-")
    doc = fitz.open(stream=draft_pdf, filetype="pdf")
    assert doc.page_count >= 1
    rect = doc[0].rect
    assert rect.width > rect.height  # A4 landscape
    page_text = doc[0].get_text()
    assert "IT3080" in page_text
    doc.close()

    locked_pdf = build_pdf(_sample_report(is_locked=True))
    assert locked_pdf.startswith(b"%PDF-")


# ----------------------------------------------------------------------
# Pure Grade Calculation & ReportingService Orchestration
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_reporting_service_authorization_missing_grades_and_export():
    course_id = uuid.uuid4()
    g1, g2 = uuid.uuid4(), uuid.uuid4()
    c1, c2 = uuid.uuid4(), uuid.uuid4()
    s1, s2 = uuid.uuid4(), uuid.uuid4()
    lo_id = uuid.uuid4()

    matrix = CourseGradeMatrixDTO(
        course_id=course_id,
        columns=(
            GradeColumnDTO(c1, g1, "Quá trình", 40, False, None, "GK", Decimal("10")),
            GradeColumnDTO(c2, g2, "Cuối kỳ", 60, True, Decimal("3.0"), "CK", Decimal("10")),
        ),
        cells=(
            GradeCellDTO(c1, s1, Decimal("8.0"), {str(lo_id): 8.0}),
            GradeCellDTO(c2, s1, Decimal("9.0"), None),
            # s2 is missing final exam score -> triggers E-EXP-01 when unlocked
            GradeCellDTO(c1, s2, Decimal("7.0"), None),
        ),
        students=(
            StudentEnrollmentDTO(s1, "20220001", "Nguyễn Văn A", "a@adlas.edu.vn"),
            StudentEnrollmentDTO(s2, "20220002", "Trần Thị B", "b@adlas.edu.vn"),
        ),
    )
    lo_profile = [
        LoCompetencyDTO(
            lo=LODTO(lo_id, course_id, "LO1", "Thiết kế", BloomLevel.APPLY, 1),
            criterion_titles=("Tiêu chí 1",),
            criterion_max_points=Decimal("10.0"),
        )
    ]

    groups, rows = compute_student_rows(matrix, lo_profile)
    assert groups == ["Quá trình", "Cuối kỳ"]
    assert rows[0].total_score == Decimal("8.6")
    assert rows[0].letter_grade == "A"
    assert rows[0].lo_attainment["LO1"] == Decimal("80.0")
    assert rows[1].missing is True

    provider = AsyncMock()
    provider.get_lock_status.return_value = GradebookLockDTO(course_id=course_id, is_locked=False)
    provider.get_grade_matrix.return_value = matrix
    provider.get_lo_competency_profile.return_value = lo_profile

    course_svc = AsyncMock(spec=CoursePublicService)
    course_svc.get_course_info.return_value = CourseInfoDTO(
        id=course_id,
        course_code="IT3080",
        section_code="150245",
        name="Mạng máy tính",
        semester="2026-1",
        credits=3,
    )

    user = MagicMock(id=uuid.uuid4(), system_role="USER")
    svc = ReportingService(db=AsyncMock(), provider=provider, course_service=course_svc)

    # 1. Non-instructor -> E-REP-01
    course_svc.assert_course_role.side_effect = CourseForbiddenException()
    with pytest.raises(ReportAccessDeniedException) as exc_role:
        await svc.preview(course_id, user)
    assert exc_role.value.detail["code"] == "E-REP-01"
    course_svc.assert_course_role.side_effect = None

    # 2. Preview shows missing count & requires_confirmation
    preview = await svc.preview(course_id, user)
    assert preview.missing_grade_students_count == 1
    assert preview.requires_confirmation is True
    assert preview.watermark_text == WATERMARK_TEXT

    # 3. Draft export without confirm_draft -> E-EXP-01
    with pytest.raises(MissingGradesConfirmationRequiredException) as exc_exp:
        await svc.export(course_id, user, ExportFormat.EXCEL, confirm_draft=False)
    assert exc_exp.value.detail["code"] == "E-EXP-01"

    # 4. With confirm_draft=True -> succeeds
    result = await svc.export(course_id, user, ExportFormat.EXCEL, confirm_draft=True)
    assert result.filename == "150245_IT3080_BangDiem_DU_KIEN.xlsx"
    assert len(result.content) > 0

    # 5. Course not found -> E-REP-02
    course_svc.get_course_info.return_value = None
    with pytest.raises(ReportDataUnavailableException) as exc_data:
        await svc.preview(course_id, user)
    assert exc_data.value.detail["code"] == "E-REP-02"
