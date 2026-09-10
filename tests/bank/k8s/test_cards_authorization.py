from __future__ import annotations

import json

from prometheus_client import CollectorRegistry

from bank.k8s._shared.kafka import KafkaMetrics
from bank.k8s.cards_authorization.service import CardsAuthorizationService


class FakeFaultFile:
    def __init__(self, mode: str | None = None) -> None:
        self.mode = mode

    def current(self) -> str | None:
        return self.mode


class FakePublisher:
    def __init__(self) -> None:
        self.published: list[tuple[str, str | None, bytes]] = []

    def publish(self, topic: str, key: str | None, value: bytes) -> None:
        self.published.append((topic, key, value))


class BrokenPublisher:
    def publish(self, topic: str, key: str | None, value: bytes) -> None:
        raise RuntimeError("boom")


def _counter_value(registry: CollectorRegistry, name: str, **labels: str) -> float:
    return registry.get_sample_value(name, labels) or 0.0


def test_normal_mode_records_ok_result():
    registry = CollectorRegistry()
    service = CardsAuthorizationService(registry, fault_file=FakeFaultFile(None))

    result = service.work()

    assert result["mode"] == "normal"
    assert result["result"] == "ok"
    assert _counter_value(registry, "cards_auth_requests_total", result="ok") == 1
    assert _counter_value(registry, "cards_auth_requests_total", result="error") == 0
    assert registry.get_sample_value("cards_auth_request_seconds_count") == 1


def test_timeouts_mode_observes_three_seconds_and_ok():
    registry = CollectorRegistry()
    service = CardsAuthorizationService(registry, fault_file=FakeFaultFile("timeouts"))

    result = service.work()

    assert result["mode"] == "timeouts"
    assert result["result"] == "ok"
    assert result["latency_seconds"] == 3.0
    assert registry.get_sample_value("cards_auth_request_seconds_sum") == 3.0
    assert _counter_value(registry, "cards_auth_requests_total", result="ok") == 1


def test_issuer_down_mode_always_errors():
    registry = CollectorRegistry()
    service = CardsAuthorizationService(registry, fault_file=FakeFaultFile("issuer-down"))

    for _ in range(5):
        result = service.work()
        assert result["result"] == "error"


def test_publishes_a_card_authorized_event_when_publisher_configured():
    registry = CollectorRegistry()
    publisher = FakePublisher()
    kafka_metrics = KafkaMetrics.create(registry)
    service = CardsAuthorizationService(
        registry, fault_file=FakeFaultFile(None), publisher=publisher, kafka_metrics=kafka_metrics
    )

    result = service.work()

    assert len(publisher.published) == 1
    topic, key, value = publisher.published[0]
    assert topic == "card.authorized"
    event = json.loads(value)
    assert set(event) == {"txn_id", "amount", "currency", "result", "ts"}
    assert event["currency"] == "EUR"
    assert event["result"] == result["result"]
    assert key == event["txn_id"]
    assert _counter_value(registry, "kafka_events_produced_total", topic="card.authorized") == 1


def test_no_publish_when_publisher_not_configured():
    registry = CollectorRegistry()
    service = CardsAuthorizationService(registry, fault_file=FakeFaultFile(None))

    service.work()  # must not raise with no publisher wired


def test_publish_error_increments_error_counter_and_does_not_raise():
    registry = CollectorRegistry()
    kafka_metrics = KafkaMetrics.create(registry)
    service = CardsAuthorizationService(
        registry,
        fault_file=FakeFaultFile(None),
        publisher=BrokenPublisher(),
        kafka_metrics=kafka_metrics,
    )

    service.work()  # must not raise even though the publisher fails

    assert _counter_value(registry, "kafka_produce_errors_total") == 1
    assert _counter_value(registry, "kafka_events_produced_total", topic="card.authorized") == 0
    # A failed publish doesn't affect the pre-existing (non-Kafka) request metrics.
    assert _counter_value(registry, "cards_auth_requests_total", result="ok") == 1
