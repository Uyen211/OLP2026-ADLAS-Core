# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""PDF builder (PyMuPDF): A4 landscape official grade sheet with 3 signature boxes."""

import os
import re
from typing import List, Optional, Tuple
import unicodedata
import fitz
from app.modules.analytics.reporting.schemas import WATERMARK_TEXT, ReportData

PAGE_W, PAGE_H = 842.0, 595.0  # A4 landscape in points
MARGIN = 36.0
ROW_H = 18.0
FONT_NAME = "advnfont"
FONT_CANDIDATES = (
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\times.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
)
SIGNATURES = ("Giảng viên chấm thi", "Trưởng Bộ môn", "Trưởng Khoa")


def _find_font() -> Optional[str]:
    custom = os.environ.get("ADLAS_REPORT_FONT")
    for path in ((custom,) if custom else ()) + FONT_CANDIDATES:
        if path and os.path.exists(path):
            return path
    return None


def _fold(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.replace("Đ", "D").replace("đ", "d"))
    return re.sub(r"[^\x00-\x7f]", "", folded)


class _Canvas:
    """Thin wrapper that handles Unicode font vs. ASCII-folded fallback."""

    def __init__(self, doc: "fitz.Document", is_locked: bool):
        self.doc = doc
        self.is_locked = is_locked
        self.font_path = _find_font()
        self.page: "fitz.Page" = None  # type: ignore[assignment]

    def text(self, x: float, y: float, value: str, size: float = 9, bold_color=(0, 0, 0)) -> None:
        content = value if self.font_path else _fold(value)
        self.page.insert_text(
            (x, y),
            content,
            fontsize=size,
            fontname=FONT_NAME if self.font_path else "helv",
            color=bold_color,
        )

    def centered(self, cx: float, y: float, value: str, size: float = 9) -> None:
        content = value if self.font_path else _fold(value)
        font = fitz.Font(fontfile=self.font_path) if self.font_path else fitz.Font("helv")
        width = font.text_length(content, fontsize=size)
        self.text(cx - width / 2, y, value, size)

    def new_page(self) -> None:
        self.page = self.doc.new_page(width=PAGE_W, height=PAGE_H)
        if self.font_path:
            self.page.insert_font(fontname=FONT_NAME, fontfile=self.font_path)
        if not self.is_locked:
            self._watermark()

    def _watermark(self) -> None:
        content = WATERMARK_TEXT if self.font_path else _fold(WATERMARK_TEXT)
        pivot = fitz.Point(PAGE_W / 2, PAGE_H / 2)
        matrix = fitz.Matrix(1, 1).prerotate(30)
        font = fitz.Font(fontfile=self.font_path) if self.font_path else fitz.Font("helv")
        width = font.text_length(content, fontsize=34)
        self.page.insert_text(
            (pivot.x - width / 2, pivot.y),
            content,
            fontsize=34,
            fontname=FONT_NAME if self.font_path else "helv",
            color=(0.93, 0.62, 0.62),
            morph=(pivot, matrix),
        )


def _column_layout(group_names: List[str]) -> Tuple[List[str], List[float]]:
    headers = ["STT", "MSSV", "Họ và tên"] + list(group_names) + ["Tổng (10)", "Chữ", "Thang 4", "Ghi chú"]
    fixed = {"STT": 30.0, "MSSV": 70.0, "Họ và tên": 150.0, "Tổng (10)": 55.0, "Chữ": 35.0, "Thang 4": 50.0, "Ghi chú": 70.0}
    used = sum(fixed.values())
    usable = PAGE_W - 2 * MARGIN
    group_w = max(36.0, min(70.0, (usable - used) / max(1, len(group_names))))
    widths = [
        fixed[h] if h in fixed and h not in group_names else group_w
        for h in headers
    ]
    scale = usable / sum(widths)
    return headers, [w * scale for w in widths]


def _fmt(value) -> str:
    return "" if value is None else format(value, "f")


def _draw_header(canvas: _Canvas, data: ReportData) -> float:
    canvas.text(MARGIN, 50, data.school_name, 10)
    canvas.text(MARGIN, 64, data.faculty_name, 10)
    right = PAGE_W - MARGIN - 140
    canvas.centered(right, 50, "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", 10)
    canvas.centered(right, 64, "Độc lập - Tự do - Hạnh phúc", 10)
    canvas.centered(PAGE_W / 2, 96, "BẢNG ĐIỂM HỌC PHẦN", 15)
    canvas.centered(
        PAGE_W / 2,
        114,
        f"Học phần: {data.course_name} ({data.course_code}) - Lớp: {data.section_code} - {data.semester}",
        10,
    )
    return 134.0


def _draw_signatures(canvas: _Canvas, y: float) -> None:
    box_w = (PAGE_W - 2 * MARGIN) / 3
    for index, title in enumerate(SIGNATURES):
        cx = MARGIN + box_w * index + box_w / 2
        canvas.centered(cx, y, title, 10)
        canvas.centered(cx, y + 13, "(Ký, ghi rõ họ tên)", 8)
        canvas.page.draw_rect(
            fitz.Rect(cx - box_w / 2 + 20, y + 20, cx + box_w / 2 - 20, y + 70), color=(0.3, 0.3, 0.3), width=0.5
        )


def build_pdf(data: ReportData) -> bytes:
    doc = fitz.open()
    canvas = _Canvas(doc, data.is_locked)
    headers, widths = _column_layout(data.group_names)
    canvas.new_page()
    y = _draw_header(canvas, data)

    def draw_table_header(y_pos: float) -> float:
        x = MARGIN
        for header, width in zip(headers, widths):
            rect = fitz.Rect(x, y_pos, x + width, y_pos + ROW_H)
            canvas.page.draw_rect(rect, color=(0, 0, 0), fill=(0.9, 0.93, 0.97), width=0.5)
            canvas.text(x + 2, y_pos + 12, header, 7.5)
            x += width
        return y_pos + ROW_H

    y = draw_table_header(y)
    bottom_limit = PAGE_H - MARGIN - 10
    for index, student in enumerate(data.rows, start=1):
        if y + ROW_H > bottom_limit:
            canvas.new_page()
            y = draw_table_header(MARGIN + 10)
        values = [str(index), student.user_code, student.full_name]
        values += [_fmt(student.group_scores.get(name)) for name in data.group_names]
        values += [_fmt(student.total_score), student.letter_grade, _fmt(student.scale4), student.remark]
        x = MARGIN
        fill = (0.97, 0.8, 0.68) if student.hurdle_failed else None
        for value, width in zip(values, widths):
            rect = fitz.Rect(x, y, x + width, y + ROW_H)
            canvas.page.draw_rect(rect, color=(0, 0, 0), fill=fill, width=0.5)
            canvas.text(x + 2, y + 12, value[:40], 7.5)
            x += width
        y += ROW_H

    if y + 100 > PAGE_H - MARGIN:
        canvas.new_page()
        y = MARGIN + 10
    canvas.text(PAGE_W - MARGIN - 220, y + 22, f"Ngày {data.generated_at:%d} tháng {data.generated_at:%m} năm {data.generated_at:%Y}", 9)
    _draw_signatures(canvas, y + 38)
    content = doc.tobytes()
    doc.close()
    return content
