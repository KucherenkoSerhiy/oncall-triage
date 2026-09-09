"""Business logic for fraud-scoring, framework-free on purpose.

See `bank/k8s/cards_authorization/service.py` for the `_shared` sibling
import trick this module reuses.
"""

from __future__ import annotations

import random
import sys
import time
from collections.abc import Callable
from typing import Any

from prometheus_client import CollectorRegistry, Counter, Histogram

try:
    from _shared.faults import FaultFile
except ImportError:
    from bank.k8s._shared.faults import FaultFile

SERVICE = "fraud-scoring"
VALID_MODES = ("model-drift", "latency", "crashloop", "lag")

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
    ) -> None:
        self._fault_file = fault_file or FaultFile(
            path="/etc/nordwind/fault", ttl=5, valid_modes=VALID_MODES
        )
        self._clock = clock
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

        if mode == "model-drift":
            mean, stddev = _DRIFT_MEAN, _DRIFT_STDDEV
        else:
            mean, stddev = _NORMAL_MEAN, _NORMAL_STDDEV
        score = min(1.0, max(0.0, random.gauss(mean, stddev)))

        self.score_bucket.observe(score)
        self.scored_total.inc()

        if mode == "latency":
            self.scoring_seconds.observe(_LATENCY_FAULT_SECONDS)

        return {"mode": mode or "normal", "score": round(score, 4)}
