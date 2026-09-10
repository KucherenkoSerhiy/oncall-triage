"""Kafka wiring shared by the three Kubernetes bank services (M7a).

`KafkaSettings.from_env()` reads the four env vars the Helm chart sets on
each Deployment when `kafka.enabled=true` (`deploy/helm/nordwind-bank/templates/kafka/`);
it returns `None` when `KAFKA_BOOTSTRAP` is unset, which is how a service
tells "no Kafka" (M6a ticker-only behaviour) from "Kafka wired up" apart.

`make_producer`/`make_consumer` build `confluent_kafka` clients authenticated
over the `tls` SCRAM-SHA-512 listener. `Publisher` is the narrow interface
service code depends on, so tests can inject a recording fake instead of a
real `confluent_kafka.Producer`. `ConsumerLoop` is the background-thread
consumer shape both fraud-scoring and open-banking-api use; `pause_mode`
implements the `lag` fault (fraud-scoring stops polling but stays alive).
"""

from __future__ import annotations

import logging
import os
import threading
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import confluent_kafka
from prometheus_client import CollectorRegistry, Counter

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class KafkaSettings:
    bootstrap: str
    user: str
    password_file: str
    ca_file: str

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> KafkaSettings | None:
        env = env if env is not None else os.environ
        bootstrap = env.get("KAFKA_BOOTSTRAP")
        if not bootstrap:
            return None
        return cls(
            bootstrap=bootstrap,
            user=env["KAFKA_USER"],
            password_file=env["KAFKA_PASSWORD_FILE"],
            ca_file=env["KAFKA_CA_FILE"],
        )

    def _password(self) -> str:
        return Path(self.password_file).read_text().strip()

    def client_config(self) -> dict[str, Any]:
        return {
            "bootstrap.servers": self.bootstrap,
            "security.protocol": "SASL_SSL",
            "sasl.mechanism": "SCRAM-SHA-512",
            "sasl.username": self.user,
            "sasl.password": self._password(),
            "ssl.ca.location": self.ca_file,
        }


class Publisher(Protocol):
    def publish(self, topic: str, key: str | None, value: bytes) -> None: ...


class KafkaPublisher:
    """Wraps a real `confluent_kafka.Producer` as a `Publisher`."""

    def __init__(self, producer: confluent_kafka.Producer) -> None:
        self._producer = producer

    def publish(self, topic: str, key: str | None, value: bytes) -> None:
        self._producer.produce(topic, key=key.encode() if key is not None else None, value=value)
        self._producer.poll(0)

    def flush(self, timeout: float = 10.0) -> None:
        self._producer.flush(timeout)


def make_producer(settings: KafkaSettings) -> Publisher:
    return KafkaPublisher(confluent_kafka.Producer(settings.client_config()))


def make_consumer(
    settings: KafkaSettings, group: str, topics: Iterable[str]
) -> confluent_kafka.Consumer:
    config = settings.client_config()
    config.update(
        {
            "group.id": group,
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
        }
    )
    consumer = confluent_kafka.Consumer(config)
    consumer.subscribe(list(topics))
    return consumer


class FaultFileLike(Protocol):
    def current(self) -> str | None: ...


class ConsumerLoop:
    """Background thread that polls a consumer and dispatches each message.

    `handle_message(consumer, message)` owns committing (so it can commit
    only after a successful publish, or after just counting - whatever the
    service needs); the loop never commits on its own.

    When `pause_mode` is set and `fault_file.current()` equals it, the loop
    stops calling `consumer.poll()` entirely (but keeps the thread and the
    pod alive) - this is the `lag` fault: unread messages pile up on the
    broker and `kafka_consumergroup_lag` grows.
    """

    def __init__(
        self,
        consumer: confluent_kafka.Consumer,
        handle_message: Callable[[confluent_kafka.Consumer, confluent_kafka.Message], None],
        *,
        fault_file: FaultFileLike | None = None,
        pause_mode: str | None = None,
        poll_timeout: float = 1.0,
    ) -> None:
        self._consumer = consumer
        self._handle_message = handle_message
        self._fault_file = fault_file
        self._pause_mode = pause_mode
        self._poll_timeout = poll_timeout
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        """Signal the loop to exit and wait for it to actually stop.

        The background thread may be blocked inside `consumer.poll()` for up
        to `poll_timeout` seconds; joining here (rather than just setting the
        stop event) means the caller can safely close the consumer as soon as
        `stop()` returns instead of racing a still-running `poll()` call
        against `close()` on the same `confluent_kafka.Consumer` object.
        """
        self._stop.set()
        self._thread.join(timeout=self._poll_timeout + 5)

    def _paused(self) -> bool:
        return bool(
            self._pause_mode is not None
            and self._fault_file is not None
            and self._fault_file.current() == self._pause_mode
        )

    def _run(self) -> None:
        while not self._stop.is_set():
            if self._paused():
                self._stop.wait(self._poll_timeout)
                continue
            msg = self._consumer.poll(self._poll_timeout)
            if msg is None:
                continue
            if msg.error():
                logger.warning("consumer error: %s", msg.error())
                continue
            try:
                self._handle_message(self._consumer, msg)
            except Exception:
                logger.exception("consumer message handler failed")


@dataclass
class KafkaMetrics:
    produced_total: Counter
    consumed_total: Counter
    produce_errors_total: Counter

    @classmethod
    def create(cls, registry: CollectorRegistry) -> KafkaMetrics:
        return cls(
            produced_total=Counter(
                "kafka_events_produced_total",
                "Kafka events produced, by topic",
                ["topic"],
                registry=registry,
            ),
            consumed_total=Counter(
                "kafka_events_consumed_total",
                "Kafka events consumed, by topic",
                ["topic"],
                registry=registry,
            ),
            produce_errors_total=Counter(
                "kafka_produce_errors_total",
                "Kafka produce errors",
                registry=registry,
            ),
        )
