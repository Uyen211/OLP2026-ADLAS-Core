# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""Pure security and timing rules for Examination Context (BR-08, BR-AUTOSAVE-02, E-SEC-01..03)."""

from datetime import datetime, timedelta, timezone
import ipaddress
import secrets
from typing import Optional
from app.modules.examination.exceptions import (
    ExamClosedException,
    ExaminationValidationException,
    InvalidExamWindowException,
    IpNotAllowedException,
)

GRACE_PERIOD_MINUTES = 5
PASSCODE_LENGTH = 6
# Unambiguous uppercase alphanumeric characters (excludes 0/O and 1/I)
PASSCODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def validate_exam_window(
    available_from: datetime,
    available_until: datetime,
    time_limit_mins: int,
) -> None:
    """
    Enforce E-SEC-01:
    - time_limit_mins > 0
    - available_until > available_from
    - (available_until - available_from) >= time_limit_mins
    """
    if time_limit_mins <= 0:
        raise InvalidExamWindowException(
            "Thoi luong lam bai phai lon hon 0 phut."
        )

    start_utc = _ensure_utc(available_from)
    end_utc = _ensure_utc(available_until)
    if end_utc <= start_utc:
        raise InvalidExamWindowException(
            "Thoi diem dong de thi phai sau thoi diem mo de thi."
        )

    if (end_utc - start_utc) < timedelta(minutes=time_limit_mins):
        raise InvalidExamWindowException(
            "Khung gio mo de thi phai lon hon hoac bang thoi luong lam bai quy dinh."
        )


def compute_effective_deadline(
    started_at: datetime,
    time_limit_mins: int,
    available_until: datetime,
) -> datetime:
    """
    Enforce BR-08 (late entry time shrinkage):
        expires_at = min(started_at + time_limit_mins, available_until)
    Raises ExamClosedException (E-EXAM-CLOSED) if started_at >= available_until.
    """
    if time_limit_mins <= 0:
        raise InvalidExamWindowException("Thoi luong lam bai phai lon hon 0 phut.")

    start_utc = _ensure_utc(started_at)
    until_utc = _ensure_utc(available_until)

    if start_utc >= until_utc:
        raise ExamClosedException("Ky thi da dong, khong the bat dau luot thi moi.")

    nominal_deadline = start_utc + timedelta(minutes=time_limit_mins)
    return min(nominal_deadline, until_utc)


def is_within_grace_period(
    now: datetime,
    expires_at: datetime,
    grace_minutes: int = GRACE_PERIOD_MINUTES,
) -> bool:
    """
    Check BR-AUTOSAVE-02: returns True if `now` is within `expires_at + grace_minutes`.
    """
    now_utc = _ensure_utc(now)
    exp_utc = _ensure_utc(expires_at)
    return now_utc <= exp_utc + timedelta(minutes=max(0, grace_minutes))


def assert_within_grace_period(
    now: datetime,
    expires_at: datetime,
    grace_minutes: int = GRACE_PERIOD_MINUTES,
) -> None:
    """Raise ExamClosedException (E-EXAM-CLOSED) if `now` exceeds the 5-minute grace window."""
    if not is_within_grace_period(now, expires_at, grace_minutes=grace_minutes):
        raise ExamClosedException(
            "Da qua thoi han nop bai va thoi gian an han dong bo 5 phut."
        )


def validate_cidr_expression(ip_filter_range: Optional[str]) -> Optional[str]:
    """Validate comma/semicolon-separated CIDR or IP allowlist expression."""
    if ip_filter_range is None:
        return None
    cleaned = ip_filter_range.strip()
    if not cleaned:
        return None

    parts = [p.strip() for p in cleaned.replace(";", ",").split(",") if p.strip()]
    normalized = []
    for part in parts:
        try:
            network = ipaddress.ip_network(part, strict=False)
            normalized.append(str(network))
        except ValueError as exc:
            raise ExaminationValidationException(
                detail=f"Dai IP/CIDR khong hop le: '{part}'.",
                field="ip_filter_range",
            ) from exc
    return ", ".join(normalized)


def validate_ip_in_cidr(
    client_ip: Optional[str],
    ip_filter_range: Optional[str],
) -> bool:
    """
    Check whether `client_ip` belongs to at least one CIDR/IP entry in `ip_filter_range`.
    Returns True if `ip_filter_range` is None or empty (no IP restriction configured).
    """
    if ip_filter_range is None or not ip_filter_range.strip():
        return True
    if not client_ip or not client_ip.strip():
        return False

    try:
        addr = ipaddress.ip_address(client_ip.strip())
    except ValueError:
        return False

    parts = [p.strip() for p in ip_filter_range.replace(";", ",").split(",") if p.strip()]
    for part in parts:
        try:
            network = ipaddress.ip_network(part, strict=False)
            if addr.version == network.version and addr in network:
                return True
        except ValueError:
            continue
    return False


def assert_ip_allowed(
    client_ip: Optional[str],
    ip_filter_range: Optional[str],
) -> None:
    """Raise IpNotAllowedException (E-SEC-03) if `client_ip` is outside `ip_filter_range`."""
    if not validate_ip_in_cidr(client_ip, ip_filter_range):
        raise IpNotAllowedException()


def generate_passcode(length: int = PASSCODE_LENGTH) -> str:
    """Generate a cryptographically secure 6-character exam passcode via `secrets.choice`."""
    if length < 4:
        raise ValueError("Passcode length must be at least 4 characters.")
    return "".join(secrets.choice(PASSCODE_ALPHABET) for _ in range(length))
