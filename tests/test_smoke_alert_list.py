"""GET /alerts is what the console calls; smoke must exercise it (#124)."""

import json

import pytest

from scripts import smoke


def _fake_http(status, payload):
    def http(method, url, headers=None, body=None):
        assert url.endswith("/alerts?limit=50")
        return status, json.dumps(payload).encode()

    return http


def test_listed_with_verdict_passes(monkeypatch):
    monkeypatch.setattr(
        smoke, "http", _fake_http(200, [{"alert_id": "A", "verdict": {"action": "ack"}}])
    )
    smoke.check_alert_list("https://api", "t", "A")


def test_listed_without_verdict_fails(monkeypatch):
    monkeypatch.setattr(smoke, "http", _fake_http(200, [{"alert_id": "A", "verdict": None}]))
    with pytest.raises(smoke.SmokeError, match="without its verdict"):
        smoke.check_alert_list("https://api", "t", "A")


def test_missing_alert_fails(monkeypatch):
    monkeypatch.setattr(smoke, "http", _fake_http(200, [{"alert_id": "B", "verdict": {}}]))
    with pytest.raises(smoke.SmokeError, match="missing"):
        smoke.check_alert_list("https://api", "t", "A")


def test_non_200_fails(monkeypatch):
    monkeypatch.setattr(smoke, "http", _fake_http(500, {"message": "Internal Server Error"}))
    with pytest.raises(smoke.SmokeError, match="HTTP 500"):
        smoke.check_alert_list("https://api", "t", "A")
