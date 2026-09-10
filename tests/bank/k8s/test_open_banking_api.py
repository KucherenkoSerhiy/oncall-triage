from __future__ import annotations

from prometheus_client import CollectorRegistry

from bank.k8s._shared.kafka import KafkaMetrics
from bank.k8s.open_banking_api.service import OpenBankingApiService


class FakeFaultFile:
    def __init__(self, mode: str | None = None) -> None:
        self.mode = mode

    def current(self) -> str | None:
        return self.mode


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


def _counter_value(registry: CollectorRegistry, name: str, **labels: str) -> float:
    return registry.get_sample_value(name, labels) or 0.0


def test_normal_mode_always_200_and_expiry_ninety_days_out():
    registry = CollectorRegistry()
    now = 1_000_000.0
    service = OpenBankingApiService(registry, fault_file=FakeFaultFile(None), clock=lambda: now)

    for _ in range(10):
        result = service.work()
        assert result["code"] == "200"

    assert _counter_value(registry, "openbanking_responses_total", code="200") == 10
    assert _counter_value(registry, "openbanking_responses_total", code="429") == 0
    assert registry.get_sample_value("openbanking_cert_expiry_seconds") == now + 90 * 24 * 3600


def test_rate_limit_storm_mode_is_roughly_eighty_percent_429():
    registry = CollectorRegistry()
    service = OpenBankingApiService(registry, fault_file=FakeFaultFile("rate-limit-storm"))

    for _ in range(500):
        service.work()

    total_429 = _counter_value(registry, "openbanking_responses_total", code="429")
    total_200 = _counter_value(registry, "openbanking_responses_total", code="200")
    assert total_429 + total_200 == 500
    ratio = total_429 / 500
    assert 0.65 < ratio < 0.95


def test_cert_expiry_mode_sets_gauge_three_days_out():
    registry = CollectorRegistry()
    now = 1_000_000.0
    fault_file = FakeFaultFile("cert-expiry")
    service = OpenBankingApiService(registry, fault_file=fault_file, clock=lambda: now)

    service.work()

    assert registry.get_sample_value("openbanking_cert_expiry_seconds") == now + 3 * 24 * 3600


def test_handle_fraud_scored_counts_and_commits():
    registry = CollectorRegistry()
    kafka_metrics = KafkaMetrics.create(registry)
    service = OpenBankingApiService(registry, kafka_metrics=kafka_metrics)
    consumer = FakeConsumer()
    message = FakeMessage(b'{"txn_id": "t-1", "score": 0.1}')

    service.handle_fraud_scored(consumer, message)

    assert registry.get_sample_value("openbanking_events_consumed_total") == 1
    assert _counter_value(registry, "kafka_events_consumed_total", topic="fraud.scored") == 1
    assert consumer.committed == [message]
