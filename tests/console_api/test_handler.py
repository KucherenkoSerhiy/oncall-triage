from __future__ import annotations

import json

import boto3

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


def _put_alert(moto_infra, alert_id, status, received_at, service="svc", severity="sev2"):
    table = boto3.resource("dynamodb", region_name=moto_infra["region"]).Table(
        moto_infra["alerts_table"]
    )
    table.put_item(
        Item={
            "alert_id": alert_id,
            "status": status,
            "received_at": received_at,
            "service": service,
            "alert_name": "HighLatency",
            "severity": severity,
            "occurrences": 1,
        }
    )


def _put_verdict(moto_infra, alert_id, action="page"):
    table = boto3.resource("dynamodb", region_name=moto_infra["region"]).Table(
        moto_infra["verdicts_table"]
    )
    table.put_item(Item={"alert_id": alert_id, "action": action, "known": False})


def test_health_is_open_and_ok(moto_infra):
    result = handler.lambda_handler(_event("GET", "/health"), None)

    assert result["statusCode"] == 200
    assert json.loads(result["body"]) == {"ok": True}


def test_options_returns_204_with_cors_headers(moto_infra):
    result = handler.lambda_handler(_event("OPTIONS", "/alerts"), None)

    assert result["statusCode"] == 204
    assert result["headers"]["Access-Control-Allow-Origin"] == ORIGIN
    assert result["headers"]["Access-Control-Allow-Headers"] == "Authorization, Content-Type"
    assert result["headers"]["Access-Control-Allow-Methods"] == "GET, POST, DELETE, OPTIONS"


def test_alerts_without_token_is_401(moto_infra):
    result = handler.lambda_handler(_event("GET", "/alerts"), None)

    assert result["statusCode"] == 401


def test_alerts_with_wrong_token_is_401(moto_infra):
    result = handler.lambda_handler(
        _event("GET", "/alerts", headers={"Authorization": "Bearer wrong"}), None
    )

    assert result["statusCode"] == 401


def test_list_alerts_orders_by_received_at_desc_and_respects_limit(moto_infra):
    _put_alert(moto_infra, "A" * 26, "queued", "2024-01-01T00:00:00Z")
    _put_alert(moto_infra, "B" * 26, "triaged", "2024-01-01T00:05:00Z")
    _put_alert(moto_infra, "C" * 26, "queued", "2024-01-01T00:10:00Z")

    result = handler.lambda_handler(
        _event("GET", "/alerts", headers=_auth_headers(), query={"limit": "2"}), None
    )

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert [item["alert_id"] for item in body] == ["C" * 26, "B" * 26]


def test_get_alert_includes_verdict_when_present(moto_infra):
    _put_alert(moto_infra, "A" * 26, "triaged", "2024-01-01T00:00:00Z")
    _put_verdict(moto_infra, "A" * 26, action="page")

    result = handler.lambda_handler(
        _event("GET", "/alerts/" + "A" * 26, headers=_auth_headers()), None
    )

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["verdict"]["action"] == "page"


def test_get_alert_without_verdict_is_none(moto_infra):
    _put_alert(moto_infra, "A" * 26, "queued", "2024-01-01T00:00:00Z")

    result = handler.lambda_handler(
        _event("GET", "/alerts/" + "A" * 26, headers=_auth_headers()), None
    )

    assert result["statusCode"] == 200
    assert json.loads(result["body"])["verdict"] is None


def test_get_alert_missing_is_404(moto_infra):
    result = handler.lambda_handler(
        _event("GET", "/alerts/" + "Z" * 26, headers=_auth_headers()), None
    )

    assert result["statusCode"] == 404


def test_known_issues_create_list_filter_delete_round_trip(moto_infra):
    create = handler.lambda_handler(
        _event(
            "POST",
            "/known-issues",
            headers=_auth_headers(),
            body=json.dumps(
                {
                    "service": "payments-api",
                    "pattern": "connection pool exhausted",
                    "explanation": "auto-recovers",
                }
            ),
        ),
        None,
    )
    assert create["statusCode"] == 201
    record = json.loads(create["body"])
    assert record["taught_by"] == "console"
    assert record["service"] == "payments-api"

    other = handler.lambda_handler(
        _event(
            "POST",
            "/known-issues",
            headers=_auth_headers(),
            body=json.dumps({"service": "other-svc", "pattern": "p", "explanation": "e"}),
        ),
        None,
    )
    assert other["statusCode"] == 201

    list_all = handler.lambda_handler(_event("GET", "/known-issues", headers=_auth_headers()), None)
    assert len(json.loads(list_all["body"])) == 2

    list_filtered = handler.lambda_handler(
        _event(
            "GET",
            "/known-issues",
            headers=_auth_headers(),
            query={"service": "payments-api"},
        ),
        None,
    )
    filtered = json.loads(list_filtered["body"])
    assert len(filtered) == 1
    assert filtered[0]["service"] == "payments-api"

    delete = handler.lambda_handler(
        _event(
            "DELETE",
            f"/known-issues/payments-api/{record['issue_id']}",
            headers=_auth_headers(),
        ),
        None,
    )
    assert delete["statusCode"] == 204

    delete_again = handler.lambda_handler(
        _event(
            "DELETE",
            f"/known-issues/payments-api/{record['issue_id']}",
            headers=_auth_headers(),
        ),
        None,
    )
    assert delete_again["statusCode"] == 404


def test_known_issues_missing_field_is_400(moto_infra):
    result = handler.lambda_handler(
        _event(
            "POST",
            "/known-issues",
            headers=_auth_headers(),
            body=json.dumps({"service": "payments-api", "pattern": "p"}),
        ),
        None,
    )

    assert result["statusCode"] == 400


def test_unknown_route_is_404(moto_infra):
    result = handler.lambda_handler(_event("GET", "/nope", headers=_auth_headers()), None)

    assert result["statusCode"] == 404
