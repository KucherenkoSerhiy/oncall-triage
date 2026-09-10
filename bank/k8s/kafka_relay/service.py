"""Business logic for kafka-relay: consumes `alerts.raw` and POSTs each alert,
HMAC-signed, to the AWS ingest endpoint (route A's second hop).

See `bank/k8s/cards_authorization/service.py` for the `_shared` sibling
import trick this module reuses.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any, Protocol

from prometheus_client import CollectorRegistry, Counter, Gauge

try:
    from _shared.hmac_sign import signed_headers
except ImportError:
    from bank.k8s._shared.hmac_sign import signed_headers

logger = logging.getLogger(__name__)

ALERTS_RAW_TOPIC = "alerts.raw"
RECEIVER = "route-a-kafka"

# 1, 2, 4, 8, 16s - five retries after the first attempt before giving up.
_BACKOFF_SECONDS: tuple[float, ...] = (1.0, 2.0, 4.0, 8.0, 16.0)
_TIMEOUT_SECONDS = 10


class Http(Protocol):
    def __call__(
        self, method: str, url: str, headers: dict[str, str], body: bytes
    ) -> tuple[int, bytes]: ...


def _default_http(method: str, url: str, headers: dict[str, str], body: bytes) -> tuple[int, bytes]:
    req = urllib.request.Request(url, method=method, headers=headers, data=body)  # noqa: S310 - fixed ingest URL from an env var
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as response:  # noqa: S310
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except urllib.error.URLError:
        return 0, b""


class KafkaRelayService:
    def __init__(
        self,
        registry: CollectorRegistry,
        ingest_url: str,
        secret: bytes,
        http: Http = _default_http,
        sleep: Callable[[float], None] = time.sleep,
        wall_clock: Callable[[], float] = time.time,
        backoff: tuple[float, ...] = _BACKOFF_SECONDS,
    ) -> None:
        self._ingest_url = ingest_url
        self._secret = secret
        self._http = http
        self._sleep = sleep
        self._wall_clock = wall_clock
        self._backoff = backoff
        self.posted_total = Counter(
            "relay_posted_total", "Alerts successfully posted to ingest", registry=registry
        )
        self.failures_total = Counter(
            "relay_failures_total",
            "Non-2xx responses or network errors posting to ingest",
            registry=registry,
        )
        self.dropped_total = Counter(
            "relay_dropped_total",
            "Messages dropped (committed without a successful post) after exhausting retries",
            registry=registry,
        )
        self.last_success_timestamp = Gauge(
            "relay_last_success_timestamp_seconds",
            "Wall-clock time of the last successful post to ingest",
            registry=registry,
        )
        self.inflight = Gauge(
            "relay_inflight", "Messages currently being relayed to ingest", registry=registry
        )

    def _post_once(self, body: bytes) -> bool:
        headers = signed_headers(self._secret, body, now=self._wall_clock)
        status, _body = self._http("POST", self._ingest_url, headers, body)
        if 200 <= status < 300:
            self.posted_total.inc()
            self.last_success_timestamp.set(self._wall_clock())
            return True
        self.failures_total.inc()
        logger.warning("post to ingest failed: status=%s", status)
        return False

    def handle_message(self, consumer: Any, message: Any) -> None:
        """`ConsumerLoop` handler for an `alerts.raw` message.

        Wraps the message as an Alertmanager-shaped payload inside ingest's
        {source, payload} envelope, HMAC-signs it,
        and POSTs it to ingest with exponential backoff on failure. Commits
        the message either way - after a successful post, or after the last
        retry is exhausted (counted as `relay_dropped_total`) - so one bad
        message can never block the rest of the partition.
        """
        alert = json.loads(message.value())
        # Ingest reads an envelope - {"source": ..., "payload": ...} - and hands
        # the payload to the adapter named by `source` (services/ingest/handler.py);
        # a bare Alertmanager payload is a 400 (#86 - the first route-A demo).
        payload = {"receiver": RECEIVER, "status": "firing", "alerts": [alert]}
        body = json.dumps({"source": "alertmanager", "payload": payload}).encode()

        self.inflight.inc()
        try:
            posted = self._post_once(body)
            for delay in self._backoff:
                if posted:
                    break
                self._sleep(delay)
                posted = self._post_once(body)
            if not posted:
                self.dropped_total.inc()
        finally:
            self.inflight.dec()

        consumer.commit(message=message)
