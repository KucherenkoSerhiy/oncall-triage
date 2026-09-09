"""Business logic for the customer-notifications timer trigger.

Framework-free on purpose: ``function_app.py`` is the only module that
imports ``azure.functions``, so these tests never need the Functions host.
Faults come from the same control plane as the AWS bank estate (M4), but
Azure cannot read the DynamoDB table directly, so :class:`ChaosClient` polls
the console API's chaos route instead.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from collections.abc import Callable
from typing import Protocol

logger = logging.getLogger(__name__)

DEFAULT_CHAOS_URL = "https://api.triage.serhiykucherenko.dev/chaos"
SERVICE = "customer-notifications"

_TIMEOUT = 10
_BATCH_SIZE = 20


class ProviderError(Exception):
    pass


class Metrics(Protocol):
    def record(self, name: str, value: float) -> None: ...


class Http(Protocol):
    def __call__(self, url: str, headers: dict[str, str]) -> bytes: ...


def _default_http(url: str, headers: dict[str, str]) -> bytes:
    req = urllib.request.Request(url, method="GET", headers=headers)  # noqa: S310 - fixed chaos URL from app setting
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as response:  # noqa: S310 - fixed chaos URL from app setting
        return response.read()


class ChaosClient:
    """Polls the console API's ``GET /chaos`` route and caches the answer.

    A failed poll (network error, bad JSON, non-2xx) never raises - it just
    returns whatever was last cached, or ``None`` if nothing has been
    cached yet.
    """

    def __init__(
        self,
        chaos_url: str,
        token: str | None,
        ttl_seconds: float = 60,
        http: Http = _default_http,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._chaos_url = chaos_url
        self._token = token
        self._ttl_seconds = ttl_seconds
        self._http = http
        self._clock = clock
        self._cached_mode: str | None = None
        self._cached_at: float | None = None
        self._warned_missing_token = False

    def current_mode(self, service: str = SERVICE) -> str | None:
        if not self._token:
            if not self._warned_missing_token:
                logger.warning(
                    "CONSOLE_TOKEN is not set; customer-notifications runs in normal mode"
                )
                self._warned_missing_token = True
            return None

        now = self._clock()
        if self._cached_at is not None and now - self._cached_at < self._ttl_seconds:
            return self._cached_mode

        try:
            body = self._http(self._chaos_url, {"Authorization": f"Bearer {self._token}"})
            faults = json.loads(body)
            mode = next(
                (
                    fault.get("mode")
                    for fault in faults
                    if fault.get("service") == service and fault.get("active")
                ),
                None,
            )
        except Exception:  # a poll failure must never raise, only fall back to the cache
            logger.warning("chaos poll failed; using the last cached mode", exc_info=True)
            self._cached_at = now
            return self._cached_mode

        self._cached_mode = mode
        self._cached_at = now
        return mode


class AppInsightsMetrics:
    """Production `Metrics` backed by OpenTelemetry counters."""

    def __init__(self) -> None:
        from opentelemetry import metrics as otel_metrics

        self._meter = otel_metrics.get_meter("customer-notifications")
        self._counters: dict[str, object] = {}

    def record(self, name: str, value: float) -> None:
        counter = self._counters.get(name)
        if counter is None:
            counter = self._meter.create_counter(name)
            self._counters[name] = counter
        counter.add(value)  # type: ignore[attr-defined]


def send_batch(mode: str | None, metrics: Metrics) -> None:
    """ "Send" 20 notifications, recording metrics for the given fault mode."""
    if mode == "provider-429":
        metrics.record("provider_429", _BATCH_SIZE)
        raise ProviderError("SMS provider returned 429 Too Many Requests")

    metrics.record("notifications_sent", _BATCH_SIZE)
    if mode == "backlog":
        metrics.record("notifications_backlog", 150)
