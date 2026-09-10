"""Business logic for cards-authorization, framework-free on purpose.

Deploys standalone (Docker image built from this directory plus `_shared`
copied in as a sibling - see `bank/k8s/cards_authorization/Dockerfile`), so
`_shared` is imported the same relative-path-safe way M5a's Azure apps
import their `_shared`: a top-level sibling package in the deployed image,
but nested under `bank.k8s` in the repo (and under pytest).
"""

from __future__ import annotations

import json
import random
import time
import uuid
from collections.abc import Callable
from typing import Any

from prometheus_client import CollectorRegistry, Counter, Histogram

try:
    from _shared.faults import FaultFile
    from _shared.kafka import KafkaMetrics, Publisher
except ImportError:
    from bank.k8s._shared.faults import FaultFile
    from bank.k8s._shared.kafka import KafkaMetrics, Publisher

SERVICE = "cards-authorization"
VALID_MODES = ("timeouts", "issuer-down")
CARD_AUTHORIZED_TOPIC = "card.authorized"

_LATENCY_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
_TIMEOUT_LATENCY_SECONDS = 3.0
_MIN_AMOUNT, _MAX_AMOUNT = 1.0, 500.0


class CardsAuthorizationService:
    def __init__(
        self,
        registry: CollectorRegistry,
        fault_file: FaultFile | None = None,
        publisher: Publisher | None = None,
        kafka_metrics: KafkaMetrics | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._fault_file = fault_file or FaultFile(
            path="/etc/nordwind/fault", ttl=5, valid_modes=VALID_MODES
        )
        self._publisher = publisher
        self._kafka_metrics = kafka_metrics
        self._clock = clock
        self.request_seconds = Histogram(
            "cards_auth_request_seconds",
            "Card authorization request latency in seconds",
            buckets=_LATENCY_BUCKETS,
            registry=registry,
        )
        self.requests_total = Counter(
            "cards_auth_requests_total",
            "Card authorization requests",
            ["result"],
            registry=registry,
        )

    def _publish_card_authorized(self, txn_id: str, amount: float, result: str) -> None:
        if self._publisher is None:
            return
        event = {
            "txn_id": txn_id,
            "amount": amount,
            "currency": "EUR",
            "result": result,
            "ts": self._clock(),
        }
        try:
            self._publisher.publish(CARD_AUTHORIZED_TOPIC, txn_id, json.dumps(event).encode())
        except Exception:
            if self._kafka_metrics is not None:
                self._kafka_metrics.produce_errors_total.inc()
            return
        if self._kafka_metrics is not None:
            self._kafka_metrics.produced_total.labels(topic=CARD_AUTHORIZED_TOPIC).inc()

    def work(self) -> dict[str, Any]:
        mode = self._fault_file.current()

        if mode == "timeouts":
            latency = _TIMEOUT_LATENCY_SECONDS
            result = "ok"
        elif mode == "issuer-down":
            latency = round(random.uniform(0.01, 0.05), 4)  # noqa: S311 - synthetic demo latency
            result = "error"
        else:
            latency = round(random.uniform(0.01, 0.08), 4)  # noqa: S311 - synthetic demo latency
            result = "ok"

        self.request_seconds.observe(latency)
        self.requests_total.labels(result=result).inc()

        txn_id = str(uuid.uuid4())
        amount = round(random.uniform(_MIN_AMOUNT, _MAX_AMOUNT), 2)  # noqa: S311 - synthetic demo amount
        self._publish_card_authorized(txn_id, amount, result)

        return {"mode": mode or "normal", "result": result, "latency_seconds": latency}
