# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

"""RFC 6238 Time-Based One-Time Password (TOTP) implementation using stdlib only."""

import base64
import hashlib
import hmac
import secrets
import struct
import time
from typing import Optional
from urllib.parse import quote

DEFAULT_TIME_STEP = 30
DEFAULT_DIGITS = 6
DEFAULT_WINDOW = 1

_HASH_ALGORITHMS = {
    "sha1": hashlib.sha1,
    "sha256": hashlib.sha256,
    "sha512": hashlib.sha512,
}


def generate_secret(num_bytes: int = 20) -> str:
    """Generate a cryptographically random Base32-encoded TOTP secret without padding."""
    raw = secrets.token_bytes(num_bytes)
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def decode_base32_secret(secret: str) -> bytes:
    """Decode a Base32 secret string, tolerating spaces and omitted padding."""
    cleaned = secret.strip().replace(" ", "").upper()
    padding = (-len(cleaned)) % 8
    return base64.b32decode(cleaned + ("=" * padding), casefold=True)


def generate_hotp_from_bytes(
    key: bytes,
    counter: int,
    digits: int = DEFAULT_DIGITS,
    digest: str = "sha1",
) -> str:
    """Compute an RFC 4226 HOTP value from raw secret bytes and an 8-byte counter."""
    algo = _HASH_ALGORITHMS.get(digest.lower())
    if algo is None:
        raise ValueError(f"Unsupported TOTP hash algorithm: {digest}")

    counter_bytes = struct.pack(">Q", counter)
    mac = hmac.new(key, counter_bytes, algo).digest()
    offset = mac[-1] & 0x0F
    binary = struct.unpack(">I", mac[offset : offset + 4])[0] & 0x7FFFFFFF
    otp = binary % (10**digits)
    return str(otp).zfill(digits)


def generate_totp_from_bytes(
    key: bytes,
    timestamp: Optional[int] = None,
    time_step: int = DEFAULT_TIME_STEP,
    digits: int = DEFAULT_DIGITS,
    digest: str = "sha1",
) -> str:
    """Compute an RFC 6238 TOTP code from raw secret bytes."""
    now = int(time.time()) if timestamp is None else int(timestamp)
    counter = now // time_step
    return generate_hotp_from_bytes(key=key, counter=counter, digits=digits, digest=digest)


def generate_totp(
    secret: str,
    timestamp: Optional[int] = None,
    time_step: int = DEFAULT_TIME_STEP,
    digits: int = DEFAULT_DIGITS,
    digest: str = "sha1",
) -> str:
    """Compute an RFC 6238 TOTP code from a Base32-encoded secret."""
    key = decode_base32_secret(secret)
    return generate_totp_from_bytes(
        key=key,
        timestamp=timestamp,
        time_step=time_step,
        digits=digits,
        digest=digest,
    )


def verify_totp(
    secret: str,
    code: str,
    timestamp: Optional[int] = None,
    window: int = DEFAULT_WINDOW,
    time_step: int = DEFAULT_TIME_STEP,
    digits: int = DEFAULT_DIGITS,
    digest: str = "sha1",
) -> bool:
    """
    Verify a TOTP code allowing +/- `window` time steps (default +/- 30s)
    using constant-time comparison (`hmac.compare_digest`).
    """
    normalized = code.strip()
    if len(normalized) != digits or not normalized.isdigit():
        return False

    try:
        key = decode_base32_secret(secret)
    except Exception:
        return False

    now = int(time.time()) if timestamp is None else int(timestamp)
    base_counter = now // time_step

    matched = False
    for offset in range(-window, window + 1):
        candidate_counter = base_counter + offset
        if candidate_counter < 0:
            continue
        expected = generate_hotp_from_bytes(
            key=key,
            counter=candidate_counter,
            digits=digits,
            digest=digest,
        )
        if hmac.compare_digest(expected, normalized):
            matched = True
    return matched


def build_otpauth_uri(
    secret: str,
    account_name: str,
    issuer: str = "ADLAS",
    digits: int = DEFAULT_DIGITS,
    period: int = DEFAULT_TIME_STEP,
) -> str:
    """Build a standard otpauth:// URI for authenticator applications."""
    label = f"{quote(issuer)}:{quote(account_name)}"
    return (
        f"otpauth://totp/{label}"
        f"?secret={quote(secret)}"
        f"&issuer={quote(issuer)}"
        f"&algorithm=SHA1"
        f"&digits={digits}"
        f"&period={period}"
    )
