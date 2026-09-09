from __future__ import annotations

import argparse
import json

from cli.bankops import client, commands
from cli.bankops.commands import Config
from services.ingest.hmac_auth import verify

CONFIG = Config(
    api="https://api.example.com",
    hmac_secret="test-secret",  # noqa: S106
    token="test-token",  # noqa: S106
)


def _fire_args(**overrides) -> argparse.Namespace:
    defaults = dict(
        service="payments-api",
        alert="HighLatency",
        severity="sev2",
        title=None,
        description=None,
        estate="aws",
        label=["env=prod"],
        log=["line1"],
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def test_fire_builds_correct_payload_and_signature(monkeypatch):
    captured = {}

    def fake_request(method, url, headers=None, body=None):
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = body
        return json.dumps({"results": [{"alert_id": "A" * 26, "deduped": False}]}).encode()

    monkeypatch.setattr(commands.client, "request", fake_request)

    exit_code = commands.cmd_fire(_fire_args(), CONFIG)

    assert exit_code == 0
    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.example.com/alerts"

    timestamp = captured["headers"]["X-Nordwind-Timestamp"]
    signature = captured["headers"]["X-Nordwind-Signature"]
    verify(b"test-secret", timestamp, captured["body"], signature)

    body = json.loads(captured["body"])
    assert body["source"] == "bankops"
    payload = body["payload"]
    assert payload["service"] == "payments-api"
    assert payload["alert_name"] == "HighLatency"
    assert payload["severity"] == "sev2"
    assert payload["estate"] == "aws"
    assert payload["labels"] == {"env": "prod"}
    assert payload["sample_logs"] == ["line1"]


def test_fire_exits_1_and_prints_error_on_failure(monkeypatch, capsys):
    def fake_request(method, url, headers=None, body=None):
        raise client.BankopsError(400, "bad request")

    monkeypatch.setattr(commands.client, "request", fake_request)

    exit_code = commands.cmd_fire(_fire_args(), CONFIG)

    assert exit_code == 1
    assert "bad request" in capsys.readouterr().out


def test_tail_renders_table_from_canned_response(monkeypatch, capsys):
    canned = [
        {
            "alert_id": "A" * 26,
            "received_at": "2024-01-01T12:34:56Z",
            "severity": "sev2",
            "service": "payments-api",
            "alert_name": "HighLatency",
            "status": "queued",
            "occurrences": 3,
        }
    ]

    def fake_request(method, url, headers=None, body=None):
        assert method == "GET"
        assert headers["Authorization"] == "Bearer test-token"
        return json.dumps(canned).encode()

    monkeypatch.setattr(commands.client, "request", fake_request)

    exit_code = commands.cmd_tail(argparse.Namespace(limit=50, watch=False, interval=10), CONFIG)

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "12:34:56" in out
    assert "payments-api" in out
    assert "HighLatency" in out
    assert "queued" in out
    assert "-" in out  # no verdict present


def test_teach_posts_the_right_body(monkeypatch):
    captured = {}

    def fake_request(method, url, headers=None, body=None):
        captured["method"] = method
        captured["url"] = url
        captured["body"] = body
        return json.dumps(
            {"service": "payments-api", "issue_id": "I" * 26, "pattern": "p", "explanation": "e"}
        ).encode()

    monkeypatch.setattr(commands.client, "request", fake_request)

    exit_code = commands.cmd_teach(
        argparse.Namespace(
            service="payments-api", pattern="connection pool exhausted", explanation="benign"
        ),
        CONFIG,
    )

    assert exit_code == 0
    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.example.com/known-issues"
    body = json.loads(captured["body"])
    assert body == {
        "service": "payments-api",
        "pattern": "connection pool exhausted",
        "explanation": "benign",
    }


def test_teach_exits_1_on_error(monkeypatch):
    def fake_request(method, url, headers=None, body=None):
        raise client.BankopsError(500, "server error")

    monkeypatch.setattr(commands.client, "request", fake_request)

    exit_code = commands.cmd_teach(
        argparse.Namespace(service="s", pattern="p", explanation="e"), CONFIG
    )

    assert exit_code == 1


def test_known_lists_issues(monkeypatch, capsys):
    def fake_request(method, url, headers=None, body=None):
        assert url == "https://api.example.com/known-issues?service=payments-api"
        return json.dumps(
            [{"service": "payments-api", "pattern": "p", "explanation": "e"}]
        ).encode()

    monkeypatch.setattr(commands.client, "request", fake_request)

    exit_code = commands.cmd_known(argparse.Namespace(service="payments-api"), CONFIG)

    assert exit_code == 0
    assert "payments-api" in capsys.readouterr().out
