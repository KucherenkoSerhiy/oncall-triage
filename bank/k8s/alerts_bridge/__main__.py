"""Entrypoint: `python -m alerts_bridge` (image) / `python -m bank.k8s.alerts_bridge` (repo)."""

from __future__ import annotations

import logging

from prometheus_client import CollectorRegistry

try:
    from _shared.kafka import KafkaSettings, make_producer
except ImportError:
    from bank.k8s._shared.kafka import KafkaSettings, make_producer

from .server import run
from .service import AlertsBridgeService


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    registry = CollectorRegistry()

    settings = KafkaSettings.from_env()
    if settings is None:
        raise RuntimeError("alerts-bridge requires KAFKA_BOOTSTRAP to be set")

    publisher = make_producer(settings)
    service = AlertsBridgeService(registry, publisher)

    run(service, registry).serve_forever()


if __name__ == "__main__":
    main()
