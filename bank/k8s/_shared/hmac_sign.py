"""HMAC-SHA256 request signing for the alert-ingest HTTP endpoint.

Duplicated from ``services/ingest/hmac_auth.py`` (sign side only) rather than
imported: `kafka-relay` deploys standalone, built from this ``_shared``
directory copied in alongside ``bank/k8s/kafka_relay/`` (M6a's sibling-import
trick), so the image never depends on the ``services`` package.
``tests/bank/k8s/test_hmac_sign.py`` pins this copy to the original - and to
``bank/azure/_shared/hmac_sign.py`` - so the three algorithms never drift
apart.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Callable


def sign(secret: bytes, timestamp: str, body: bytes) -> str:
    digest = hmac.new(secret, timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def signed_headers(
    secret: bytes, body: bytes, now: Callable[[], float] = time.time
) -> dict[str, str]:
    timestamp = str(int(now()))
    return {
        "Content-Type": "application/json",
        "X-Nordwind-Timestamp": timestamp,
        "X-Nordwind-Signature": sign(secret, timestamp, body),
    }
