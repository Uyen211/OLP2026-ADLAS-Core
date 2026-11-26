# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Formula/DDE injection sanitizer, score rounding and TT08 grade conversion (BR-EXP-03)."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
import re
from typing import Any, Optional
import unicodedata

# Characters that make spreadsheet software interpret a cell as a formula / DDE command.
DANGEROUS_PREFIXES = ("=", "+", "-", "@", "|", "\t", "\r")

ONE_DECIMAL = Decimal("0.1")

# TT08/2021/TT-BGDDT: (minimum score on scale 10, letter grade, scale 4)
GRADE_TABLE = (
    (Decimal("8.5"), "A", Decimal("4.0")),
    (Decimal("8.0"), "B+", Decimal("3.5")),
    (Decimal("7.0"), "B", Decimal("3.0")),
    (Decimal("6.5"), "C+", Decimal("2.5")),
    (Decimal("5.5"), "C", Decimal("2.0")),
    (Decimal("5.0"), "D+", Decimal("1.5")),
    (Decimal("4.0"), "D", Decimal("1.0")),
)
FAIL_LETTER = "F"
FAIL_SCALE4 = Decimal("0.0")


def sanitize_cell(value: Any) -> Any:
    """Neutralize formula injection in text. Numbers/None pass through unchanged (None -> '')."""
    if value is None:
        return ""
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        return value
    text = str(value)
    if text.startswith(DANGEROUS_PREFIXES):
        return "'" + text
    return text


def to_decimal(value: Any) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def round_score(value: Any) -> Optional[Decimal]:
    """Round to exactly 1 decimal place with ROUND_HALF_UP (never float rounding)."""
    if value is None:
        return None
    return to_decimal(value).quantize(ONE_DECIMAL, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class GradeConversion:
    score10: Optional[Decimal]
    letter: str
    scale4: Optional[Decimal]
    passed: bool


def convert_grade(score10: Any, hurdle_failed: bool = False) -> GradeConversion:
    """Scale 10 -> letter grade -> scale 4. A failed Hurdle forces F / 0.0."""
    rounded = round_score(score10)
    if rounded is None:
        return GradeConversion(None, "", None, False)
    if hurdle_failed:
        return GradeConversion(rounded, FAIL_LETTER, FAIL_SCALE4, False)
    for minimum, letter, scale4 in GRADE_TABLE:
        if rounded >= minimum:
            return GradeConversion(rounded, letter, scale4, True)
    return GradeConversion(rounded, FAIL_LETTER, FAIL_SCALE4, False)


def ascii_slug(value: str, fallback: str = "NA") -> str:
    """Strip accents and unsafe characters so the result is filename-safe ASCII."""
    folded = unicodedata.normalize("NFKD", (value or "").replace("Đ", "D").replace("đ", "d"))
    ascii_text = folded.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9]+", "", ascii_text)
    return slug or fallback


def build_filename(class_code: str, course_code: str, is_locked: bool, extension: str) -> str:
    """`{MaLop}_{MaMon}_BangDiem_ChinhThuc.{ext}` or `..._DU_KIEN.{ext}`."""
    suffix = "ChinhThuc" if is_locked else "DU_KIEN"
    ext = ascii_slug(extension, "bin").lower()
    return f"{ascii_slug(class_code)}_{ascii_slug(course_code)}_BangDiem_{suffix}.{ext}"
