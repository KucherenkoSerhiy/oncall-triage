from __future__ import annotations

import json

from prometheus_client import CollectorRegistry

from bank.k8s.kafka_relay.service import RECEIVER, KafkaRelayService
from services.ingest import hmac_auth

SECRET = b"test-secret"


class FakeMessage:
    def __init__(self, value: bytes) -> None:
        self._value = value

    def value(self) -> bytes:
        return self._value


class FakeConsumer:
    def __init__(self) -> None:
        self.committed: list[FakeMessage] = []

    def commit(self, message: FakeMessage | None = None, **kwargs: object) -> None:
        self.committed.append(message)


def _alert(fingerprint: str = "f1") -> dict:
    return {
        "fingerprint": fingerprint,
        "status": "firing",
        "labels": {"alertname": "KafkaConsumerLag", "service": "fraud-scoring"},
        "receiver": "route-a-kafka",
        "bridge_ts": "2026-01-01T00:00:00+00:00",
    }


def _service(registry, http, sleeps=None, **kwargs) -> KafkaRelayService:
    sleeps = sleeps if sleeps is not None else []
    return KafkaRelayService(
        registry,
        "https://ingest.example/alerts",
        SECRET,
        http=http,
        sleep=lambda seconds: sleeps.append(seconds),
        wall_clock=lambda: 1700000000.0,
        **kwargs,
    )


def test_posts_an_alertmanager_shaped_body_with_a_verifiable_hmac_signature():
    calls = []

    def http(method, url, headers, body):
        calls.append((method, url, headers, body))
        return 200, b""

    registry = CollectorRegistry()
    service = _service(registry, http)
    consumer = FakeConsumer()
    message = FakeMessage(json.dumps(_alert()).encode())

    service.handle_message(consumer, message)

    assert len(calls) == 1
    method, url, headers, body = calls[0]
    assert method == "POST"
    assert url == "https://ingest.example/alerts"
    payload = json.loads(body)
    assert payload == {"receiver": RECEIVER, "status": "firing", "alerts": [_alert()]}

    hmac_auth.verify(
        SECRET,
        headers["X-Nordwind-Timestamp"],
        body,
        headers["X-Nordwind-Signature"],
        now=1700000000.0,
    )


def test_commits_only_after_a_2xx():
    registry = CollectorRegistry()
    service = _service(registry, http=lambda *a: (200, b""))
    consumer = FakeConsumer()
    message = FakeMessage(json.dumps(_alert()).encode())

    service.handle_message(consumer, message)

    assert consumer.committed == [message]
    assert registry.get_sample_value("relay_posted_total") == 1
    assert registry.get_sample_value("relay_dropped_total") == 0
    assert registry.get_sample_value("relay_last_success_timestamp_seconds") == 1700000000.0


def test_retries_with_exponential_backoff_then_succeeds():
    statuses = iter([500, 500, 200])

    def http(*_a):
        return next(statuses), b""

    sleeps: list[float] = []
    registry = CollectorRegistry()
    service = _service(registry, http, sleeps=sleeps)
    consumer = FakeConsumer()

    service.handle_message(consumer, FakeMessage(json.dumps(_alert()).encode()))

    assert sleeps == [1.0, 2.0]
    assert consumer.committed
    assert registry.get_sample_value("relay_failures_total") == 2
    assert registry.get_sample_value("relay_posted_total") == 1


def test_drops_and_commits_after_exhausting_all_retries():
    def http(*_a):
        return 500, b""

    sleeps: list[float] = []
    registry = CollectorRegistry()
    service = _service(registry, http, sleeps=sleeps)
    consumer = FakeConsumer()
    message = FakeMessage(json.dumps(_alert()).encode())

    service.handle_message(consumer, message)

    assert sleeps == [1.0, 2.0, 4.0, 8.0, 16.0]
    assert consumer.committed == [message]
    assert registry.get_sample_value("relay_dropped_total") == 1
    assert registry.get_sample_value("relay_posted_total") == 0
    assert registry.get_sample_value("relay_failures_total") == 6


def test_network_error_is_treated_as_a_failure_and_retried():
    def http(*_a):
        return 0, b""

    sleeps: list[float] = []
    registry = CollectorRegistry()
    service = _service(registry, http, sleeps=sleeps)
    consumer = FakeConsumer()

    service.handle_message(consumer, FakeMessage(json.dumps(_alert()).encode()))

    assert sleeps == [1.0, 2.0, 4.0, 8.0, 16.0]
    assert registry.get_sample_value("relay_dropped_total") == 1


def test_inflight_gauge_is_zero_after_handling_a_message():
    registry = CollectorRegistry()
    service = _service(registry, http=lambda *a: (200, b""))

    service.handle_message(FakeConsumer(), FakeMessage(json.dumps(_alert()).encode()))

    assert registry.get_sample_value("relay_inflight") == 0
