from __future__ import annotations

import json
from pathlib import Path

import pytest

from bank.azure.alert_forwarder.forwarder import ForwardResult, classify, forward
from services.ingest.hmac_auth import verify

_FIXTURES = Path(__file__).parent / "fixtures"
SECRET = b"test-secret"


def _load(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text())


# --- classify --------------------------------------------------------------


def test_classify_recognises_azure_monitor_common_alert_schema():
    assert classify(_load("azure_monitor.json")) == "azure-monitor"


def test_classify_recognises_alertmanager_webhook():
    assert classify(_load("alertmanager.json")) == "alertmanager"


def test_classify_raises_value_error_for_unrecognised_shape():
    with pytest.raises(ValueError, match="neither"):
        classify({"nonsense": True})


# --- forward -----------------------------------------------------------


def test_forward_happy_path_signs_and_wraps_azure_monitor_payload():
    payload = _load("azure_monitor.json")
    captured = {}

    def fake_http(method, url, headers, body):
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = body
        return 200, b"ok"

    result = forward(payload, "https://ingest.example.com/alerts", SECRET, http=fake_http)

    assert result == ForwardResult(status=200, source="azure-monitor", alert_count=1)
    assert captured["method"] == "POST"
    assert captured["url"] == "https://ingest.example.com/alerts"

    verify(
        SECRET,
        captured["headers"]["X-Nordwind-Timestamp"],
        captured["body"],
        captured["headers"]["X-Nordwind-Signature"],
    )

    wrapped = json.loads(captured["body"])
    assert wrapped == {"source": "azure-monitor", "payload": payload}


def test_forward_happy_path_counts_alertmanager_alerts():
    payload = _load("alertmanager.json")

    def fake_http(method, url, headers, body):
        return 200, b"ok"

    result = forward(payload, "https://ingest.example.com/alerts", SECRET, http=fake_http)

    assert result.source == "alertmanager"
    assert result.alert_count == len(payload["alerts"]) == 2


def test_forward_propagates_non_2xx_ingest_status():
    payload = _load("azure_monitor.json")

    def fake_http(method, url, headers, body):
        return 500, b"internal error"

    result = forward(payload, "https://ingest.example.com/alerts", SECRET, http=fake_http)

    assert result.status == 500


def test_forward_logs_one_json_line_per_request(caplog):
    payload = _load("azure_monitor.json")

    def fake_http(method, url, headers, body):
        return 202, b""

    with caplog.at_level("INFO"):
        forward(payload, "https://ingest.example.com/alerts", SECRET, http=fake_http)

    records = [r for r in caplog.records if r.name == "bank.azure.alert_forwarder.forwarder"]
    assert len(records) == 1
    logged = json.loads(records[0].message)
    assert logged == {
        "event": "forward",
        "source": "azure-monitor",
        "ingest_status": 202,
        "alert_count": 1,
    }
