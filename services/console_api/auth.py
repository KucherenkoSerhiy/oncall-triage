"""Bearer-token auth for the console API."""

from __future__ import annotations

import hmac


class AuthError(Exception):
    pass


def check_bearer(headers: dict, expected_token: str) -> None:
    lowered = {k.lower(): v for k, v in headers.items()}
    value = lowered.get("authorization", "")
    prefix = "Bearer "
    if not value.startswith(prefix):
        raise AuthError("missing or malformed Authorization header")

    token = value[len(prefix) :]
    if not hmac.compare_digest(token, expected_token):
        raise AuthError("token mismatch")
