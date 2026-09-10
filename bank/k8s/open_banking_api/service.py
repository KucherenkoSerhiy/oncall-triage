"""Business logic for open-banking-api, framework-free on purpose.

See `bank/k8s/cards_authorization/service.py` for the `_shared` sibling
import trick this module reuses.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import Any

from prometheus_client import CollectorRegistry, Counter, Gauge

try:
    from _shared.faults import FaultFile
    from _shared.kafka import KafkaMetrics
except ImportError:
    from bank.k8s._shared.faults import FaultFile
    from bank.k8s._shared.kafka import KafkaMetrics

SERVICE = "open-banking-api"
VALID_MODES = ("rate-limit-storm", "cert-expiry")
FRAUD_SCORED_TOPIC = "fraud.scored"

_NORMAL_EXPIRY_SECONDS = 90 * 24 * 3600
_STORM_MODE_EXPIRY_SECONDS = 3 * 24 * 3600
_RATE_LIMIT_STORM_RATIO = 0.8


class OpenBankingApiService:
    def __init__(
        self,
        registry: CollectorRegistry,
        fault_file: FaultFile | None = None,
        clock: Callable[[], float] = time.time,
        kafka_metrics: KafkaMetrics | None = None,
    ) -> None:
        self._fault_file = fault_file or FaultFile(
            path="/etc/nordwind/fault", ttl=5, valid_modes=VALID_MODES
        )
        self._clock = clock
        self._kafka_metrics = kafka_metrics
        self.responses_total = Counter(
            "openbanking_responses_total",
            "Open banking API responses",
            ["code"],
            registry=registry,
        )
        self.cert_expiry_seconds = Gauge(
            "openbanking_cert_expiry_seconds",
            "TLS certificate expiry, epoch seconds",
            registry=registry,
        )
        self.cert_expiry_seconds.set(self._clock() + _NORMAL_EXPIRY_SECONDS)
        self.events_consumed_total = Counter(
            "openbanking_events_consumed_total",
            "fraud.scored events consumed",
            registry=registry,
        )

    def work(self) -> dict[str, Any]:
        mode = self._fault_file.current()

        if mode == "cert-expiry":
            expiry_offset = _STORM_MODE_EXPIRY_SECONDS
        else:
            expiry_offset = _NORMAL_EXPIRY_SECONDS
        self.cert_expiry_seconds.set(self._clock() + expiry_offset)

        is_storm_429 = mode == "rate-limit-storm" and random.random() < _RATE_LIMIT_STORM_RATIO  # noqa: S311
        code = "429" if is_storm_429 else "200"

        self.responses_total.labels(code=code).inc()
        return {"mode": mode or "normal", "code": code}

    def handle_fraud_scored(self, consumer: Any, message: Any) -> None:
        """`ConsumerLoop` handler for a `fraud.scored` message."""
        self.events_consumed_total.inc()
        if self._kafka_metrics is not None:
            self._kafka_metrics.consumed_total.labels(topic=FRAUD_SCORED_TOPIC).inc()
        consumer.commit(message=message)
