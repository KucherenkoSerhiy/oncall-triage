"""Unit tests for scripts/chaos_probe.py (HTTP monkeypatched, no network)."""

import json

import pytest

from scripts import chaos_probe, smoke


def _alerts(*alerts):
    return 200, json.dumps(list(alerts)).encode()


def test_wait_for_alert_ignores_older_and_other_services(monkeypatch):
    old = {
        "alert_id": "old",
        "service": "payments",
        "alert_name": "x-PoolExhausted-Sev3",
        "received_at": "2026-01-01T00:00:00",
    }
    other = {
        "alert_id": "o",
        "service": "ledger",
        "alert_name": "x-PoolExhausted-Sev3",
        "received_at": "2026-12-01T00:00:00",
    }
    fresh = {
        "alert_id": "new",
        "service": "payments",
        "alert_name": "x-PoolExhausted-Sev3",
        "received_at": "2026-12-01T00:00:01",
    }
    responses = iter([_alerts(old, other), _alerts(old, other, fresh)])
    monkeypatch.setattr(chaos_probe, "http", lambda *a, **k: next(responses))
    sleeps = []

    alert = chaos_probe.wait_for_alert(
        "https://api.example",
        "t",
        "payments",
        "PoolExhausted",
        not_before="2026-12-01T00:00:00",
        timeout=60,
        interval=15,
        sleep=sleeps.append,
        now=iter([0, 1, 2]).__next__,
    )

    assert alert["alert_id"] == "new"
    assert sleeps == [15]


def test_wait_for_alert_times_out(monkeypatch):
    monkeypatch.setattr(chaos_probe, "http", lambda *a, **k: _alerts())
    with pytest.raises(smoke.SmokeError, match="wait-for-alert"):
        chaos_probe.wait_for_alert(
            "https://api.example",
            "t",
            "payments",
            "PoolExhausted",
            not_before="2026-12-01T00:00:00",
            timeout=10,
            interval=5,
            sleep=lambda _: None,
            now=iter([0, 5, 10, 15]).__next__,
        )


def test_run_clears_fault_even_when_alert_never_comes(monkeypatch):
    calls = []

    def fake_http(method, url, headers=None, body=None):
        calls.append((method, url))
        if method == "POST":
            return 201, json.dumps({"service": "payments", "mode": "pool", "until": 1}).encode()
        if method == "DELETE":
            return 204, b""
        return _alerts()

    monkeypatch.setattr(chaos_probe, "http", fake_http)
    monkeypatch.setattr(chaos_probe, "_ALERT_TIMEOUT_SECONDS", 0)
    monkeypatch.setattr(chaos_probe.time, "sleep", lambda _: None)

    with pytest.raises(smoke.SmokeError, match="wait-for-alert"):
        chaos_probe.run(
            "https://api.example",
            "t",
            "payments",
            "pool",
            "PoolExhausted",
            expect_known=True,
            minutes=1,
        )

    assert ("DELETE", "https://api.example/chaos/payments") in calls


def test_run_rejects_stub_model_and_missing_known(monkeypatch):
    alert = {
        "alert_id": "a",
        "service": "payments",
        "alert_name": "PoolExhausted",
        "received_at": "9999-01-01T00:00:00",
        "source": "cloudwatch",
        "verdict": {"model": "claude", "known": False, "action": "monitor"},
    }

    def fake_http(method, url, headers=None, body=None):
        if method == "POST":
            return 201, json.dumps({"service": "payments", "mode": "pool", "until": 1}).encode()
        if method == "DELETE":
            return 204, b""
        if url.endswith("/alerts?limit=100"):
            return _alerts(alert)
        return 200, json.dumps(alert).encode()

    monkeypatch.setattr(chaos_probe, "http", fake_http)
    monkeypatch.setattr(smoke, "http", fake_http)

    with pytest.raises(smoke.SmokeError, match="expected known=true"):
        chaos_probe.run(
            "https://api.example",
            "t",
            "payments",
            "pool",
            "PoolExhausted",
            expect_known=True,
            minutes=1,
        )

    result = chaos_probe.run(
        "https://api.example",
        "t",
        "payments",
        "pool",
        "PoolExhausted",
        expect_known=False,
        minutes=1,
    )
    assert result["verdict"]["action"] == "monitor"
