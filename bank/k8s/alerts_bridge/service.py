"""Business logic for alerts-bridge: an Alertmanager webhook receiver that
produces one Kafka message per alert to `alerts.raw` (route A's first hop).

See `bank/k8s/cards_authorization/service.py` for the `_shared` sibling
import trick this module reuses.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Protocol

from prometheus_client import CollectorRegistry, Counter

ALERTS_RAW_TOPIC = "alerts.raw"
RECEIVER = "route-a-kafka"


class FlushingPublisher(Protocol):
    """A `_shared.kafka.Publisher` that can also flush - what
    `_shared.kafka.make_producer` returns, and what a test fake must
    implement so `handle_webhook` can answer 202 only once every message has
    actually left the local producer buffer."""

    def publish(self, topic: str, key: str | None, value: bytes) -> None: ...
    def flush(self, timeout: float = 10.0) -> None: ...


class AlertsBridgeService:
    def __init__(
        self,
        registry: CollectorRegistry,
        publisher: FlushingPublisher,
        wall_clock: Callable[[], float] = time.time,
    ) -> None:
        self._publisher = publisher
        self._wall_clock = wall_clock
        self.alerts_produced_total = Counter(
            "bridge_alerts_produced_total",
            "Alerts produced to alerts.raw",
            registry=registry,
        )
        self.produce_errors_total = Counter(
            "bridge_produce_errors_total",
            "Kafka produce/flush errors in alerts-bridge",
            registry=registry,
        )

    def handle_webhook(self, payload: dict[str, Any]) -> int:
        """Produce one `alerts.raw` message per alert in an Alertmanager
        webhook payload.

        Returns the HTTP status to answer with: 202 once every message has
        been produced and flushed, 500 if any produce or flush call failed.
        """
        bridge_ts = datetime.fromtimestamp(self._wall_clock(), UTC).isoformat()
        had_error = False

        for alert in payload.get("alerts", []):
            value = {**alert, "receiver": RECEIVER, "bridge_ts": bridge_ts}
            try:
                self._publisher.publish(
                    ALERTS_RAW_TOPIC, alert.get("fingerprint"), json.dumps(value).encode()
                )
            except Exception:
                had_error = True
                self.produce_errors_total.inc()
                continue
            self.alerts_produced_total.inc()

        try:
            self._publisher.flush()
        except Exception:
            had_error = True
            self.produce_errors_total.inc()

        return 500 if had_error else 202
