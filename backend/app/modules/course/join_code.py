# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""CSPRNG 6-character Join Code generator and validator (T2-P-M1-03)."""

import secrets

# 31 unambiguous uppercase characters (excludes 0, O, 1, I, L)
JOIN_CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
JOIN_CODE_LENGTH = 6


def generate_join_code(length: int = JOIN_CODE_LENGTH) -> str:
    """Generate a cryptographically secure uppercase join code."""
    return "".join(secrets.choice(JOIN_CODE_ALPHABET) for _ in range(length))


def normalize_join_code(raw: str) -> str:
    """Trim whitespace and convert join code to uppercase."""
    return raw.strip().upper()


def is_valid_join_code(code: str, length: int = JOIN_CODE_LENGTH) -> bool:
    """Check whether `code` matches the expected length and unambiguous alphabet."""
    normalized = normalize_join_code(code)
    return len(normalized) == length and all(ch in JOIN_CODE_ALPHABET for ch in normalized)
