"""Entrypoint: `python -m fraud_scoring` (image) / `python -m bank.k8s.fraud_scoring` (repo)."""

from __future__ import annotations

import logging

from prometheus_client import CollectorRegistry

try:
    from _shared.faults import FaultFile
    from _shared.kafka import (
        ConsumerLoop,
        KafkaMetrics,
        KafkaSettings,
        make_consumer,
        make_producer,
    )
    from _shared.server import run
    from _shared.ticker import Ticker
except ImportError:
    from bank.k8s._shared.faults import FaultFile
    from bank.k8s._shared.kafka import (
        ConsumerLoop,
        KafkaMetrics,
        KafkaSettings,
        make_consumer,
        make_producer,
    )
    from bank.k8s._shared.server import run
    from bank.k8s._shared.ticker import Ticker

from .service import CARD_AUTHORIZED_TOPIC, VALID_MODES, FraudScoringService

_CONSUMER_GROUP = "fraud-scoring"
_LAG_FAULT_MODE = "lag"


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    registry = CollectorRegistry()
    fault_file = FaultFile(path="/etc/nordwind/fault", ttl=5, valid_modes=VALID_MODES)

    kafka_settings = KafkaSettings.from_env()
    publisher = None
    kafka_metrics = None
    if kafka_settings is not None:
        publisher = make_producer(kafka_settings)
        kafka_metrics = KafkaMetrics.create(registry)

    service = FraudScoringService(
        registry, fault_file=fault_file, publisher=publisher, kafka_metrics=kafka_metrics
    )
    ticker = Ticker(service.work)
    ticker.start()

    if kafka_settings is not None:
        consumer = make_consumer(kafka_settings, _CONSUMER_GROUP, [CARD_AUTHORIZED_TOPIC])
        consumer_loop = ConsumerLoop(
            consumer,
            service.handle_card_authorized,
            fault_file=fault_file,
            pause_mode=_LAG_FAULT_MODE,
        )
        consumer_loop.start()

    run(service.work, registry).serve_forever()


if __name__ == "__main__":
    main()
