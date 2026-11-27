# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Excel (.xlsx) builder: 2 sheets (TT08 credit grades and LO competency profile)."""

import io
from typing import Any, List
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet
from app.modules.analytics.reporting.sanitizer import sanitize_cell
from app.modules.analytics.reporting.schemas import (
    SHEET_GRADES,
    SHEET_LO,
    WATERMARK_TEXT,
    ReportData,
)

SCORE_FORMAT = "0.0"
HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HURDLE_FILL = PatternFill("solid", fgColor="F8CBAD")
WATERMARK_FONT = Font(bold=True, color="C00000", size=14)


def _num(value: Any) -> Any:
    return None if value is None else float(value)


def _write_banner(ws: Worksheet, data: ReportData, title: str, span: int) -> int:
    """Write title (+ watermark when unlocked). Returns the next free row."""
    ws.cell(row=1, column=1, value=sanitize_cell(title)).font = Font(bold=True, size=14)
    row = 2
    ws.cell(
        row=row,
        column=1,
        value=sanitize_cell(
            f"Học phần: {data.course_name} ({data.course_code}) - Lớp: {data.section_code} - {data.semester}"
        ),
    )
    row += 1
    if not data.is_locked:
        cell = ws.cell(row=row, column=1, value=WATERMARK_TEXT)
        cell.font = WATERMARK_FONT
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=max(span, 2))
        ws.oddHeader.center.text = WATERMARK_TEXT
        row += 1
    return row + 1


def _write_header(ws: Worksheet, row: int, headers: List[str]) -> None:
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=col, value=sanitize_cell(header))
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _autosize(ws: Worksheet, widths: List[int]) -> None:
    for index, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(index)].width = width


def _build_grade_sheet(ws: Worksheet, data: ReportData) -> None:
    headers = (
        ["STT", "MSSV", "Họ và tên"]
        + list(data.group_names)
        + ["Tổng kết (Thang 10)", "Điểm chữ", "Thang 4", "Ghi chú"]
    )
    row = _write_banner(ws, data, "BẢNG ĐIỂM TÍN CHỈ THEO THÔNG TƯ 08/2021/TT-BGDĐT", len(headers))
    _write_header(ws, row, headers)
    for index, student in enumerate(data.rows, start=1):
        row += 1
        values: List[Any] = [index, student.user_code, student.full_name]
        values += [_num(student.group_scores.get(name)) for name in data.group_names]
        values += [_num(student.total_score), student.letter_grade, _num(student.scale4), student.remark]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=row, column=col, value=sanitize_cell(value) if value is not None else None)
            if isinstance(value, float):
                cell.number_format = SCORE_FORMAT
            if student.hurdle_failed:
                cell.fill = HURDLE_FILL
    _autosize(ws, [6, 14, 28] + [14] * len(data.group_names) + [18, 10, 10, 14])
    ws.freeze_panes = ws.cell(row=row - len(data.rows) + 1, column=4)


def _build_lo_sheet(ws: Worksheet, data: ReportData) -> None:
    lo_headers = ["Mã LO", "Mô tả chuẩn đầu ra", "Mức Bloom", "Tiêu chí Rubric liên kết", "Tổng điểm tối đa"]
    row = _write_banner(ws, data, "HỒ SƠ NĂNG LỰC THEO CHUẨN ĐẦU RA HỌC PHẦN (LO)", len(lo_headers))
    _write_header(ws, row, lo_headers)
    for lo in data.lo_rows:
        row += 1
        values = [lo.code, lo.description, lo.bloom_level, "; ".join(lo.criterion_titles), float(lo.max_points)]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=row, column=col, value=sanitize_cell(value))
            if isinstance(value, float):
                cell.number_format = SCORE_FORMAT
    row += 2
    matrix_headers = ["MSSV", "Họ và tên"] + [f"{lo.code} (%)" for lo in data.lo_rows]
    _write_header(ws, row, matrix_headers)
    for student in data.rows:
        row += 1
        values = [student.user_code, student.full_name] + [
            _num(student.lo_attainment.get(lo.code)) for lo in data.lo_rows
        ]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=row, column=col, value=sanitize_cell(value) if value is not None else None)
            if isinstance(value, float):
                cell.number_format = SCORE_FORMAT
    _autosize(ws, [14, 40, 14, 40, 16] + [12] * max(0, len(data.lo_rows) - 3))


def build_excel(data: ReportData) -> bytes:
    workbook = Workbook()
    grade_sheet = workbook.active
    grade_sheet.title = SHEET_GRADES
    _build_grade_sheet(grade_sheet, data)
    lo_sheet = workbook.create_sheet(SHEET_LO)
    _build_lo_sheet(lo_sheet, data)
    buffer = io.BytesIO()
    workbook.save(buffer)
    workbook.close()
    return buffer.getvalue()
