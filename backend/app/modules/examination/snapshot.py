# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Pure snapshot selection and cryptographic shuffling engine (BR-EXAM-01, BR-EXAM-02)."""

from copy import deepcopy
from dataclasses import dataclass
import random
import secrets
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, TypeVar
import uuid
from app.modules.examination.exceptions import InsufficientQuestionsException
from app.modules.examination.models import Question, QuizAttemptQuestion, QuizQuestion

T = TypeVar("T")

_SYSTEM_RNG = secrets.SystemRandom()


@dataclass(frozen=True)
class MatrixRule:
    """Single row of a quiz generation matrix."""

    bank_id: uuid.UUID
    count: int
    bloom_level: Optional[str] = None
    lo_id: Optional[uuid.UUID] = None


@dataclass(frozen=True)
class DrawRule:
    """Folder and difficulty based rule for dynamic exam draw."""

    count: int
    folder_id: Optional[uuid.UUID] = None
    bank_id: Optional[uuid.UUID] = None
    difficulty: Optional[str] = None


def select_questions_by_draw_rules(
    draw_rules: Sequence[DrawRule],
    candidate_pools: Sequence[Sequence[T]],
    rng: Optional[random.Random] = None,
) -> List[T]:
    """
    Randomly draw questions matching each (draw_rule, candidate_pool) pair without duplicates.
    Raises InsufficientQuestionsException (E-EXAM-03) if any rule lacks enough active questions.
    """
    if len(draw_rules) != len(candidate_pools):
        raise ValueError("draw_rules and candidate_pools must have equal length.")

    generator = rng or _SYSTEM_RNG
    selected: List[T] = []
    seen_ids: Set[Any] = set()

    for rule, pool in zip(draw_rules, candidate_pools):
        if rule.count <= 0:
            continue
        available = []
        for item in pool:
            item_id = getattr(item, "id", None)
            if item_id is not None and item_id in seen_ids:
                continue
            available.append(item)

        if len(available) < rule.count:
            raise InsufficientQuestionsException(
                detail=(
                    f"Ngan hang/thu muc khong du cau hoi (can {rule.count}, "
                    f"chi co {len(available)} cau hop le)."
                ),
                requested=rule.count,
                available=len(available),
            )

        picked = generator.sample(available, rule.count)
        for item in picked:
            item_id = getattr(item, "id", None)
            if item_id is not None:
                seen_ids.add(item_id)
            selected.append(item)

    return selected


def select_questions_by_matrix(
    matrix_rules: Sequence[MatrixRule],
    candidate_pools: Sequence[Sequence[T]],
    rng: Optional[random.Random] = None,
) -> List[T]:
    """
    Randomly draw questions matching each `(rule, candidate_pool)` pair without duplicates.
    Raises InsufficientQuestionsException (E-EXAM-03) if any cell lacks enough questions.
    """
    if len(matrix_rules) != len(candidate_pools):
        raise ValueError("matrix_rules and candidate_pools must have equal length.")

    generator = rng or _SYSTEM_RNG
    selected: List[T] = []
    seen_ids: Set[Any] = set()

    for rule, pool in zip(matrix_rules, candidate_pools):
        if rule.count <= 0:
            continue
        available = []
        for item in pool:
            item_id = getattr(item, "id", None)
            if item_id is not None and item_id in seen_ids:
                continue
            available.append(item)

        if len(available) < rule.count:
            raise InsufficientQuestionsException(
                detail=(
                    f"Ngan hang khong du cau hoi (can {rule.count}, "
                    f"chi co {len(available)} cau hop le)."
                ),
                requested=rule.count,
                available=len(available),
            )

        picked = generator.sample(available, rule.count)
        for item in picked:
            item_id = getattr(item, "id", None)
            if item_id is not None:
                seen_ids.add(item_id)
            selected.append(item)

    return selected


def normalize_options_snapshot(
    options: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Deep-copy question options ensuring every entry has stable `id`, `key`, `text`, `is_correct`."""
    normalized: List[Dict[str, Any]] = []
    for idx, raw in enumerate(options):
        opt = deepcopy(dict(raw))
        default_key = chr(ord("A") + idx)
        key = str(opt.get("key") or default_key).strip().upper()
        opt_id = str(opt.get("id") or key)
        normalized.append(
            {
                "id": opt_id,
                "key": key,
                "text": str(opt.get("text", "")),
                "is_correct": bool(opt.get("is_correct", False)),
            }
        )
    return normalized


def build_quiz_question_snapshots(
    selected_questions: Sequence[Question],
    quiz_id: uuid.UUID,
) -> List[QuizQuestion]:
    """
    Build Tier-1 immutable quiz-level snapshots (`examination.quiz_questions`, BR-EXAM-01).
    Subsequent edits or soft-deletes to `examination.questions` do not alter these rows.
    """
    snapshots: List[QuizQuestion] = []
    for order_idx, q in enumerate(selected_questions, start=1):
        snapshots.append(
            QuizQuestion(
                quiz_id=quiz_id,
                question_id=q.id,
                lo_id=q.lo_id,
                question_order=order_idx,
                question_type=q.question_type,
                question_text_snapshot=q.question_text,
                options_snapshot=normalize_options_snapshot(q.options or []),
                explanation_snapshot=q.explanation,
                default_points=q.default_points,
            )
        )
    return snapshots


def shuffle_options_snapshot(
    options_snapshot: Sequence[Mapping[str, Any]],
    shuffle_options: bool = True,
    rng: Optional[random.Random] = None,
) -> List[Dict[str, Any]]:
    """
    Deep-copy and optionally shuffle options using `secrets.SystemRandom` (BR-EXAM-02),
    reassigning display keys A, B, C, D... while keeping each option's stable `id`.
    """
    generator = rng or _SYSTEM_RNG
    items = normalize_options_snapshot(options_snapshot)
    if shuffle_options and len(items) > 1:
        generator.shuffle(items)

    for idx, item in enumerate(items):
        item["key"] = chr(ord("A") + idx)
    return items


def build_attempt_question_snapshots(
    quiz_questions: Sequence[QuizQuestion],
    submission_id: uuid.UUID,
    shuffle_questions: bool = True,
    shuffle_options: bool = True,
    rng: Optional[random.Random] = None,
) -> List[QuizAttemptQuestion]:
    """
    Build Tier-2 per-student shuffled snapshots (`examination.quiz_attempt_questions`, BR-EXAM-02)
    derived strictly from Tier-1 `quiz_questions`.
    """
    generator = rng or _SYSTEM_RNG
    ordered = list(quiz_questions)
    if shuffle_questions and len(ordered) > 1:
        generator.shuffle(ordered)

    attempt_rows: List[QuizAttemptQuestion] = []
    for order_idx, qq in enumerate(ordered, start=1):
        shuffled_opts = shuffle_options_snapshot(
            qq.options_snapshot or [],
            shuffle_options=shuffle_options,
            rng=generator,
        )
        attempt_rows.append(
            QuizAttemptQuestion(
                submission_id=submission_id,
                quiz_question_id=qq.id,
                question_id=qq.question_id,
                lo_id=qq.lo_id,
                question_order=order_idx,
                question_type=qq.question_type,
                question_text=qq.question_text_snapshot,
                options_snapshot=shuffled_opts,
                explanation_snapshot=qq.explanation_snapshot,
                default_points=qq.default_points,
            )
        )
    return attempt_rows


def sanitize_options_for_student(
    options_snapshot: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Remove `is_correct` flags from options before sending question payloads to students."""
    sanitized: List[Dict[str, Any]] = []
    for opt in options_snapshot:
        sanitized.append(
            {
                "id": str(opt.get("id") or opt.get("key") or ""),
                "key": str(opt.get("key") or ""),
                "text": str(opt.get("text") or ""),
            }
        )
    return sanitized
