"""Thin HTTP client wrapping ``urllib.request``.

All HTTP traffic goes through :func:`request` so tests can monkeypatch a
single choke point instead of the network.
"""

from __future__ import annotations

import urllib.error
import urllib.request

_TIMEOUT = 10


class BankopsError(Exception):
    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"HTTP {status}: {body}")
        self.status = status
        self.body = body


def request(method: str, url: str, headers: dict | None = None, body: bytes | None = None) -> bytes:
    req = urllib.request.Request(url, method=method, headers=headers or {}, data=body)  # noqa: S310 - fixed base URL from config
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as response:  # noqa: S310 - fixed base URL from config
            return response.read()
    except urllib.error.HTTPError as exc:
        raise BankopsError(exc.code, exc.read().decode()) from exc
