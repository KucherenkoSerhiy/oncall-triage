"""GET /known-issues is the console's other read; smoke must exercise it (#137)."""

import json

import pytest

from scripts import smoke


def _fake_http(status, payload):
    def http(method, url, headers=None, body=None):
        assert method == "GET"
        assert url.endswith("/known-issues")
        return status, json.dumps(payload).encode()

    return http


def test_taught_pattern_listed_passes(monkeypatch):
    listed = [{"service": "payments", "pattern": "pool"}]
    monkeypatch.setattr(smoke, "http", _fake_http(200, listed))
    smoke.check_known_issue_list("https://api", "t", "pool")


def test_server_error_fails(monkeypatch):
    monkeypatch.setattr(smoke, "http", _fake_http(500, {"message": "Internal Server Error"}))
    with pytest.raises(smoke.SmokeError, match="HTTP 500"):
        smoke.check_known_issue_list("https://api", "t", "pool")


def test_missing_pattern_fails(monkeypatch):
    monkeypatch.setattr(smoke, "http", _fake_http(200, []))
    with pytest.raises(smoke.SmokeError, match="missing"):
        smoke.check_known_issue_list("https://api", "t", "pool")
