"""Lambda handler for `auth`: EventBridge schedule, every minute.

Normal path "issues" synthetic tokens. Fault modes simulate a JWKS rotation
gone wrong (every verification fails) or a burst of account lockouts (a
softer failure that still succeeds).
"""

from __future__ import annotations

from typing import Any

from bank.aws.common import current_fault, emit_metric, fail

_SERVICE = "auth"
_ISSUED = 20


def lambda_handler(event: dict, context: Any) -> dict:
    mode = current_fault(_SERVICE)

    if mode == "jwks-rotation":
        emit_metric("AuthFailures", _ISSUED, _SERVICE)
        fail("JWT signature verification failed: unknown key id kid-77")

    if mode == "lockouts":
        emit_metric("AccountLockouts", 7, _SERVICE)

    return {"issued": _ISSUED}
