from __future__ import annotations

from prometheus_client import CollectorRegistry

from bank.k8s.fraud_scoring.service import FraudScoringService


class FakeFaultFile:
    def __init__(self, mode: str | None = None) -> None:
        self.mode = mode

    def current(self) -> str | None:
        return self.mode


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


def test_normal_mode_scores_around_point_two():
    registry = CollectorRegistry()
    fault_file = FakeFaultFile(None)
    service = FraudScoringService(registry, fault_file=fault_file)

    scores = [service.work()["score"] for _ in range(200)]

    assert all(0.0 <= s <= 1.0 for s in scores)
    mean = sum(scores) / len(scores)
    assert 0.1 < mean < 0.3
    assert registry.get_sample_value("fraud_scored_total") == 200


def test_model_drift_mode_scores_around_point_eight():
    registry = CollectorRegistry()
    fault_file = FakeFaultFile("model-drift")
    service = FraudScoringService(registry, fault_file=fault_file)

    scores = [service.work()["score"] for _ in range(200)]

    assert all(0.0 <= s <= 1.0 for s in scores)
    mean = sum(scores) / len(scores)
    assert mean > 0.6


def test_latency_mode_observes_two_seconds():
    registry = CollectorRegistry()
    fault_file = FakeFaultFile("latency")
    service = FraudScoringService(registry, fault_file=fault_file)

    service.work()

    assert registry.get_sample_value("fraud_scoring_seconds_sum") == 2.0
    assert registry.get_sample_value("fraud_scoring_seconds_count") == 1


def test_lag_mode_is_a_noop():
    registry = CollectorRegistry()
    fault_file = FakeFaultFile("lag")
    service = FraudScoringService(registry, fault_file=fault_file)

    result = service.work()

    assert result == {"mode": "lag", "skipped": True}
    assert registry.get_sample_value("fraud_scored_total") == 0


def test_crashloop_exits_after_ten_seconds(monkeypatch):
    registry = CollectorRegistry()
    fault_file = FakeFaultFile("crashloop")
    clock = FakeClock()
    service = FraudScoringService(registry, fault_file=fault_file, clock=clock)

    exit_calls: list[int] = []
    monkeypatch.setattr("bank.k8s.fraud_scoring.service.sys.exit", exit_calls.append)

    for elapsed in (0, 2, 4, 6, 8):
        clock.now = elapsed
        service.work()
    assert exit_calls == []

    clock.now = 10
    service.work()
    assert exit_calls == [1]


def test_crashloop_timer_resets_when_mode_clears(monkeypatch):
    registry = CollectorRegistry()
    fault_file = FakeFaultFile("crashloop")
    clock = FakeClock()
    service = FraudScoringService(registry, fault_file=fault_file, clock=clock)

    exit_calls: list[int] = []
    monkeypatch.setattr("bank.k8s.fraud_scoring.service.sys.exit", exit_calls.append)

    clock.now = 0
    service.work()
    clock.now = 9
    service.work()  # still under the 10s deadline

    fault_file.mode = None
    clock.now = 9.5
    service.work()  # clears normally, resetting the crashloop timer

    fault_file.mode = "crashloop"
    clock.now = 10
    service.work()  # only 0.5s since the timer reset - should not exit yet

    assert exit_calls == []
