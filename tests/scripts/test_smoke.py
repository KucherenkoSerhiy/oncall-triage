"""Unit tests for scripts/smoke.py's polling logic (HTTP monkeypatched, no network)."""

import json

import pytest

from scripts import smoke


def test_wait_for_verdict_returns_once_verdict_present(monkeypatch):
    responses = iter(
        [
            (200, json.dumps({"alert_id": "a1", "verdict": None}).encode()),
            (200, json.dumps({"alert_id": "a1", "verdict": None}).encode()),
            (200, json.dumps({"alert_id": "a1", "verdict": {"action": "monitor"}}).encode()),
        ]
    )
    sleeps = []
    monkeypatch.setattr(smoke, "http", lambda *args, **kwargs: next(responses))

    alert = smoke.wait_for_verdict(
        "https://api.example",
        "token",
        "a1",
        timeout=10,
        interval=1,
        sleep=sleeps.append,
        now=iter([0, 0, 1, 2]).__next__,
    )

    assert alert["verdict"] == {"action": "monitor"}
    assert sleeps == [1, 1]


def test_wait_for_verdict_times_out(monkeypatch):
    monkeypatch.setattr(
        smoke,
        "http",
        lambda *args, **kwargs: (200, json.dumps({"alert_id": "a1", "verdict": None}).encode()),
    )
    clock = iter([0, 5, 10, 15])

    with pytest.raises(smoke.SmokeError) as exc_info:
        smoke.wait_for_verdict(
            "https://api.example",
            "token",
            "a1",
            timeout=10,
            interval=5,
            sleep=lambda _seconds: None,
            now=lambda: next(clock),
        )

    assert exc_info.value.step == "wait-for-verdict"


def test_wait_for_verdict_raises_on_unexpected_status(monkeypatch):
    monkeypatch.setattr(smoke, "http", lambda *args, **kwargs: (500, b"boom"))

    with pytest.raises(smoke.SmokeError) as exc_info:
        smoke.wait_for_verdict(
            "https://api.example",
            "token",
            "a1",
            timeout=10,
            interval=1,
            sleep=lambda _seconds: None,
            now=iter([0, 1]).__next__,
        )

    assert exc_info.value.step == "wait-for-verdict"


def test_check_health_raises_on_non_200(monkeypatch):
    monkeypatch.setattr(smoke, "http", lambda *args, **kwargs: (503, b"down"))

    with pytest.raises(smoke.SmokeError) as exc_info:
        smoke.check_health("https://api.example")

    assert exc_info.value.step == "health"


def test_fire_alert_returns_alert_id(monkeypatch):
    captured = {}

    def fake_http(method, url, headers=None, body=None):
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = json.loads(body)
        results = [{"alert_id": "a1", "fingerprint": "f", "deduped": False}]
        return 202, json.dumps({"results": results}).encode()

    monkeypatch.setattr(smoke, "http", fake_http)

    alert_id = smoke.fire_alert("https://api.example", "secret")

    assert alert_id == "a1"
    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.example/alerts"
    assert captured["body"]["payload"]["service"] == "smoke"
    assert captured["body"]["payload"]["alert_name"] == "SmokeTest"
    assert captured["body"]["payload"]["severity"] == "sev4"
    assert captured["headers"]["X-Nordwind-Signature"].startswith("sha256=")


def test_fire_alert_raises_on_non_202(monkeypatch):
    monkeypatch.setattr(smoke, "http", lambda *args, **kwargs: (400, b"bad"))

    with pytest.raises(smoke.SmokeError) as exc_info:
        smoke.fire_alert("https://api.example", "secret")

    assert exc_info.value.step == "fire-alert"


def test_fire_alert_accepts_service_and_description_overrides(monkeypatch):
    captured = {}

    def fake_http(method, url, headers=None, body=None):
        captured["body"] = json.loads(body)
        results = [{"alert_id": "a2", "fingerprint": "f", "deduped": False}]
        return 202, json.dumps({"results": results}).encode()

    monkeypatch.setattr(smoke, "http", fake_http)

    smoke.fire_alert(
        "https://api.example",
        "secret",
        service="payments",
        alert_name="SmokeTestKnownIssue",
        description="connection pool exhausted",
        sample_logs=["ERROR: connection pool exhausted"],
    )

    assert captured["body"]["payload"]["service"] == "payments"
    assert captured["body"]["payload"]["alert_name"] == "SmokeTestKnownIssue"
    assert captured["body"]["payload"]["description"] == "connection pool exhausted"
    assert captured["body"]["payload"]["sample_logs"] == ["ERROR: connection pool exhausted"]


def test_teach_known_issue_posts_to_known_issues(monkeypatch):
    captured = {}

    def fake_http(method, url, headers=None, body=None):
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = json.loads(body)
        return 201, b"{}"

    monkeypatch.setattr(smoke, "http", fake_http)

    smoke.teach_known_issue(
        "https://api.example", "token", "payments", "connection pool exhausted", "explained"
    )

    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.example/known-issues"
    assert captured["headers"]["Authorization"] == "Bearer token"
    assert captured["body"] == {
        "service": "payments",
        "pattern": "connection pool exhausted",
        "explanation": "explained",
    }


def test_teach_known_issue_raises_on_non_201(monkeypatch):
    monkeypatch.setattr(smoke, "http", lambda *args, **kwargs: (400, b"bad"))

    with pytest.raises(smoke.SmokeError) as exc_info:
        smoke.teach_known_issue(
            "https://api.example", "token", "payments", "pattern", "explanation"
        )

    assert exc_info.value.step == "teach-known-issue"
