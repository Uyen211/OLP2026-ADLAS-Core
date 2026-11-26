# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Unit tests for Gradebook TT08 calculation, ROUND_HALF_UP, Drop Lowest, and Hurdle (T2-P-M5-02)."""

from decimal import Decimal
import pytest
from app.modules.gradebook.calculation import (
    GroupCalcSpec,
    build_grade_distribution,
    compute_group_average,
    compute_student_final_grade,
    convert_to_letter_and_gpa,
    round_tt08,
    validate_score_range,
)
from app.modules.gradebook.exceptions import GradeScoreRangeException


def test_round_tt08_half_up_br13():
    assert round_tt08(Decimal("6.45")) == Decimal("6.5")
    assert round_tt08(Decimal("6.44")) == Decimal("6.4")
    assert round_tt08(Decimal("7.45")) == Decimal("7.5")
    assert round_tt08(Decimal("8.45")) == Decimal("8.5")


def test_convert_to_letter_and_gpa_boundaries():
    assert convert_to_letter_and_gpa(Decimal("8.5")) == ("A", Decimal("4.0"), True)
    assert convert_to_letter_and_gpa(Decimal("8.1")) == ("B+", Decimal("3.5"), True)
    assert convert_to_letter_and_gpa(Decimal("7.0")) == ("B", Decimal("3.0"), True)
    assert convert_to_letter_and_gpa(Decimal("6.5")) == ("C+", Decimal("2.5"), True)
    assert convert_to_letter_and_gpa(Decimal("5.5")) == ("C", Decimal("2.0"), True)
    assert convert_to_letter_and_gpa(Decimal("5.0")) == ("D+", Decimal("1.5"), True)
    assert convert_to_letter_and_gpa(Decimal("4.0")) == ("D", Decimal("1.0"), True)
    assert convert_to_letter_and_gpa(Decimal("3.9")) == ("F", Decimal("0.0"), False)


def test_validate_score_range_e_gb_02():
    assert validate_score_range(Decimal("0.0")) == Decimal("0.0")
    assert validate_score_range(Decimal("10.0")) == Decimal("10.0")
    with pytest.raises(GradeScoreRangeException):
        validate_score_range(Decimal("-0.1"))
    with pytest.raises(GradeScoreRangeException):
        validate_score_range(Decimal("10.01"))


def test_drop_lowest_only_when_gt_one_br_gb_03():
    # Only 1 score -> never drop
    assert compute_group_average([Decimal("5.0")], drop_lowest_count=1) == Decimal("5.00")
    # 3 scores -> drop lowest (2.0), average of 8.0 and 10.0 = 9.00
    assert compute_group_average(
        [Decimal("2.0"), Decimal("8.0"), Decimal("10.0")], drop_lowest_count=1
    ) == Decimal("9.00")


def test_standard_passing_student_ac01():
    groups = [
        GroupCalcSpec("g1", 10, 0, False, Decimal("4.0"), ["c1"]),
        GroupCalcSpec("g2", 30, 0, False, Decimal("4.0"), ["c2"]),
        GroupCalcSpec("g3", 20, 0, False, Decimal("4.0"), ["c3"]),
        GroupCalcSpec("g4", 40, 0, True, Decimal("4.0"), ["c4"]),
    ]
    res = compute_student_final_grade(
        groups,
        {"c1": Decimal("9.0"), "c2": Decimal("8.0"), "c3": Decimal("8.0"), "c4": Decimal("8.0")},
    )
    assert res.final_score_10 == Decimal("8.1")
    assert res.letter_grade == "B+"
    assert res.score_4 == Decimal("3.5")
    assert res.is_passed is True
    assert res.hurdle_failed is False
    assert res.is_provisional is False


def test_hurdle_forces_grade_f_br10_ac02():
    groups = [
        GroupCalcSpec("g1", 10, 0, False, Decimal("4.0"), ["c1"]),
        GroupCalcSpec("g2", 30, 0, False, Decimal("4.0"), ["c2"]),
        GroupCalcSpec("g3", 20, 0, False, Decimal("4.0"), ["c3"]),
        GroupCalcSpec("g4", 40, 0, True, Decimal("4.0"), ["c4"]),
    ]
    res = compute_student_final_grade(
        groups,
        {"c1": Decimal("10.0"), "c2": Decimal("10.0"), "c3": Decimal("9.0"), "c4": Decimal("3.5")},
    )
    # Weighted sum = 1.0 + 3.0 + 1.8 + 1.4 = 7.2, but Hurdle (< 4.0) forces F / 0.0 / Failed
    assert res.final_score_10 == Decimal("7.2")
    assert res.hurdle_failed is True
    assert res.letter_grade == "F"
    assert res.score_4 == Decimal("0.0")
    assert res.is_passed is False


def test_missing_column_marks_provisional_e_calc_01():
    groups = [
        GroupCalcSpec("g1", 50, 0, False, Decimal("4.0"), ["c1"]),
        GroupCalcSpec("g2", 50, 0, False, Decimal("4.0"), ["c2"]),
    ]
    res = compute_student_final_grade(groups, {"c1": Decimal("8.0"), "c2": None})
    assert res.is_provisional is True
    assert res.missing_columns_count == 1
    assert res.final_score_10 == Decimal("4.0")


def test_grade_distribution_buckets():
    buckets = build_grade_distribution(["A", "B+", "B", "C", "F", None])
    by_label = {b.label: b for b in buckets}
    assert by_label["A"].count == 1
    assert by_label["B / B+"].count == 2
    assert by_label["F"].count == 1
    assert by_label["A"].percentage == 20.0
