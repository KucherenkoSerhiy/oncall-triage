from __future__ import annotations

import argparse
import json
import time

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
            "estate": "aws",
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
    assert "aws" in out
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


def test_chaos_status_prints_table(monkeypatch, capsys):
    canned = [{"service": "payments", "mode": "errors", "until": time.time() + 120}]

    def fake_request(method, url, headers=None, body=None):
        assert method == "GET"
        assert url == "https://api.example.com/chaos"
        return json.dumps(canned).encode()

    monkeypatch.setattr(commands.client, "request", fake_request)

    exit_code = commands.cmd_chaos(
        argparse.Namespace(
            service=None, mode=None, minutes=5, clear=False, status=True, estate="aws"
        ),
        CONFIG,
    )

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "payments" in out
    assert "errors" in out


def test_chaos_sets_a_fault(monkeypatch):
    captured = {}

    def fake_request(method, url, headers=None, body=None):
        captured["method"] = method
        captured["url"] = url
        captured["body"] = body
        return json.dumps({"service": "payments", "mode": "errors", "until": 123.0}).encode()

    monkeypatch.setattr(commands.client, "request", fake_request)

    exit_code = commands.cmd_chaos(
        argparse.Namespace(
            service="payments", mode="errors", minutes=5, clear=False, status=False, estate="aws"
        ),
        CONFIG,
    )

    assert exit_code == 0
    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.example.com/chaos/payments"
    assert json.loads(captured["body"]) == {"mode": "errors", "minutes": 5}


def test_chaos_sets_a_fault_for_customer_notifications(monkeypatch):
    captured = {}

    def fake_request(method, url, headers=None, body=None):
        captured["method"] = method
        captured["url"] = url
        captured["body"] = body
        return json.dumps(
            {"service": "customer-notifications", "mode": "backlog", "until": 123.0}
        ).encode()

    monkeypatch.setattr(commands.client, "request", fake_request)

    exit_code = commands.cmd_chaos(
        argparse.Namespace(
            service="customer-notifications",
            mode="backlog",
            minutes=5,
            clear=False,
            status=False,
            estate="aws",
        ),
        CONFIG,
    )

    assert exit_code == 0
    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.example.com/chaos/customer-notifications"
    assert json.loads(captured["body"]) == {"mode": "backlog", "minutes": 5}


def test_chaos_rejects_invalid_mode_client_side(monkeypatch, capsys):
    def fake_request(method, url, headers=None, body=None):
        raise AssertionError("should not make an HTTP call for an invalid mode")

    monkeypatch.setattr(commands.client, "request", fake_request)

    exit_code = commands.cmd_chaos(
        argparse.Namespace(
            service="payments",
            mode="not-a-mode",
            minutes=5,
            clear=False,
            status=False,
            estate="aws",
        ),
        CONFIG,
    )

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "errors" in out
    assert "latency" in out
    assert "pool" in out


def test_chaos_clears_a_fault(monkeypatch):
    captured = {}

    def fake_request(method, url, headers=None, body=None):
        captured["method"] = method
        captured["url"] = url
        return b""

    monkeypatch.setattr(commands.client, "request", fake_request)

    exit_code = commands.cmd_chaos(
        argparse.Namespace(
            service="ledger", mode=None, minutes=5, clear=True, status=False, estate="aws"
        ),
        CONFIG,
    )

    assert exit_code == 0
    assert captured["method"] == "DELETE"
    assert captured["url"] == "https://api.example.com/chaos/ledger"


def test_chaos_kubernetes_patches_the_configmap(monkeypatch):
    captured = {}

    def fake_run(argv, check=False):
        captured["argv"] = argv
        captured["check"] = check

    monkeypatch.setattr(commands.subprocess, "run", fake_run)

    exit_code = commands.cmd_chaos(
        argparse.Namespace(
            service="cards-authorization",
            mode="timeouts",
            minutes=5,
            clear=False,
            status=False,
            estate="kubernetes",
        ),
        CONFIG,
    )

    assert exit_code == 0
    assert captured["check"] is True
    assert captured["argv"][:6] == [
        "kubectl",
        "-n",
        "bank",
        "patch",
        "configmap",
        "nordwind-faults",
    ]
    patch_arg = captured["argv"][-1]
    assert json.loads(patch_arg) == {"data": {"cards-authorization": "timeouts"}}


def test_chaos_kubernetes_clear_writes_empty_string(monkeypatch):
    captured = {}

    def fake_run(argv, check=False):
        captured["argv"] = argv

    monkeypatch.setattr(commands.subprocess, "run", fake_run)

    exit_code = commands.cmd_chaos(
        argparse.Namespace(
            service="fraud-scoring",
            mode=None,
            minutes=5,
            clear=True,
            status=False,
            estate="kubernetes",
        ),
        CONFIG,
    )

    assert exit_code == 0
    assert json.loads(captured["argv"][-1]) == {"data": {"fraud-scoring": ""}}


def test_chaos_kubernetes_rejects_invalid_mode_client_side(monkeypatch):
    def fake_run(argv, check=False):
        raise AssertionError("should not shell out for an invalid mode")

    monkeypatch.setattr(commands.subprocess, "run", fake_run)

    exit_code = commands.cmd_chaos(
        argparse.Namespace(
            service="cards-authorization",
            mode="not-a-mode",
            minutes=5,
            clear=False,
            status=False,
            estate="kubernetes",
        ),
        CONFIG,
    )

    assert exit_code == 1


def test_chaos_kubernetes_rejects_unknown_service(monkeypatch):
    def fake_run(argv, check=False):
        raise AssertionError("should not shell out for an unknown service")

    monkeypatch.setattr(commands.subprocess, "run", fake_run)

    exit_code = commands.cmd_chaos(
        argparse.Namespace(
            service="not-a-service",
            mode="timeouts",
            minutes=5,
            clear=False,
            status=False,
            estate="kubernetes",
        ),
        CONFIG,
    )

    assert exit_code == 1


def test_chaos_kubernetes_kafka_broker_down(monkeypatch):
    calls = []
    monkeypatch.setattr(commands, "kafka_broker_down", lambda: calls.append("broker-down"))
    monkeypatch.setattr(commands, "kafka_clear", lambda: calls.append("clear"))

    exit_code = commands.cmd_chaos(
        argparse.Namespace(
            service="kafka",
            mode="broker-down",
            minutes=5,
            clear=False,
            status=False,
            estate="kubernetes",
        ),
        CONFIG,
    )

    assert exit_code == 0
    assert calls == ["broker-down"]


def test_chaos_kubernetes_kafka_clear(monkeypatch):
    calls = []
    monkeypatch.setattr(commands, "kafka_broker_down", lambda: calls.append("broker-down"))
    monkeypatch.setattr(commands, "kafka_clear", lambda: calls.append("clear"))

    exit_code = commands.cmd_chaos(
        argparse.Namespace(
            service="kafka", mode=None, minutes=5, clear=True, status=False, estate="kubernetes"
        ),
        CONFIG,
    )

    assert exit_code == 0
    assert calls == ["clear"]


def test_chaos_kubernetes_kafka_rejects_invalid_mode(monkeypatch):
    monkeypatch.setattr(
        commands, "kafka_broker_down", lambda: (_ for _ in ()).throw(AssertionError)
    )

    exit_code = commands.cmd_chaos(
        argparse.Namespace(
            service="kafka",
            mode="not-a-mode",
            minutes=5,
            clear=False,
            status=False,
            estate="kubernetes",
        ),
        CONFIG,
    )

    assert exit_code == 1


def test_chaos_status_hints_at_kubernetes(monkeypatch, capsys):
    def fake_request(method, url, headers=None, body=None):
        return json.dumps([]).encode()

    monkeypatch.setattr(commands.client, "request", fake_request)

    exit_code = commands.cmd_chaos(
        argparse.Namespace(
            service=None, mode=None, minutes=5, clear=False, status=True, estate="aws"
        ),
        CONFIG,
    )

    assert exit_code == 0
    assert "kubernetes" in capsys.readouterr().out.lower()


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
