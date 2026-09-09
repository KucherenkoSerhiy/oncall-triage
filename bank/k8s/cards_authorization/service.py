"""Business logic for cards-authorization, framework-free on purpose.

Deploys standalone (Docker image built from this directory plus `_shared`
copied in as a sibling - see `bank/k8s/cards_authorization/Dockerfile`), so
`_shared` is imported the same relative-path-safe way M5a's Azure apps
import their `_shared`: a top-level sibling package in the deployed image,
but nested under `bank.k8s` in the repo (and under pytest).
"""

from __future__ import annotations

import random
from typing import Any

from prometheus_client import CollectorRegistry, Counter, Histogram

try:
    from _shared.faults import FaultFile
except ImportError:
    from bank.k8s._shared.faults import FaultFile

SERVICE = "cards-authorization"
VALID_MODES = ("timeouts", "issuer-down")

_LATENCY_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
_TIMEOUT_LATENCY_SECONDS = 3.0


class CardsAuthorizationService:
    def __init__(
        self,
        registry: CollectorRegistry,
        fault_file: FaultFile | None = None,
    ) -> None:
        self._fault_file = fault_file or FaultFile(
            path="/etc/nordwind/fault", ttl=5, valid_modes=VALID_MODES
        )
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
        return {"mode": mode or "normal", "result": result, "latency_seconds": latency}
