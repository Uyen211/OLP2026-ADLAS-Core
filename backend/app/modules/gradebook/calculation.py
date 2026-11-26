# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""
Pure-Python academic grading calculation engine using fixed-point Decimal arithmetic.
Implements Circular 08/2021/TT-BGDDT (BR-13), Hurdle Requirement (BR-10), and Drop Lowest (BR-GB-03).
"""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Sequence, Tuple
from app.modules.gradebook.enums import LetterGrade
from app.modules.gradebook.exceptions import GradeScoreRangeException
from app.modules.gradebook.schemas import GradeDistributionBucket

ZERO = Decimal("0.0")
TEN = Decimal("10.0")
ONE_DECIMAL = Decimal("0.1")
TWO_DECIMALS = Decimal("0.01")


def validate_score_range(score: Decimal) -> Decimal:
    """Enforce Invariant-Score-Range: 0.00 <= score <= 10.00 (E-GB-02)."""
    dec = Decimal(str(score))
    if dec < Decimal("0.00") or dec > Decimal("10.00"):
        raise GradeScoreRangeException(score)
    return dec


def round_tt08(value: Decimal) -> Decimal:
    """Round score to 1 decimal place using standard ROUND_HALF_UP (BR-13)."""
    return Decimal(str(value)).quantize(ONE_DECIMAL, rounding=ROUND_HALF_UP)


def convert_to_letter_and_gpa(score_10: Decimal) -> Tuple[str, Decimal, bool]:
    """
    Convert rounded 10-point score to Circular 08/2021 letter grade, 4-point GPA, and pass flag.
    Returns (letter_grade, score_4, is_passed).
    """
    s = round_tt08(score_10)
    if s >= Decimal("8.5"):
        return LetterGrade.A.value, Decimal("4.0"), True
    if s >= Decimal("8.0"):
        return LetterGrade.B_PLUS.value, Decimal("3.5"), True
    if s >= Decimal("7.0"):
        return LetterGrade.B.value, Decimal("3.0"), True
    if s >= Decimal("6.5"):
        return LetterGrade.C_PLUS.value, Decimal("2.5"), True
    if s >= Decimal("5.5"):
        return LetterGrade.C.value, Decimal("2.0"), True
    if s >= Decimal("5.0"):
        return LetterGrade.D_PLUS.value, Decimal("1.5"), True
    if s >= Decimal("4.0"):
        return LetterGrade.D.value, Decimal("1.0"), True
    return LetterGrade.F.value, Decimal("0.0"), False


def compute_group_average(
    scores: Sequence[Decimal],
    drop_lowest_count: int = 0,
) -> Optional[Decimal]:
    """
    Compute arithmetic average for a grade group.
    Enforces BR-GB-03: Drop Lowest only applies when there is more than 1 score in the group,
    and always retains at least 1 score.
    """
    if not scores:
        return None
    normalized = sorted(Decimal(str(s)) for s in scores)
    drop_n = int(drop_lowest_count or 0)
    effective_drop = 0
    if drop_n > 0 and len(normalized) > 1:
        effective_drop = min(drop_n, len(normalized) - 1)
    kept = normalized[effective_drop:]
    total = sum(kept, Decimal("0"))
    avg = total / Decimal(len(kept))
    return avg.quantize(TWO_DECIMALS, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class GroupCalcSpec:
    """Calculation parameters for one grade category."""

    group_id: str
    weight_percent: int
    drop_lowest_count: int
    is_hurdle: bool
    hurdle_min_score: Decimal
    column_ids: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class StudentFinalGradeResult:
    """Result of TT08 + Hurdle calculation for a single student."""

    group_averages: Dict[str, Optional[Decimal]]
    final_score_10: Optional[Decimal]
    letter_grade: Optional[str]
    score_4: Optional[Decimal]
    is_passed: Optional[bool]
    hurdle_failed: bool
    is_provisional: bool
    missing_columns_count: int


def compute_student_final_grade(
    groups: Sequence[GroupCalcSpec],
    scores_by_column: Dict[str, Optional[Decimal]],
) -> StudentFinalGradeResult:
    """
    Compute weighted final grade (scale 10), letter grade, 4-point GPA, and Hurdle status.
    - If any column has no score -> marks is_provisional=True (E-CALC-01) and counts missing columns.
    - If any hurdle group has average < hurdle_min_score -> forces F, 0.0, is_passed=False (BR-10).
    """
    group_averages: Dict[str, Optional[Decimal]] = {}
    weighted_sum = Decimal("0")
    present_weight = 0
    missing_count = 0
    hurdle_failed = False

    for grp in groups:
        grp_scores: List[Decimal] = []
        for col_id in grp.column_ids:
            val = scores_by_column.get(col_id)
            if val is None:
                missing_count += 1
            else:
                grp_scores.append(Decimal(str(val)))

        avg = compute_group_average(grp_scores, grp.drop_lowest_count)
        group_averages[grp.group_id] = round_tt08(avg) if avg is not None else None

        if avg is not None:
            weighted_sum += avg * (Decimal(grp.weight_percent) / Decimal("100"))
            present_weight += grp.weight_percent
            if grp.is_hurdle and avg < Decimal(str(grp.hurdle_min_score)):
                hurdle_failed = True

    if present_weight == 0:
        return StudentFinalGradeResult(
            group_averages=group_averages,
            final_score_10=None,
            letter_grade=None,
            score_4=None,
            is_passed=None,
            hurdle_failed=False,
            is_provisional=missing_count > 0,
            missing_columns_count=missing_count,
        )

    final_10 = round_tt08(weighted_sum)
    if hurdle_failed:
        letter = LetterGrade.F.value
        score_4 = Decimal("0.0")
        is_passed = False
    else:
        letter, score_4, is_passed = convert_to_letter_and_gpa(final_10)

    return StudentFinalGradeResult(
        group_averages=group_averages,
        final_score_10=final_10,
        letter_grade=letter,
        score_4=score_4,
        is_passed=is_passed,
        hurdle_failed=hurdle_failed,
        is_provisional=missing_count > 0,
        missing_columns_count=missing_count,
    )


def build_grade_distribution(letter_grades: Sequence[Optional[str]]) -> List[GradeDistributionBucket]:
    """Aggregate class letter grades into 5 standard distribution buckets (Subflow A-1 of M5-02)."""
    valid = [lg for lg in letter_grades if lg is not None]
    total = len(valid)
    buckets_spec = [
        ("A", "8.5 - 10.0", {"A"}),
        ("B / B+", "7.0 - 8.4", {"B+", "B"}),
        ("C / C+", "5.5 - 6.9", {"C+", "C"}),
        ("D / D+", "4.0 - 5.4", {"D+", "D"}),
        ("F", "< 4.0 / Diem liet", {"F"}),
    ]
    result: List[GradeDistributionBucket] = []
    for label, hint, letters in buckets_spec:
        cnt = sum(1 for lg in valid if lg in letters)
        pct = round((cnt / total) * 100.0, 1) if total > 0 else 0.0
        result.append(
            GradeDistributionBucket(
                label=label,
                range_hint=hint,
                count=cnt,
                percentage=pct,
            )
        )
    return result
