"""Business logic for the alert-forwarder HTTP trigger.

Framework-free on purpose: ``function_app.py`` is the only module that
imports ``azure.functions``. Deploys standalone, zipped from this directory
plus ``_shared`` copied in as a sibling folder (M5b) - see
``bank/azure/_shared/hmac_sign.py`` for why the import below has a
try/except: in the deployed zip ``_shared`` is a top-level sibling package
next to this file, but in the repo (and under pytest) it lives nested under
``bank/azure/_shared``.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Literal, Protocol

try:
    from _shared.hmac_sign import signed_headers
except ImportError:
    from bank.azure._shared.hmac_sign import signed_headers

logger = logging.getLogger(__name__)

DEFAULT_INGEST_URL = "https://api.triage.serhiykucherenko.dev/alerts"

_TIMEOUT = 10

AlertSource = Literal["azure-monitor", "alertmanager"]


class Http(Protocol):
    def __call__(
        self, method: str, url: str, headers: dict[str, str], body: bytes
    ) -> tuple[int, bytes]: ...


def _default_http(method: str, url: str, headers: dict[str, str], body: bytes) -> tuple[int, bytes]:
    req = urllib.request.Request(url, method=method, headers=headers, data=body)  # noqa: S310 - fixed ingest URL from app setting
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as response:  # noqa: S310
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


@dataclass
class ForwardResult:
    status: int
    source: AlertSource
    alert_count: int


def classify(payload: dict) -> AlertSource:
    data = payload.get("data")
    if isinstance(data, dict) and "essentials" in data:
        return "azure-monitor"
    if isinstance(payload.get("alerts"), list):
        return "alertmanager"
    raise ValueError("payload matches neither the azure-monitor nor the alertmanager shape")


def forward(
    payload: dict,
    ingest_url: str,
    secret: bytes,
    http: Http = _default_http,
) -> ForwardResult:
    source = classify(payload)
    alert_count = len(payload["alerts"]) if source == "alertmanager" else 1

    body = json.dumps({"source": source, "payload": payload}).encode()
    headers = signed_headers(secret, body)
    status, _response_body = http("POST", ingest_url, headers, body)

    logger.info(
        json.dumps(
            {
                "event": "forward",
                "source": source,
                "ingest_status": status,
                "alert_count": alert_count,
            }
        )
    )
    return ForwardResult(status=status, source=source, alert_count=alert_count)
