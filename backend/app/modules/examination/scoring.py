# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Pure objective scoring engine for Examination Context (BR-13, BR-EXAM-MULTI)."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable, Mapping, Sequence, Set, Union
from app.modules.examination.enums import QuestionType

NumberLike = Union[Decimal, int, float, str]


def _to_decimal(value: NumberLike) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _normalize_keys(keys: Union[str, Iterable[str], None]) -> Set[str]:
    if keys is None:
        return set()
    if isinstance(keys, str):
        cleaned = keys.strip()
        return {cleaned} if cleaned else set()
    return {str(k).strip() for k in keys if str(k).strip()}


def score_single_choice(
    selected_keys: Union[str, Iterable[str], None],
    correct_keys: Iterable[str],
    points: NumberLike,
) -> Decimal:
    """
    Score a single-choice (MULTIPLE_CHOICE) question.
    Awards full `points` if and only if the student selected the single exact correct option.
    """
    pts = _to_decimal(points)
    if pts <= Decimal("0"):
        return Decimal("0")

    selected = _normalize_keys(selected_keys)
    correct = _normalize_keys(correct_keys)
    if not correct or len(selected) != 1:
        return Decimal("0")

    return pts if selected == correct else Decimal("0")


def score_multi_select(
    selected_keys: Union[str, Iterable[str], None],
    correct_keys: Iterable[str],
    all_option_keys: Iterable[str],
    points: NumberLike,
) -> Decimal:
    """
    Score a multi-select (MULTI_SELECT) question with anti-guessing penalty (BR-EXAM-MULTI).

    Formula:
        score_i = max(0, P_i * (r / k - w / m))
    where:
        k = |C| (number of correct options)
        m = |W| (number of wrong options)
        r = |S ∩ C| (correct options selected)
        w = |S ∩ W| (wrong options selected)

    Selecting every option yields r = k and w = m, resulting in exactly 0 points.
    """
    pts = _to_decimal(points)
    if pts <= Decimal("0"):
        return Decimal("0")

    all_opts = _normalize_keys(all_option_keys)
    correct = _normalize_keys(correct_keys) & all_opts
    wrong = all_opts - correct
    selected = _normalize_keys(selected_keys) & all_opts

    k = len(correct)
    m = len(wrong)
    if k == 0 or not selected:
        return Decimal("0")

    r = len(selected & correct)
    w = len(selected & wrong)

    if m == 0:
        ratio = Decimal(r) / Decimal(k)
    else:
        ratio = (Decimal(r) / Decimal(k)) - (Decimal(w) / Decimal(m))

    if ratio <= Decimal("0"):
        return Decimal("0")

    return pts * ratio


def score_question_from_snapshot(
    question_type: str,
    options_snapshot: Sequence[Mapping[str, Any]],
    selected_keys: Union[str, Iterable[str], None],
    default_points: NumberLike,
) -> Decimal:
    """Score a single question directly from its frozen `options_snapshot` JSONB payload."""
    all_keys = []
    correct_keys = []
    for opt in options_snapshot:
        key = str(opt.get("key") or opt.get("id") or "").strip()
        if not key:
            continue
        all_keys.append(key)
        if bool(opt.get("is_correct")):
            correct_keys.append(key)

    if question_type == QuestionType.MULTI_SELECT.value:
        return score_multi_select(
            selected_keys=selected_keys,
            correct_keys=correct_keys,
            all_option_keys=all_keys,
            points=default_points,
        )

    return score_single_choice(
        selected_keys=selected_keys,
        correct_keys=correct_keys,
        points=default_points,
    )


def compute_quiz_score_scale_10(
    earned_points: Sequence[NumberLike],
    max_points: Sequence[NumberLike],
) -> Decimal:
    """
    Convert raw earned points to the standard 10.0 scale rounded to 1 decimal place
    using Decimal ROUND_HALF_UP (BR-13).
    """
    total_max = sum((_to_decimal(p) for p in max_points), Decimal("0"))
    if total_max <= Decimal("0"):
        return Decimal("0.0")

    total_earned = sum((_to_decimal(e) for e in earned_points), Decimal("0"))
    if total_earned <= Decimal("0"):
        return Decimal("0.0")

    scaled = (total_earned / total_max) * Decimal("10")
    if scaled > Decimal("10"):
        scaled = Decimal("10")

    return scaled.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
