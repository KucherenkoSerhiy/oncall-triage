"""HMAC-SHA256 request signing/verification for the alert-ingest HTTP endpoint."""

from __future__ import annotations

import hashlib
import hmac
import time


class HmacError(ValueError):
    pass


def sign(secret: bytes, timestamp: str, body: bytes) -> str:
    digest = hmac.new(secret, timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify(
    secret: bytes,
    timestamp: str,
    body: bytes,
    signature: str,
    now: float | None = None,
    max_skew_seconds: int = 300,
) -> None:
    try:
        ts = int(timestamp)
    except (TypeError, ValueError) as exc:
        raise HmacError(f"invalid timestamp {timestamp!r}") from exc

    current = time.time() if now is None else now
    if abs(current - ts) > max_skew_seconds:
        raise HmacError(f"timestamp {timestamp!r} outside allowed skew of {max_skew_seconds}s")

    if not signature or not signature.startswith("sha256="):
        raise HmacError("missing or malformed signature")

    expected = sign(secret, timestamp, body)
    if not hmac.compare_digest(expected, signature):
        raise HmacError("signature mismatch")
