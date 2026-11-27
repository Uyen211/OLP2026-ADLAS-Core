# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""CSV builder: UTF-8 with BOM (utf-8-sig), formula-injection sanitized."""

import csv
import io
from typing import Any, List
from app.modules.analytics.reporting.sanitizer import sanitize_cell
from app.modules.analytics.reporting.schemas import ReportData


def _fmt(value: Any) -> Any:
    return "" if value is None else format(value, "f") if hasattr(value, "as_tuple") else value


def build_csv(data: ReportData) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\r\n")
    headers = (
        ["STT", "MSSV", "Ho va ten"]
        + list(data.group_names)
        + ["Tong ket (Thang 10)", "Diem chu", "Thang 4", "Ghi chu", "Trang thai so diem"]
    )
    writer.writerow([sanitize_cell(h) for h in headers])
    status = "CHINH_THUC" if data.is_locked else "DU_KIEN"
    for index, student in enumerate(data.rows, start=1):
        values: List[Any] = [index, student.user_code, student.full_name]
        values += [_fmt(student.group_scores.get(name)) for name in data.group_names]
        values += [
            _fmt(student.total_score),
            student.letter_grade,
            _fmt(student.scale4),
            student.remark,
            status,
        ]
        writer.writerow([sanitize_cell(v) for v in values])
    return buffer.getvalue().encode("utf-8-sig")
