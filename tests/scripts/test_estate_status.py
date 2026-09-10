"""Unit tests for scripts/estate_status.py (kubectl and HTTP monkeypatched)."""

from __future__ import annotations

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
