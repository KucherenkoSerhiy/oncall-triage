"""Trigger-level tests for the alert-forwarder HTTP function.

Exercises `function_app.forward` directly with a hand-built
`func.HttpRequest`, monkeypatching the injected `_logic.forward` so no real
HTTP call happens - proving the 202/400/502 status mapping the spec
describes as the trigger's job (vs. `forwarder.forward`'s own return value,
covered in `test_forwarder.py`).
"""

from __future__ import annotations

import json

import azure.functions as func

from bank.azure.alert_forwarder import function_app
from bank.azure.alert_forwarder.forwarder import ForwardResult


def _request(body: bytes) -> func.HttpRequest:
    return func.HttpRequest(
        method="POST", url="https://forwarder.example.com/api/alerts", body=body
    )


def test_trigger_returns_202_when_ingest_accepts(monkeypatch):
    monkeypatch.setattr(
        function_app._logic,
        "forward",
        lambda payload, ingest_url, secret: ForwardResult(
            status=200, source="azure-monitor", alert_count=1
        ),
    )

    response = function_app.forward(_request(b'{"data": {"essentials": {}}}'))

    assert response.status_code == 202


def test_trigger_returns_502_with_ingest_status_on_failure(monkeypatch):
    monkeypatch.setattr(
        function_app._logic,
        "forward",
        lambda payload, ingest_url, secret: ForwardResult(
            status=500, source="azure-monitor", alert_count=1
        ),
    )

    response = function_app.forward(_request(b'{"data": {"essentials": {}}}'))

    assert response.status_code == 502
    assert json.loads(response.get_body()) == {"ingest_status": 500}


def test_trigger_returns_400_for_invalid_json_body():
    response = function_app.forward(_request(b"not json"))

    assert response.status_code == 400


def test_trigger_returns_400_for_unrecognised_payload_shape():
    response = function_app.forward(_request(b'{"nonsense": true}'))

    assert response.status_code == 400
