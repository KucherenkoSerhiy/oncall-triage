from __future__ import annotations

import json

import boto3
import pytest

from bank.aws.common import BankFault
from bank.aws.payments import handler
from tests.bank.conftest import put_fault


def _receive_all(moto_infra) -> list[dict]:
    sqs = boto3.client("sqs", region_name=moto_infra["region"])
    response = sqs.receive_message(QueueUrl=moto_infra["queue_url"], MaxNumberOfMessages=10)
    return [json.loads(m["Body"]) for m in response.get("Messages", [])]


def test_normal_path_sends_5_messages_and_reports_authorised(moto_infra):
    result = handler.lambda_handler({}, None)

    assert result == {"authorised": 5}
    messages = _receive_all(moto_infra)
    assert len(messages) == 5
    for message in messages:
        assert message["currency"] == "EUR"
        assert "txn_id" in message
        assert "amount" in message


def test_errors_mode_raises_and_sends_nothing(moto_infra):
    put_fault(moto_infra, "payments", "errors")

    with pytest.raises(BankFault, match="upstream issuer returned 503"):
        handler.lambda_handler({}, None)

    assert _receive_all(moto_infra) == []


def test_latency_mode_sleeps_then_succeeds(moto_infra, monkeypatch):
    put_fault(moto_infra, "payments", "latency")
    slept = []
    monkeypatch.setattr(handler.time, "sleep", lambda seconds: slept.append(seconds))

    result = handler.lambda_handler({}, None)

    assert slept == [2.5]
    assert result == {"authorised": 5}


def test_pool_mode_emits_metric_and_raises_known_phrase(moto_infra):
    put_fault(moto_infra, "payments", "pool")

    with pytest.raises(BankFault, match="connection pool exhausted"):
        handler.lambda_handler({}, None)

    cloudwatch = boto3.client("cloudwatch", region_name=moto_infra["region"])
    metrics = cloudwatch.list_metrics(Namespace="Nordwind/Bank")["Metrics"]
    assert any(m["MetricName"] == "PoolExhausted" for m in metrics)
    assert _receive_all(moto_infra) == []
