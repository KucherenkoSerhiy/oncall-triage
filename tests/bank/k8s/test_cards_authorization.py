from __future__ import annotations

from prometheus_client import CollectorRegistry

from bank.k8s.cards_authorization.service import CardsAuthorizationService


class FakeFaultFile:
    def __init__(self, mode: str | None = None) -> None:
        self.mode = mode

    def current(self) -> str | None:
        return self.mode


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

    assert _counter_value(registry, "cards_auth_requests_total", result="error") == 5
    assert _counter_value(registry, "cards_auth_requests_total", result="ok") == 0
