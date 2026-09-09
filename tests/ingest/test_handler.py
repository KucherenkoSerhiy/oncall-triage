import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import boto3

from services.ingest import handler
from services.ingest.hmac_auth import sign

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def _http_event(body: dict, secret: str, timestamp: str | None = None) -> dict:
    body_bytes = json.dumps(body).encode()
    ts = timestamp or str(int(time.time()))
    sig = sign(secret.encode(), ts, body_bytes)
    return {
        "version": "2.0",
        "routeKey": "POST /alerts",
        "headers": {"x-nordwind-timestamp": ts, "x-nordwind-signature": sig},
        "body": body_bytes.decode(),
        "isBase64Encoded": False,
    }


def _sns_event(message: dict) -> dict:
    return {"Records": [{"EventSource": "aws:sns", "Sns": {"Message": json.dumps(message)}}]}


def _queue_message_count(queue_url: str, region: str) -> int:
    sqs = boto3.client("sqs", region_name=region)
    messages = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10).get("Messages", [])
    return len(messages)


def test_http_happy_path_returns_202(moto_infra):
    body = {"source": "bankops", "payload": _load("bankops")}
    event = _http_event(body, "test-secret")

    result = handler.lambda_handler(event, None)

    assert result["statusCode"] == 202
    payload = json.loads(result["body"])
    assert len(payload["results"]) == 1
    entry = payload["results"][0]
    assert entry["deduped"] is False
    assert len(entry["alert_id"]) == 26
    assert _queue_message_count(moto_infra["queue_url"], moto_infra["region"]) == 1


def test_http_bad_signature_returns_401(moto_infra):
    body = {"source": "bankops", "payload": _load("bankops")}
    event = _http_event(body, "wrong-secret")

    result = handler.lambda_handler(event, None)

    assert result["statusCode"] == 401
    assert "error" in json.loads(result["body"])


def test_http_malformed_json_returns_400(moto_infra):
    ts = str(int(time.time()))
    body_bytes = b"not json"
    sig = sign(b"test-secret", ts, body_bytes)
    event = {
        "headers": {"x-nordwind-timestamp": ts, "x-nordwind-signature": sig},
        "body": body_bytes.decode(),
        "isBase64Encoded": False,
    }

    result = handler.lambda_handler(event, None)

    assert result["statusCode"] == 400


def test_http_resolved_azure_alert_returns_422(moto_infra):
    payload = _load("azure_monitor")
    payload["data"]["essentials"]["monitorCondition"] = "Resolved"
    body = {"source": "azure-monitor", "payload": payload}
    event = _http_event(body, "test-secret")

    result = handler.lambda_handler(event, None)

    assert result["statusCode"] == 422


def test_sns_path_stores_and_enqueues(moto_infra):
    event = _sns_event(_load("cloudwatch"))

    result = handler.lambda_handler(event, None)

    assert len(result["results"]) == 1
    assert result["results"][0]["deduped"] is False
    assert _queue_message_count(moto_infra["queue_url"], moto_infra["region"]) == 1

    table = boto3.resource("dynamodb", region_name=moto_infra["region"]).Table(
        moto_infra["table_name"]
    )
    item = table.get_item(Key={"alert_id": result["results"][0]["alert_id"]})["Item"]
    assert item["status"] == "queued"


def test_sns_ok_state_produces_no_results(moto_infra):
    payload = _load("cloudwatch")
    payload["NewStateValue"] = "OK"
    event = _sns_event(payload)

    result = handler.lambda_handler(event, None)

    assert result["results"] == []


def test_http_dedup_path_reports_deduped_true(moto_infra):
    body = {"source": "bankops", "payload": _load("bankops")}

    first = handler.lambda_handler(_http_event(body, "test-secret"), None)
    second = handler.lambda_handler(_http_event(body, "test-secret"), None)

    assert json.loads(first["body"])["results"][0]["deduped"] is False
    assert json.loads(second["body"])["results"][0]["deduped"] is True
    assert _queue_message_count(moto_infra["queue_url"], moto_infra["region"]) == 1


def test_dedup_bump_then_expiry_creates_new_alert(moto_infra, monkeypatch):
    store = handler._alert_store()
    from services.ingest.adapters import bankops

    payload = _load("bankops")
    t0 = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)

    def _at(offset_minutes: float) -> str:
        return (t0 + timedelta(minutes=offset_minutes)).isoformat().replace("+00:00", "Z")

    alert_1 = bankops.to_canonical(payload, _at(0))
    result_1 = handler._process_alert(alert_1, store)
    assert result_1["deduped"] is False

    alert_2 = bankops.to_canonical(payload, _at(5))
    result_2 = handler._process_alert(alert_2, store)
    assert result_2["deduped"] is True

    table = boto3.resource("dynamodb", region_name=moto_infra["region"]).Table(
        moto_infra["table_name"]
    )
    item = table.get_item(Key={"alert_id": alert_1.alert_id})["Item"]
    assert item["occurrences"] == 2

    alert_3 = bankops.to_canonical(payload, _at(31))
    result_3 = handler._process_alert(alert_3, store)
    assert result_3["deduped"] is False
    assert result_3["alert_id"] != alert_1.alert_id

    assert _queue_message_count(moto_infra["queue_url"], moto_infra["region"]) == 2


def test_sns_path_stores_alarm_payloads_with_floats(moto_infra):
    # Regression for #50: a real CloudWatch alarm message carries floats
    # (Trigger.Threshold: 1.0 ...) inside the raw payload; boto3 refuses
    # floats, so the first live M4 alarm crashed ingest at put_new.
    message = _load("cloudwatch")
    message["Trigger"] = {
        "MetricName": "PoolExhausted",
        "Namespace": "Nordwind/Bank",
        "Statistic": "SUM",
        "Period": 60,
        "EvaluationPeriods": 1,
        "Threshold": 1.0,
        "Dimensions": [{"name": "service", "value": "payments"}],
    }
    message["NewStateValue"] = "ALARM"

    result = handler.lambda_handler(_sns_event(message), None)

    assert len(result["results"]) == 1
    table = boto3.resource("dynamodb", region_name=moto_infra["region"]).Table(
        moto_infra["table_name"]
    )
    item = table.get_item(Key={"alert_id": result["results"][0]["alert_id"]})["Item"]
    assert item["raw"]["Trigger"]["Threshold"] == 1
    assert item["status"] == "queued"
