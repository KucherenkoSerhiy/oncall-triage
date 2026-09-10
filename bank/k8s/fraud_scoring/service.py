"""Business logic for fraud-scoring, framework-free on purpose.

See `bank/k8s/cards_authorization/service.py` for the `_shared` sibling
import trick this module reuses.

Two independent drivers call into this service: the ticker (`work()`, M6a
behaviour, still runs whether or not Kafka is configured) and, when Kafka
settings are present, a `_shared.kafka.ConsumerLoop` on `card.authorized`
(`handle_card_authorized`, M7a) that scores real events and publishes
`fraud.scored`. Both share the same mean/stddev-by-mode scoring so the
`model-drift` fault behaves identically either way.
"""

from __future__ import annotations

import json
import random
import sys
import time
from collections.abc import Callable
from typing import Any

from prometheus_client import CollectorRegistry, Counter, Histogram

try:
    from _shared.faults import FaultFile
    from _shared.kafka import KafkaMetrics, Publisher
except ImportError:
    from bank.k8s._shared.faults import FaultFile
    from bank.k8s._shared.kafka import KafkaMetrics, Publisher

SERVICE = "fraud-scoring"
VALID_MODES = ("model-drift", "latency", "crashloop", "lag")
CARD_AUTHORIZED_TOPIC = "card.authorized"
FRAUD_SCORED_TOPIC = "fraud.scored"

_SCORE_BUCKETS = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
_LATENCY_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0)
_LATENCY_FAULT_SECONDS = 2.0
_CRASHLOOP_DEADLINE_SECONDS = 10.0
_NORMAL_MEAN, _NORMAL_STDDEV = 0.2, 0.05
_DRIFT_MEAN, _DRIFT_STDDEV = 0.8, 0.05


class FraudScoringService:
    def __init__(
        self,
        registry: CollectorRegistry,
        fault_file: FaultFile | None = None,
        clock: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], float] = time.time,
        publisher: Publisher | None = None,
        kafka_metrics: KafkaMetrics | None = None,
    ) -> None:
        self._fault_file = fault_file or FaultFile(
            path="/etc/nordwind/fault", ttl=5, valid_modes=VALID_MODES
        )
        self._clock = clock
        self._wall_clock = wall_clock
        self._publisher = publisher
        self._kafka_metrics = kafka_metrics
        self._crashloop_since: float | None = None
        self.score_bucket = Histogram(
            "fraud_score_bucket",
            "Fraud score distribution",
            buckets=_SCORE_BUCKETS,
            registry=registry,
        )
        self.scored_total = Counter("fraud_scored_total", "Fraud scoring events", registry=registry)
        self.scoring_seconds = Histogram(
            "fraud_scoring_seconds",
            "Fraud scoring latency in seconds",
            buckets=_LATENCY_BUCKETS,
            registry=registry,
        )

    def _score(self, mode: str | None) -> float:
        if mode == "model-drift":
            mean, stddev = _DRIFT_MEAN, _DRIFT_STDDEV
        else:
            mean, stddev = _NORMAL_MEAN, _NORMAL_STDDEV
        return min(1.0, max(0.0, random.gauss(mean, stddev)))

    def work(self) -> dict[str, Any]:
        mode = self._fault_file.current()

        if mode == "crashloop":
            if self._crashloop_since is None:
                self._crashloop_since = self._clock()
            elif self._clock() - self._crashloop_since >= _CRASHLOOP_DEADLINE_SECONDS:
                sys.exit(1)
        else:
            self._crashloop_since = None

        if mode == "lag":
            return {"mode": mode, "skipped": True}

        score = self._score(mode)

        self.score_bucket.observe(score)
        self.scored_total.inc()

        if mode == "latency":
            self.scoring_seconds.observe(_LATENCY_FAULT_SECONDS)

        return {"mode": mode or "normal", "score": round(score, 4)}

    def handle_card_authorized(self, consumer: Any, message: Any) -> None:
        """`ConsumerLoop` handler for a `card.authorized` message.

        Scores the event with the same mode-driven distribution as `work()`,
        publishes `fraud.scored`, and commits the message only once that
        publish has succeeded.
        """
        mode = self._fault_file.current()
        event = json.loads(message.value())

        score = self._score(mode)
        self.score_bucket.observe(score)
        self.scored_total.inc()
        if mode == "latency":
            self.scoring_seconds.observe(_LATENCY_FAULT_SECONDS)
        if self._kafka_metrics is not None:
            self._kafka_metrics.consumed_total.labels(topic=CARD_AUTHORIZED_TOPIC).inc()

        fraud_event = {
            "txn_id": event.get("txn_id"),
            "score": round(score, 4),
            "ts": self._wall_clock(),
        }

        if self._publisher is not None:
            try:
                self._publisher.publish(
                    FRAUD_SCORED_TOPIC, fraud_event["txn_id"], json.dumps(fraud_event).encode()
                )
            except Exception:
                if self._kafka_metrics is not None:
                    self._kafka_metrics.produce_errors_total.inc()
                return
            if self._kafka_metrics is not None:
                self._kafka_metrics.produced_total.labels(topic=FRAUD_SCORED_TOPIC).inc()

        consumer.commit(message=message)
