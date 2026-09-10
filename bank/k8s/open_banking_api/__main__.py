"""Entrypoint: `python -m open_banking_api` (image) /
`python -m bank.k8s.open_banking_api` (repo)."""

from __future__ import annotations

import logging

from prometheus_client import CollectorRegistry

try:
    from _shared.kafka import ConsumerLoop, KafkaMetrics, KafkaSettings, make_consumer
    from _shared.server import run
    from _shared.ticker import Ticker
except ImportError:
    from bank.k8s._shared.kafka import ConsumerLoop, KafkaMetrics, KafkaSettings, make_consumer
    from bank.k8s._shared.server import run
    from bank.k8s._shared.ticker import Ticker

from .service import FRAUD_SCORED_TOPIC, OpenBankingApiService

_CONSUMER_GROUP = "open-banking-api"


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    registry = CollectorRegistry()

    kafka_settings = KafkaSettings.from_env()
    kafka_metrics = None
    if kafka_settings is not None:
        kafka_metrics = KafkaMetrics.create(registry)

    service = OpenBankingApiService(registry, kafka_metrics=kafka_metrics)
    ticker = Ticker(service.work)
    ticker.start()

    if kafka_settings is not None:
        consumer = make_consumer(kafka_settings, _CONSUMER_GROUP, [FRAUD_SCORED_TOPIC])
        consumer_loop = ConsumerLoop(consumer, service.handle_fraud_scored)
        consumer_loop.start()

    run(service.work, registry).serve_forever()


if __name__ == "__main__":
    main()
