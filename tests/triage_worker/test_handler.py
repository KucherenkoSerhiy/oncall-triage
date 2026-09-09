from __future__ import annotations

import json

import boto3

from services.triage_worker import handler


def _alerts_table(moto_infra):
    return boto3.resource("dynamodb", region_name=moto_infra["region"]).Table(
        moto_infra["alerts_table"]
    )


def _verdicts_table(moto_infra):
    return boto3.resource("dynamodb", region_name=moto_infra["region"]).Table(
        moto_infra["verdicts_table"]
    )


def _put_alert(moto_infra, alert_id, severity="sev2"):
    _alerts_table(moto_infra).put_item(
        Item={
            "alert_id": alert_id,
            "status": "queued",
            "received_at": "2024-01-01T00:00:00Z",
            "service": "svc",
            "alert_name": "HighLatency",
            "severity": severity,
        }
    )


def _record(alert_id, message_id="msg-1"):
    return {"messageId": message_id, "body": json.dumps({"alert_id": alert_id})}


def test_queued_alert_gets_verdict_and_becomes_triaged(moto_infra):
    _put_alert(moto_infra, "A" * 26)

    result = handler.lambda_handler({"Records": [_record("A" * 26)]}, None)

    assert result["batchItemFailures"] == []

    verdict = _verdicts_table(moto_infra).get_item(Key={"alert_id": "A" * 26})["Item"]
    assert verdict["known"] is False
    assert verdict["severity"] == "sev2"
    assert verdict["action"] == "monitor"
    assert verdict["model"] == "stub"

    alert = _alerts_table(moto_infra).get_item(Key={"alert_id": "A" * 26})["Item"]
    assert alert["status"] == "triaged"


def test_redelivered_message_does_not_overwrite_verdict(moto_infra):
    _put_alert(moto_infra, "A" * 26)

    handler.lambda_handler({"Records": [_record("A" * 26, "msg-1")]}, None)
    first_verdict = _verdicts_table(moto_infra).get_item(Key={"alert_id": "A" * 26})["Item"]

    result = handler.lambda_handler({"Records": [_record("A" * 26, "msg-2")]}, None)

    assert result["batchItemFailures"] == []
    second_verdict = _verdicts_table(moto_infra).get_item(Key={"alert_id": "A" * 26})["Item"]
    assert second_verdict["created_at"] == first_verdict["created_at"]


def test_missing_alert_reported_in_batch_item_failures_others_succeed(moto_infra):
    _put_alert(moto_infra, "A" * 26)

    event = {
        "Records": [
            _record("A" * 26, "msg-ok"),
            _record("Z" * 26, "msg-missing"),
        ]
    }

    result = handler.lambda_handler(event, None)

    assert result["batchItemFailures"] == [{"itemIdentifier": "msg-missing"}]
    verdict = _verdicts_table(moto_infra).get_item(Key={"alert_id": "A" * 26})["Item"]
    assert verdict["action"] == "monitor"
