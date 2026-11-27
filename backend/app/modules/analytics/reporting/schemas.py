# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Report data model (pure dataclasses used by builders) and API response schemas."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple
import uuid
from pydantic import BaseModel, Field

WATERMARK_TEXT = "BẢNG ĐIỂM DỰ KIẾN - CHƯA KHÓA"
SHEET_GRADES = "Diem_Tin_Chi_TT08"
SHEET_LO = "Ho_So_Nang_Luc_LO"
DEFAULT_SCHOOL_NAME = "TRƯỜNG ĐẠI HỌC ADLAS"
DEFAULT_FACULTY_NAME = "KHOA CÔNG NGHỆ THÔNG TIN"


class ExportFormat(str, Enum):
    EXCEL = "xlsx"
    CSV = "csv"
    PDF = "pdf"


@dataclass(frozen=True)
class StudentGradeRow:
    user_id: uuid.UUID
    user_code: str
    full_name: str
    email: str
    group_scores: Dict[str, Optional[Decimal]]
    total_score: Optional[Decimal]
    letter_grade: str
    scale4: Optional[Decimal]
    hurdle_failed: bool
    missing: bool
    lo_attainment: Dict[str, Optional[Decimal]] = field(default_factory=dict)

    @property
    def remark(self) -> str:
        if self.missing:
            return "Thiếu điểm"
        if self.hurdle_failed:
            return "Điểm liệt"
        return "Đạt" if self.letter_grade != "F" else "Không đạt"


@dataclass(frozen=True)
class LoRow:
    code: str
    description: str
    bloom_level: str
    criterion_titles: Tuple[str, ...]
    max_points: Decimal


@dataclass(frozen=True)
class ReportData:
    course_code: str
    section_code: str
    course_name: str
    semester: str
    credits: int
    is_locked: bool
    locked_at: Optional[datetime]
    group_names: List[str]
    rows: List[StudentGradeRow]
    lo_rows: List[LoRow]
    school_name: str = DEFAULT_SCHOOL_NAME
    faculty_name: str = DEFAULT_FACULTY_NAME
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def missing_count(self) -> int:
        return sum(1 for r in self.rows if r.missing)


class GradeRowPreview(BaseModel):
    user_code: str
    full_name: str
    group_scores: Dict[str, Optional[float]]
    total_score: Optional[float] = None
    letter_grade: str = ""
    scale4: Optional[float] = None
    hurdle_failed: bool = False
    missing: bool = False


class LoRowPreview(BaseModel):
    code: str
    description: str
    bloom_level: str
    criterion_titles: List[str]
    max_points: float


class ExportPreviewResponse(BaseModel):
    course_id: uuid.UUID
    course_code: str
    section_code: str
    course_name: str
    is_locked: bool
    locked_at: Optional[datetime] = None
    total_students: int
    missing_grade_students_count: int
    requires_confirmation: bool = Field(
        ..., description="True when a draft export would trigger the E-EXP-01 warning"
    )
    watermark_text: Optional[str] = None
    group_names: List[str]
    grade_rows: List[GradeRowPreview]
    lo_rows: List[LoRowPreview]
    filenames: Dict[str, str]


@dataclass(frozen=True)
class ExportResult:
    content: bytes
    media_type: str
    filename: str
