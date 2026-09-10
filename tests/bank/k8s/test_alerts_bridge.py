from __future__ import annotations

import json

from prometheus_client import CollectorRegistry

from bank.k8s.alerts_bridge.service import ALERTS_RAW_TOPIC, AlertsBridgeService


class FakePublisher:
    def __init__(self, fail_on: set[str] | None = None, fail_flush: bool = False) -> None:
        self.published: list[tuple[str, str | None, bytes]] = []
        self._fail_on = fail_on or set()
        self._fail_flush = fail_flush
        self.flushed = False

    def publish(self, topic: str, key: str | None, value: bytes) -> None:
        if key in self._fail_on:
            raise RuntimeError("boom")
        self.published.append((topic, key, value))

    def flush(self, timeout: float = 10.0) -> None:
        if self._fail_flush:
            raise RuntimeError("flush boom")
        self.flushed = True


def _payload(*alerts):
    return {"receiver": "route-a-kafka", "status": "firing", "alerts": list(alerts)}


def test_produces_one_message_per_alert_keyed_by_fingerprint():
    publisher = FakePublisher()
    service = AlertsBridgeService(CollectorRegistry(), publisher, wall_clock=lambda: 1700000000.0)
    payload = _payload(
        {"fingerprint": "f1", "labels": {"alertname": "A"}, "status": "firing"},
        {"fingerprint": "f2", "labels": {"alertname": "B"}, "status": "firing"},
    )

    status = service.handle_webhook(payload)

    assert status == 202
    assert publisher.flushed is True
    assert [key for _topic, key, _value in publisher.published] == ["f1", "f2"]
    for topic, _key, _value in publisher.published:
        assert topic == ALERTS_RAW_TOPIC


def test_message_value_is_the_alert_plus_receiver_and_bridge_ts():
    publisher = FakePublisher()
    service = AlertsBridgeService(CollectorRegistry(), publisher, wall_clock=lambda: 1700000000.0)
    alert = {
        "fingerprint": "f1",
        "labels": {"alertname": "A", "service": "kafka"},
        "status": "firing",
    }

    service.handle_webhook(_payload(alert))

    value = json.loads(publisher.published[0][2])
    assert value["fingerprint"] == "f1"
    assert value["labels"] == {"alertname": "A", "service": "kafka"}
    assert value["receiver"] == "route-a-kafka"
    assert "bridge_ts" in value


def test_returns_500_and_counts_error_when_a_produce_fails():
    publisher = FakePublisher(fail_on={"f2"})
    registry = CollectorRegistry()
    service = AlertsBridgeService(registry, publisher)

    status = service.handle_webhook(
        _payload(
            {"fingerprint": "f1", "labels": {}, "status": "firing"},
            {"fingerprint": "f2", "labels": {}, "status": "firing"},
        )
    )

    assert status == 500
    assert [key for _t, key, _v in publisher.published] == ["f1"]
    assert registry.get_sample_value("bridge_produce_errors_total") == 1
    assert registry.get_sample_value("bridge_alerts_produced_total") == 1


def test_returns_500_when_flush_fails():
    publisher = FakePublisher(fail_flush=True)
    registry = CollectorRegistry()
    service = AlertsBridgeService(registry, publisher)

    status = service.handle_webhook(
        _payload({"fingerprint": "f1", "labels": {}, "status": "firing"})
    )

    assert status == 500
    assert registry.get_sample_value("bridge_produce_errors_total") == 1


def test_metrics_registered_with_the_expected_names():
    registry = CollectorRegistry()
    AlertsBridgeService(registry, FakePublisher())

    names = {sample.name for metric in registry.collect() for sample in metric.samples}
    assert "bridge_alerts_produced_total" in names
    assert "bridge_produce_errors_total" in names
