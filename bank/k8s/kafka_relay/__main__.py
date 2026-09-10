"""Entrypoint: `python -m kafka_relay` (image) / `python -m bank.k8s.kafka_relay` (repo)."""

from __future__ import annotations

import logging
import os

from prometheus_client import CollectorRegistry

try:
    from _shared.kafka import ConsumerLoop, KafkaSettings, make_consumer
    from _shared.server import run
except ImportError:
    from bank.k8s._shared.kafka import ConsumerLoop, KafkaSettings, make_consumer
    from bank.k8s._shared.server import run

from .service import ALERTS_RAW_TOPIC, KafkaRelayService

_CONSUMER_GROUP = "kafka-relay"


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    registry = CollectorRegistry()

    settings = KafkaSettings.from_env()
    if settings is None:
        raise RuntimeError("kafka-relay requires KAFKA_BOOTSTRAP to be set")

    ingest_url = os.environ["INGEST_URL"]
    secret = os.environ["INGEST_HMAC_SECRET"].encode()

    service = KafkaRelayService(registry, ingest_url, secret)

    consumer = make_consumer(settings, _CONSUMER_GROUP, [ALERTS_RAW_TOPIC])
    consumer_loop = ConsumerLoop(consumer, service.handle_message)
    consumer_loop.start()

    run(lambda: {"service": "kafka-relay"}, registry).serve_forever()


if __name__ == "__main__":
    main()
