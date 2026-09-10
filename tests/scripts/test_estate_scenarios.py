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


def test_main_m7_scenario_exits_2(capsys):
    exit_code = estate_scenarios.main(["--scenario", "fraud-lag"])

    assert exit_code == 2
