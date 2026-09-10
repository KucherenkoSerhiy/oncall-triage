"""Unit tests for scripts/estate_scenarios.py (kubectl and HTTP monkeypatched)."""

from __future__ import annotations

import json

import pytest

from scripts import estate_scenarios, smoke


def _alertmanager_response(*alertnames):
    alerts = [{"labels": {"alertname": name}} for name in alertnames]
    return 200, json.dumps(alerts).encode()


def _spine_alerts(*alerts):
    return 200, json.dumps(list(alerts)).encode()


def test_run_cards_timeouts_happy_path(monkeypatch):
    patch_calls = []

    def fake_run(argv, check=False):
        patch_calls.append(json.loads(argv[-1]))

    verdict_alert = {
        "alert_id": "a1",
        "estate": "kubernetes",
        "service": "cards-authorization",
        "alert_name": "CardsAuthHighLatency",
        "received_at": "9999-01-01T00:00:01",
        "verdict": {"known": False, "action": "page", "model": "claude", "summary": "high latency"},
    }

    listed = {**verdict_alert, "verdict": None}  # the list endpoint never carries verdicts
    responses = iter(
        [
            _alertmanager_response("SomethingElse"),
            _alertmanager_response("CardsAuthHighLatency"),
            _spine_alerts(),
            _spine_alerts(listed),
            (200, json.dumps(verdict_alert).encode()),  # GET /alerts/a1
        ]
    )
    monkeypatch.setattr(estate_scenarios, "http", lambda *a, **k: next(responses))
    monkeypatch.setattr(estate_scenarios.time, "sleep", lambda _: None)

    alert = estate_scenarios.run_cards_timeouts(
        "http://localhost:9093", "https://api.example", "t", run=fake_run
    )

    assert alert["alert_id"] == "a1"
    assert patch_calls[0] == {"data": {"cards-authorization": "timeouts"}}
    assert patch_calls[-1] == {"data": {"cards-authorization": ""}}


def test_wait_for_rule_firing_times_out_when_rule_never_fires(monkeypatch):
    monkeypatch.setattr(estate_scenarios, "http", lambda *a, **k: _alertmanager_response())

    with pytest.raises(smoke.SmokeError, match="never fired"):
        estate_scenarios.wait_for_rule_firing(
            "http://localhost:9093",
            "CardsAuthHighLatency",
            timeout=10,
            interval=5,
            sleep=lambda _: None,
            now=iter([0, 5, 10, 15]).__next__,
        )


def test_wait_for_spine_verdict_times_out_when_alert_never_arrives(monkeypatch):
    monkeypatch.setattr(estate_scenarios, "http", lambda *a, **k: _spine_alerts())

    with pytest.raises(smoke.SmokeError, match="never delivered"):
        estate_scenarios.wait_for_spine_verdict(
            "https://api.example",
            "t",
            "kubernetes",
            "cards-authorization",
            "CardsAuthHighLatency",
            not_before="2026-01-01T00:00:00",
            timeout=10,
            interval=5,
            sleep=lambda _: None,
            now=iter([0, 5, 10, 15]).__next__,
        )


def test_wait_for_spine_verdict_times_out_when_no_verdict(monkeypatch):
    seen_alert = {
        "alert_id": "a1",
        "estate": "kubernetes",
        "service": "cards-authorization",
        "alert_name": "CardsAuthHighLatency",
        "received_at": "2026-01-01T00:00:01",
        "verdict": None,
    }

    def fake_http(method, url, headers=None, body=None):
        if url.endswith("/alerts/a1"):
            return 200, json.dumps(seen_alert).encode()
        return _spine_alerts(seen_alert)

    monkeypatch.setattr(estate_scenarios, "http", fake_http)

    with pytest.raises(smoke.SmokeError, match="no verdict"):
        estate_scenarios.wait_for_spine_verdict(
            "https://api.example",
            "t",
            "kubernetes",
            "cards-authorization",
            "CardsAuthHighLatency",
            not_before="2026-01-01T00:00:00",
            timeout=10,
            interval=5,
            sleep=lambda _: None,
            now=iter([0, 5, 10, 15]).__next__,
        )


def test_fault_cleared_when_alert_never_fires(monkeypatch):
    patch_calls = []

    def fake_run(argv, check=False):
        patch_calls.append(json.loads(argv[-1]))

    monkeypatch.setattr(estate_scenarios, "http", lambda *a, **k: _alertmanager_response())
    monkeypatch.setattr(estate_scenarios.time, "sleep", lambda _: None)

    with pytest.raises(smoke.SmokeError, match="never fired"):
        estate_scenarios.run_cards_timeouts(
            "http://localhost:9093",
            "https://api.example",
            "t",
            alert_timeout=0,
            run=fake_run,
        )

    assert patch_calls[0] == {"data": {"cards-authorization": "timeouts"}}
    assert patch_calls[-1] == {"data": {"cards-authorization": ""}}


def test_main_scenario_list_prints_all_scenarios(capsys):
    exit_code = estate_scenarios.main(["--scenario", "list"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "cards-timeouts (M6)" in out
    assert "fraud-lag (M7)" in out
    assert "broker-down (M7)" in out


def test_run_fraud_lag_happy_path(monkeypatch):
    patch_calls = []

    def fake_run(argv, check=False):
        patch_calls.append(json.loads(argv[-1]))

    verdict_alert = {
        "alert_id": "a2",
        "estate": "kubernetes",
        "service": "fraud-scoring",
        "alert_name": "KafkaConsumerLag",
        "received_at": "9999-01-01T00:00:01",
        "labels": {"route": "A"},
        "verdict": {"known": False, "action": "page", "model": "claude", "summary": "lag"},
    }
    listed = {**verdict_alert, "verdict": None}
    responses = iter(
        [
            _alertmanager_response("SomethingElse"),
            _alertmanager_response("KafkaConsumerLag"),
            _spine_alerts(),
            _spine_alerts(listed),
            (200, json.dumps(verdict_alert).encode()),
        ]
    )
    monkeypatch.setattr(estate_scenarios, "http", lambda *a, **k: next(responses))
    monkeypatch.setattr(estate_scenarios.time, "sleep", lambda _: None)

    alert = estate_scenarios.run_fraud_lag(
        "http://localhost:9093", "https://api.example", "t", run=fake_run
    )

    assert alert["alert_id"] == "a2"
    assert patch_calls[0] == {"data": {"fraud-scoring": "lag"}}
    assert patch_calls[-1] == {"data": {"fraud-scoring": ""}}


def test_run_fraud_lag_fails_when_rule_never_fires(monkeypatch):
    patch_calls = []

    def fake_run(argv, check=False):
        patch_calls.append(json.loads(argv[-1]))

    monkeypatch.setattr(estate_scenarios, "http", lambda *a, **k: _alertmanager_response())
    monkeypatch.setattr(estate_scenarios.time, "sleep", lambda _: None)

    with pytest.raises(smoke.SmokeError, match="never fired"):
        estate_scenarios.run_fraud_lag(
            "http://localhost:9093", "https://api.example", "t", alert_timeout=0, run=fake_run
        )

    assert patch_calls[-1] == {"data": {"fraud-scoring": ""}}


def test_run_fraud_lag_fails_when_verdict_took_the_wrong_route(monkeypatch):
    verdict_alert = {
        "alert_id": "a2",
        "estate": "kubernetes",
        "service": "fraud-scoring",
        "alert_name": "KafkaConsumerLag",
        "received_at": "9999-01-01T00:00:01",
        "labels": {"route": "B"},
        "verdict": {"known": False, "action": "page", "model": "claude", "summary": "lag"},
    }
    listed = {**verdict_alert, "verdict": None}
    responses = iter(
        [
            _alertmanager_response("KafkaConsumerLag"),
            _spine_alerts(listed),
            (200, json.dumps(verdict_alert).encode()),
        ]
    )
    monkeypatch.setattr(estate_scenarios, "http", lambda *a, **k: next(responses))
    monkeypatch.setattr(estate_scenarios.time, "sleep", lambda _: None)

    with pytest.raises(smoke.SmokeError, match="expected 'A'"):
        estate_scenarios.run_fraud_lag(
            "http://localhost:9093", "https://api.example", "t", run=lambda argv, check=False: None
        )


def test_run_broker_down_happy_path(monkeypatch):
    patch_calls = []

    def fake_run(argv, check=False):
        patch_calls.append(argv)

    verdict_alert = {
        "alert_id": "a3",
        "estate": "kubernetes",
        "service": "kafka",
        "alert_name": "KafkaBrokerDown",
        "received_at": "9999-01-01T00:00:01",
        "labels": {"route": "B"},
        "verdict": {"known": False, "action": "page", "model": "claude", "summary": "broker down"},
    }
    listed = {**verdict_alert, "verdict": None}
    responses = iter(
        [
            _alertmanager_response("KafkaBrokerDown"),
            _spine_alerts(listed),
            (200, json.dumps(verdict_alert).encode()),
        ]
    )
    monkeypatch.setattr(estate_scenarios, "http", lambda *a, **k: next(responses))
    monkeypatch.setattr(estate_scenarios.time, "sleep", lambda _: None)

    alert = estate_scenarios.run_broker_down(
        "http://localhost:9093", "https://api.example", "t", run=fake_run
    )

    assert alert["alert_id"] == "a3"
    # broker-down = pause reconciliation + delete the broker PodSet; recovery =
    # remove the pause annotation + wait for the PodSet and pod (#78).
    verbs = [argv[3] for argv in patch_calls if argv[:3] == ["kubectl", "-n", "bank"]]
    assert verbs[:3] == ["annotate", "wait", "delete"]
    assert "annotate" in verbs[3:] and verbs[-1] == "wait"


def test_run_broker_down_fails_when_rule_never_fires(monkeypatch):
    monkeypatch.setattr(estate_scenarios, "http", lambda *a, **k: _alertmanager_response())
    monkeypatch.setattr(estate_scenarios.time, "sleep", lambda _: None)

    with pytest.raises(smoke.SmokeError, match="never fired"):
        estate_scenarios.run_broker_down(
            "http://localhost:9093",
            "https://api.example",
            "t",
            alert_timeout=0,
            run=lambda argv, check=False: None,
        )


def test_run_broker_down_fails_when_verdict_took_the_wrong_route(monkeypatch):
    verdict_alert = {
        "alert_id": "a3",
        "estate": "kubernetes",
        "service": "kafka",
        "alert_name": "KafkaBrokerDown",
        "received_at": "9999-01-01T00:00:01",
        "labels": {"route": "A"},
        "verdict": {"known": False, "action": "page", "model": "claude", "summary": "broker down"},
    }
    listed = {**verdict_alert, "verdict": None}
    responses = iter(
        [
            _alertmanager_response("KafkaBrokerDown"),
            _spine_alerts(listed),
            (200, json.dumps(verdict_alert).encode()),
        ]
    )
    monkeypatch.setattr(estate_scenarios, "http", lambda *a, **k: next(responses))
    monkeypatch.setattr(estate_scenarios.time, "sleep", lambda _: None)

    with pytest.raises(smoke.SmokeError, match="expected 'B'"):
        estate_scenarios.run_broker_down(
            "http://localhost:9093", "https://api.example", "t", run=lambda argv, check=False: None
        )


def test_main_prints_the_route_the_verdict_took(monkeypatch, capsys):
    verdict_alert = {
        "alert_id": "a1",
        "estate": "kubernetes",
        "service": "cards-authorization",
        "alert_name": "CardsAuthHighLatency",
        "received_at": "9999-01-01T00:00:01",
        "labels": {"route": "B"},
        "verdict": {"known": False, "action": "page", "model": "claude", "summary": "high latency"},
    }
    listed = {**verdict_alert, "verdict": None}
    responses = iter(
        [
            _alertmanager_response("CardsAuthHighLatency"),
            _spine_alerts(listed),
            (200, json.dumps(verdict_alert).encode()),
        ]
    )
    monkeypatch.setattr(estate_scenarios, "http", lambda *a, **k: next(responses))
    monkeypatch.setattr(estate_scenarios.time, "sleep", lambda _: None)
    monkeypatch.setattr(estate_scenarios, "set_fault", lambda *a, **k: None)
    monkeypatch.setattr(estate_scenarios, "clear_fault", lambda *a, **k: None)
    monkeypatch.setenv("SMOKE_TOKEN", "t")

    exit_code = estate_scenarios.main(["--scenario", "cards-timeouts"])

    assert exit_code == 0
    assert "route=B" in capsys.readouterr().out
