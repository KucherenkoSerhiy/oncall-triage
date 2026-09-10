"""Unit tests for scripts/estate_status.py (kubectl and HTTP monkeypatched)."""

from __future__ import annotations

import base64
import io
import json

from scripts import estate_status


def test_print_pods_shells_out_to_kubectl(monkeypatch):
    calls = []

    def fake_kubectl(*args):
        calls.append(args)
        return "NAME  READY\ncards-authorization-abc  1/1\n"

    monkeypatch.setattr(estate_status, "kubectl", fake_kubectl)
    out = io.StringIO()

    estate_status.print_pods("bank", out=out)

    assert calls == [("-n", "bank", "get", "pods")]
    assert "cards-authorization-abc" in out.getvalue()


def test_print_faults_lists_every_service(monkeypatch):
    configmap = {"data": {"cards-authorization": "timeouts", "fraud-scoring": ""}}
    monkeypatch.setattr(estate_status, "kubectl", lambda *a: json.dumps(configmap))
    out = io.StringIO()

    estate_status.print_faults(out=out)

    text = out.getvalue()
    assert "cards-authorization" in text
    assert "timeouts" in text
    assert "fraud-scoring" in text
    assert "(normal)" in text


def test_print_firing_alerts_formats_rows(monkeypatch):
    alerts = [
        {
            "labels": {
                "alertname": "CardsAuthHighLatency",
                "service": "cards-authorization",
                "severity": "high",
            },
            "startsAt": "2026-01-01T00:00:00Z",
        }
    ]
    body = json.dumps(alerts).encode()
    monkeypatch.setattr(estate_status, "http", lambda method, url: (200, body))
    out = io.StringIO()

    estate_status.print_firing_alerts("http://localhost:9093", out=out)

    text = out.getvalue()
    assert "CardsAuthHighLatency" in text
    assert "cards-authorization" in text
    assert "high" in text
    assert "2026-01-01T00:00:00Z" in text


def test_print_firing_alerts_reports_no_alerts(monkeypatch):
    monkeypatch.setattr(estate_status, "http", lambda method, url: (200, b"[]"))
    out = io.StringIO()

    estate_status.print_firing_alerts("http://localhost:9093", out=out)

    assert "(none firing)" in out.getvalue()


def test_print_firing_alerts_reports_http_error(monkeypatch):
    monkeypatch.setattr(estate_status, "http", lambda method, url: (500, b"boom"))
    out = io.StringIO()

    estate_status.print_firing_alerts("http://localhost:9093", out=out)

    assert "500" in out.getvalue()


def test_print_forwarder_hint_when_unset(monkeypatch):
    monkeypatch.delenv("FORWARDER_URL", raising=False)
    out = io.StringIO()

    estate_status.print_forwarder_hint(out=out)

    assert "dummy receiver" in out.getvalue()


def test_print_forwarder_hint_silent_when_set(monkeypatch):
    monkeypatch.setenv("FORWARDER_URL", "https://forwarder.example/api")
    out = io.StringIO()

    estate_status.print_forwarder_hint(out=out)

    assert out.getvalue() == ""


def test_print_kafka_topics_shells_out_to_kubectl(monkeypatch):
    calls = []

    def fake_kubectl(*args):
        calls.append(args)
        return "NAME              PARTITIONS\ncard.authorized   1\n"

    monkeypatch.setattr(estate_status, "kubectl", fake_kubectl)
    out = io.StringIO()

    estate_status.print_kafka_topics(out=out)

    assert calls == [("-n", "bank", "get", "kafkatopics")]
    assert "card.authorized" in out.getvalue()


def test_print_kafka_consumer_lag_builds_admin_config_and_execs(monkeypatch):
    calls = []

    def fake_kubectl(*args, run=None):
        calls.append(args)
        if args[2:4] == ("get", "pod"):
            return "nordwind-bank-broker-0"
        if args[2:5] == ("get", "secret", "admin"):
            return base64.b64encode(b"adminpass").decode()
        if args[2:5] == ("get", "secret", "nordwind-bank-cluster-ca-cert"):
            return base64.b64encode(b"truststorepass").decode()
        if args[2] == "exec":
            return "GROUP          TOPIC             LAG\nfraud-scoring  card.authorized   0\n"
        raise AssertionError(f"unexpected kubectl args: {args}")

    monkeypatch.setattr(estate_status, "kubectl", fake_kubectl)
    out = io.StringIO()

    estate_status.print_kafka_consumer_lag(out=out)

    text = out.getvalue()
    assert "fraud-scoring" in text
    assert "card.authorized" in text

    exec_call = next(c for c in calls if c[2] == "exec")
    assert exec_call[3] == "nordwind-bank-broker-0"
    script = exec_call[-1]
    assert 'password="adminpass"' in script
    assert "ssl.truststore.password=truststorepass" in script
    assert "ssl.endpoint.identification.algorithm=\n" in script


def test_print_kafka_consumer_lag_reports_no_groups(monkeypatch):
    def fake_kubectl(*args, run=None):
        if args[2:4] == ("get", "pod"):
            return "nordwind-bank-broker-0"
        if args[2:4] == ("get", "secret"):
            return base64.b64encode(b"x").decode()
        if args[2] == "exec":
            return ""
        raise AssertionError(f"unexpected kubectl args: {args}")

    monkeypatch.setattr(estate_status, "kubectl", fake_kubectl)
    out = io.StringIO()

    estate_status.print_kafka_consumer_lag(out=out)

    assert "(no consumer groups)" in out.getvalue()


def test_main_kafka_flag_prints_topics_and_lag(monkeypatch):
    monkeypatch.setattr(estate_status, "print_pods", lambda *a, **k: None)
    monkeypatch.setattr(estate_status, "print_faults", lambda *a, **k: None)
    monkeypatch.setattr(estate_status, "print_firing_alerts", lambda *a, **k: None)
    monkeypatch.setattr(estate_status, "print_forwarder_hint", lambda *a, **k: None)
    calls = []
    monkeypatch.setattr(estate_status, "print_kafka_topics", lambda *a, **k: calls.append("topics"))
    monkeypatch.setattr(
        estate_status, "print_kafka_consumer_lag", lambda *a, **k: calls.append("lag")
    )

    exit_code = estate_status.main(["--kafka"])

    assert exit_code == 0
    assert calls == ["topics", "lag"]


def test_main_without_kafka_flag_skips_kafka_output(monkeypatch):
    monkeypatch.setattr(estate_status, "print_pods", lambda *a, **k: None)
    monkeypatch.setattr(estate_status, "print_faults", lambda *a, **k: None)
    monkeypatch.setattr(estate_status, "print_firing_alerts", lambda *a, **k: None)
    monkeypatch.setattr(estate_status, "print_forwarder_hint", lambda *a, **k: None)
    calls = []
    monkeypatch.setattr(estate_status, "print_kafka_topics", lambda *a, **k: calls.append("topics"))
    monkeypatch.setattr(
        estate_status, "print_kafka_consumer_lag", lambda *a, **k: calls.append("lag")
    )

    exit_code = estate_status.main([])

    assert exit_code == 0
    assert calls == []
