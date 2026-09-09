from __future__ import annotations

import json

from services.console_api import handler

TOKEN = "test-token"  # noqa: S105
ORIGIN = "https://console.example.com"


def _event(method: str, path: str, *, headers=None, body=None, query=None) -> dict:
    return {
        "requestContext": {"http": {"method": method}},
        "rawPath": path,
        "headers": headers or {},
        "body": body,
        "queryStringParameters": query,
    }


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {TOKEN}"}


def test_list_chaos_is_empty_when_no_faults_set(moto_infra):
    result = handler.lambda_handler(_event("GET", "/chaos", headers=_auth_headers()), None)

    assert result["statusCode"] == 200
    assert json.loads(result["body"]) == []


def test_set_chaos_writes_item_and_returns_201(moto_infra):
    result = handler.lambda_handler(
        _event(
            "POST",
            "/chaos/payments",
            headers=_auth_headers(),
            body=json.dumps({"mode": "errors", "minutes": 5}),
        ),
        None,
    )

    assert result["statusCode"] == 201
    record = json.loads(result["body"])
    assert record["service"] == "payments"
    assert record["mode"] == "errors"
    assert record["set_by"] == "console"

    listed = handler.lambda_handler(_event("GET", "/chaos", headers=_auth_headers()), None)
    faults = json.loads(listed["body"])
    assert len(faults) == 1
    assert faults[0]["service"] == "payments"
    assert faults[0]["active"] is True


def test_set_chaos_accepts_provider_429_for_customer_notifications(moto_infra):
    result = handler.lambda_handler(
        _event(
            "POST",
            "/chaos/customer-notifications",
            headers=_auth_headers(),
            body=json.dumps({"mode": "provider-429", "minutes": 5}),
        ),
        None,
    )

    assert result["statusCode"] == 201
    record = json.loads(result["body"])
    assert record["service"] == "customer-notifications"
    assert record["mode"] == "provider-429"


def test_set_chaos_rejects_unknown_mode_for_customer_notifications(moto_infra):
    result = handler.lambda_handler(
        _event(
            "POST",
            "/chaos/customer-notifications",
            headers=_auth_headers(),
            body=json.dumps({"mode": "not-a-real-mode", "minutes": 5}),
        ),
        None,
    )

    assert result["statusCode"] == 400


def test_set_chaos_unknown_service_is_404(moto_infra):
    result = handler.lambda_handler(
        _event(
            "POST",
            "/chaos/unknown-service",
            headers=_auth_headers(),
            body=json.dumps({"mode": "errors", "minutes": 5}),
        ),
        None,
    )

    assert result["statusCode"] == 404


def test_set_chaos_invalid_mode_is_400(moto_infra):
    result = handler.lambda_handler(
        _event(
            "POST",
            "/chaos/payments",
            headers=_auth_headers(),
            body=json.dumps({"mode": "not-a-real-mode", "minutes": 5}),
        ),
        None,
    )

    assert result["statusCode"] == 400


def test_clear_chaos_removes_fault_and_returns_204(moto_infra):
    handler.lambda_handler(
        _event(
            "POST",
            "/chaos/ledger",
            headers=_auth_headers(),
            body=json.dumps({"mode": "lag", "minutes": 5}),
        ),
        None,
    )

    result = handler.lambda_handler(
        _event("DELETE", "/chaos/ledger", headers=_auth_headers()), None
    )

    assert result["statusCode"] == 204
    listed = handler.lambda_handler(_event("GET", "/chaos", headers=_auth_headers()), None)
    assert json.loads(listed["body"]) == []


def test_clear_chaos_unknown_service_is_404(moto_infra):
    result = handler.lambda_handler(
        _event("DELETE", "/chaos/unknown-service", headers=_auth_headers()), None
    )

    assert result["statusCode"] == 404


def test_chaos_routes_require_auth(moto_infra):
    result = handler.lambda_handler(_event("GET", "/chaos"), None)

    assert result["statusCode"] == 401
