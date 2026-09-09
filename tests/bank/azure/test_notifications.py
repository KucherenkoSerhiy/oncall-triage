from __future__ import annotations

import json

import pytest

from bank.azure.customer_notifications.notifications import (
    ChaosClient,
    ProviderError,
    send_batch,
)


class RecordingMetrics:
    def __init__(self) -> None:
        self.records: list[tuple[str, float]] = []

    def record(self, name: str, value: float) -> None:
        self.records.append((name, value))


def _faults_response(*faults: dict) -> bytes:
    return json.dumps(list(faults)).encode()


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


# --- ChaosClient -------------------------------------------------------


def test_current_mode_picks_the_active_entry_for_the_service():
    calls = []

    def fake_http(url, headers):
        calls.append((url, headers))
        return _faults_response(
            {"service": "payments", "mode": "errors", "active": True},
            {"service": "customer-notifications", "mode": "backlog", "active": True},
        )

    client = ChaosClient("https://chaos.example.com", "tok", http=fake_http)

    assert client.current_mode() == "backlog"
    assert calls == [("https://chaos.example.com", {"Authorization": "Bearer tok"})]


def test_current_mode_ignores_inactive_entries():
    def fake_http(url, headers):
        return _faults_response(
            {"service": "customer-notifications", "mode": "backlog", "active": False}
        )

    client = ChaosClient("https://chaos.example.com", "tok", http=fake_http)

    assert client.current_mode() is None


def test_current_mode_is_none_when_no_entry_for_service():
    def fake_http(url, headers):
        return _faults_response({"service": "payments", "mode": "errors", "active": True})

    client = ChaosClient("https://chaos.example.com", "tok", http=fake_http)

    assert client.current_mode() is None


def test_current_mode_caches_within_ttl():
    calls = []
    clock = FakeClock(0.0)

    def fake_http(url, headers):
        calls.append(1)
        return _faults_response(
            {"service": "customer-notifications", "mode": "backlog", "active": True}
        )

    client = ChaosClient(
        "https://chaos.example.com", "tok", ttl_seconds=60, http=fake_http, clock=clock
    )

    assert client.current_mode() == "backlog"
    clock.now = 30.0
    assert client.current_mode() == "backlog"
    assert len(calls) == 1

    clock.now = 61.0
    assert client.current_mode() == "backlog"
    assert len(calls) == 2


def test_current_mode_falls_back_to_cached_value_on_poll_failure():
    responses = [
        _faults_response(
            {"service": "customer-notifications", "mode": "provider-429", "active": True}
        )
    ]
    clock = FakeClock(0.0)

    def fake_http(url, headers):
        if responses:
            return responses.pop()
        raise TimeoutError("chaos endpoint unreachable")

    client = ChaosClient(
        "https://chaos.example.com", "tok", ttl_seconds=60, http=fake_http, clock=clock
    )

    assert client.current_mode() == "provider-429"

    clock.now = 100.0
    assert client.current_mode() == "provider-429"


def test_current_mode_falls_back_to_none_when_first_poll_fails():
    def fake_http(url, headers):
        raise TimeoutError("chaos endpoint unreachable")

    client = ChaosClient("https://chaos.example.com", "tok", http=fake_http)

    assert client.current_mode() is None


def test_current_mode_without_token_is_normal_and_warns_once(caplog):
    def fake_http(url, headers):
        raise AssertionError("should not poll without a token")

    client = ChaosClient("https://chaos.example.com", None, http=fake_http)

    with caplog.at_level("WARNING"):
        assert client.current_mode() is None
        assert client.current_mode() is None

    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 1


# --- send_batch ----------------------------------------------------------


def test_send_batch_normal_mode():
    metrics = RecordingMetrics()

    send_batch(None, metrics)

    assert metrics.records == [("notifications_sent", 20)]


def test_send_batch_provider_429_mode_records_metric_then_raises():
    metrics = RecordingMetrics()

    with pytest.raises(ProviderError, match="429"):
        send_batch("provider-429", metrics)

    assert metrics.records == [("provider_429", 20)]


def test_send_batch_backlog_mode_succeeds_with_both_metrics():
    metrics = RecordingMetrics()

    send_batch("backlog", metrics)

    assert metrics.records == [("notifications_sent", 20), ("notifications_backlog", 150)]
