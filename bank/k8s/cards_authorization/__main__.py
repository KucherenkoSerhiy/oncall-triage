"""Entrypoint: `python -m cards_authorization` (image) /
`python -m bank.k8s.cards_authorization` (repo)."""

from __future__ import annotations

import logging

from prometheus_client import CollectorRegistry

try:
    from _shared.kafka import KafkaMetrics, KafkaSettings, make_producer
    from _shared.server import run
    from _shared.ticker import Ticker
except ImportError:
    from bank.k8s._shared.kafka import KafkaMetrics, KafkaSettings, make_producer
    from bank.k8s._shared.server import run
    from bank.k8s._shared.ticker import Ticker

from .service import CardsAuthorizationService


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    registry = CollectorRegistry()

    kafka_settings = KafkaSettings.from_env()
    publisher = None
    kafka_metrics = None
    if kafka_settings is not None:
        publisher = make_producer(kafka_settings)
        kafka_metrics = KafkaMetrics.create(registry)

    service = CardsAuthorizationService(registry, publisher=publisher, kafka_metrics=kafka_metrics)
    ticker = Ticker(service.work)
    ticker.start()
    run(service.work, registry).serve_forever()


if __name__ == "__main__":
    main()
