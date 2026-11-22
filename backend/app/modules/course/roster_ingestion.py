# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Streaming Excel/CSV roster ingestion using openpyxl(read_only=True) (T2-P-M1-03)."""

import csv
from dataclasses import dataclass, field
import io
import re
from typing import Dict, Iterator, List, Optional, Sequence, Set, Tuple
import unicodedata
import openpyxl
from app.modules.course.enums import RosterRowStatus
from app.modules.course.exceptions import (
    RosterFileTooLargeException,
    RosterFormatException,
)

MAX_ROSTER_FILE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_ROSTER_ROWS = 2000
PREVIEW_LIMIT = 5
ERRORS_LIMIT = 50

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
_CODE_RE = re.compile(r"^[A-Za-z0-9_-]{2,50}$")

_HEADER_ALIASES: Dict[str, Set[str]] = {
    "user_code": {
        "mssv",
        "ma so sinh vien",
        "ma sinh vien",
        "ma sv",
        "student_code",
        "student code",
        "user_code",
        "user code",
    },
    "full_name": {
        "ho va ten",
        "ho ten",
        "full_name",
        "full name",
        "ten sinh vien",
        "name",
    },
    "email": {
        "email",
        "dia chi email",
        "email address",
        "e-mail",
    },
}

_REQUIRED_DISPLAY_NAMES: Dict[str, str] = {
    "user_code": "Ma so sinh vien",
    "full_name": "Ho va ten",
    "email": "Email",
}


@dataclass(frozen=True)
class ParsedRosterRow:
    """Single parsed and validated roster row."""

    row_number: int
    user_code: str
    full_name: str
    email: str
    status: RosterRowStatus
    reason: Optional[str] = None


@dataclass
class RosterParseResult:
    """Summary of a streaming roster parse operation."""

    total_rows: int = 0
    valid_count: int = 0
    duplicate_count: int = 0
    error_count: int = 0
    preview_rows: List[ParsedRosterRow] = field(default_factory=list)
    errors: List[Tuple[int, str]] = field(default_factory=list)
    valid_rows: List[ParsedRosterRow] = field(default_factory=list)


def normalize_header(raw: object) -> str:
    """Strip Vietnamese accents, lowercase, and collapse spaces/underscores."""
    if raw is None:
        return ""
    text = str(raw).strip()
    text = text.replace("đ", "d").replace("Đ", "D")
    nfd = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
    cleaned = re.sub(r"[\s_]+", " ", stripped.lower()).strip()
    return cleaned


def _resolve_column_map(headers: Sequence[object]) -> Dict[str, int]:
    col_map: Dict[str, int] = {}
    for idx, cell in enumerate(headers):
        norm = normalize_header(cell)
        if not norm:
            continue
        for canonical, aliases in _HEADER_ALIASES.items():
            if canonical not in col_map and (norm in aliases or norm.replace(" ", "_") in aliases):
                col_map[canonical] = idx
                break

    missing = [
        _REQUIRED_DISPLAY_NAMES[key]
        for key in ("user_code", "full_name", "email")
        if key not in col_map
    ]
    if missing:
        cols_str = ", ".join(f"[{name}]" for name in missing)
        raise RosterFormatException(
            detail=(
                f"Tep tai len thieu cot bat buoc {cols_str}. "
                "Vui long tai tep mau chuan ve doi chieu va thu lai."
            ),
            missing_columns=missing,
        )
    return col_map


def _iter_csv_rows(content: bytes) -> Iterator[List[object]]:
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            decoded = content.decode("latin-1")
        except Exception as exc:
            raise RosterFormatException(
                detail="Khong the doc dinh dang ky tu cua tep CSV."
            ) from exc

    reader = csv.reader(io.StringIO(decoded))
    for row in reader:
        yield list(row)


def _iter_xlsx_rows(content: bytes) -> Iterator[List[object]]:
    try:
        wb = openpyxl.load_workbook(
            filename=io.BytesIO(content),
            read_only=True,
            data_only=True,
        )
    except Exception as exc:
        raise RosterFormatException(
            detail="Tep Excel khong hop le hoac bi hong. Vui long tai len tep .xlsx chuan."
        ) from exc

    try:
        sheet = wb.active
        if sheet is None:
            raise RosterFormatException(detail="Tep Excel khong co trang tinh hop le.")
        for row in sheet.iter_rows(values_only=True):
            yield list(row)
    finally:
        wb.close()


def _cell_str(row: Sequence[object], idx: int) -> str:
    if idx >= len(row) or row[idx] is None:
        return ""
    value = row[idx]
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def parse_roster_bytes(
    filename: str,
    content: bytes,
    existing_course_emails: Optional[Set[str]] = None,
    existing_course_codes: Optional[Set[str]] = None,
    existing_email_to_code: Optional[Dict[str, Optional[str]]] = None,
) -> RosterParseResult:
    """
    Stream-parse an uploaded .xlsx or .csv roster file.
    Enforces 5MB file size limit, 2000 row limit, required headers, and duplicate detection.
    """
    if len(content) > MAX_ROSTER_FILE_BYTES:
        raise RosterFileTooLargeException(max_mb=5)

    lower_name = (filename or "").strip().lower()
    if lower_name.endswith(".xlsx"):
        row_iter = _iter_xlsx_rows(content)
    elif lower_name.endswith(".csv"):
        row_iter = _iter_csv_rows(content)
    else:
        raise RosterFormatException(
            detail="Dinh dang tep khong duoc ho tro. Chi chap nhan tep .xlsx hoac .csv."
        )

    header_row = next(row_iter, None)
    if header_row is None:
        raise RosterFormatException(
            detail="Tep tai len rong, khong co dong tieu de.",
            missing_columns=list(_REQUIRED_DISPLAY_NAMES.values()),
        )

    col_map = _resolve_column_map(header_row)

    course_emails = {e.lower() for e in (existing_course_emails or set())}
    course_codes = {c.upper() for c in (existing_course_codes or set())}
    email_to_code = {k.lower(): (v.upper() if v else None) for k, v in (existing_email_to_code or {}).items()}

    seen_file_emails: Set[str] = set()
    seen_file_codes: Set[str] = set()

    result = RosterParseResult()
    row_number = 1  # Row 1 is header

    for raw_row in row_iter:
        row_number += 1
        user_code = _cell_str(raw_row, col_map["user_code"]).upper()
        full_name = _cell_str(raw_row, col_map["full_name"])
        email = _cell_str(raw_row, col_map["email"]).lower()

        if not user_code and not full_name and not email:
            continue

        result.total_rows += 1
        if result.total_rows > MAX_ROSTER_ROWS:
            raise RosterFormatException(
                detail=f"Tep vuot qua gioi han toi da {MAX_ROSTER_ROWS} sinh vien moi lan nhap."
            )

        status = RosterRowStatus.VALID
        reason: Optional[str] = None

        if not user_code or not full_name or not email:
            status = RosterRowStatus.INVALID
            reason = "Thieu thong tin bat buoc (MSSV, Ho ten hoac Email)."
        elif not _CODE_RE.match(user_code):
            status = RosterRowStatus.INVALID
            reason = "Ma so sinh vien sai dinh dang."
        elif not _EMAIL_RE.match(email):
            status = RosterRowStatus.INVALID
            reason = "Dia chi email khong hop le."
        elif email in email_to_code and email_to_code[email] and email_to_code[email] != user_code:
            status = RosterRowStatus.INVALID
            reason = f"Email da gan voi MSSV khac ({email_to_code[email]})."
        elif email in course_emails or user_code in course_codes:
            status = RosterRowStatus.DUPLICATE_IN_COURSE
            reason = "Da co trong lop (He thong se tu dong bo qua khong them trung)."
        elif email in seen_file_emails or user_code in seen_file_codes:
            status = RosterRowStatus.DUPLICATE_IN_FILE
            reason = "Trung lap trong tep tai len."
        else:
            seen_file_emails.add(email)
            seen_file_codes.add(user_code)

        parsed = ParsedRosterRow(
            row_number=row_number,
            user_code=user_code,
            full_name=full_name,
            email=email,
            status=status,
            reason=reason,
        )

        if len(result.preview_rows) < PREVIEW_LIMIT:
            result.preview_rows.append(parsed)

        if status == RosterRowStatus.VALID:
            result.valid_count += 1
            result.valid_rows.append(parsed)
        elif status in (RosterRowStatus.DUPLICATE_IN_COURSE, RosterRowStatus.DUPLICATE_IN_FILE):
            result.duplicate_count += 1
        else:
            result.error_count += 1
            if len(result.errors) < ERRORS_LIMIT and reason:
                result.errors.append((row_number, reason))

    return result


def build_roster_template_xlsx() -> bytes:
    """Generate a standard .xlsx roster template for instructor download."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "DanhSachSinhVien"
    ws.append(["MSSV", "Ho va ten", "Email"])
    ws.append(["SV2026001", "Nguyen Van An", "an.nv@adlas.edu.vn"])
    ws.append(["SV2026002", "Tran Thi Binh", "binh.tt@adlas.edu.vn"])

    buffer = io.BytesIO()
    wb.save(buffer)
    wb.close()
    return buffer.getvalue()
