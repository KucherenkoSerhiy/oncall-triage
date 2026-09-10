"""Shared fixtures: moto-backed alerts (+ by_status GSI) and verdicts tables."""

from __future__ import annotations

import boto3
import pytest
from moto import mock_aws

_REGION = "eu-north-1"
_ALERTS_TABLE = "alerts-slo-test"
_VERDICTS_TABLE = "verdicts-slo-test"


@pytest.fixture
def aws_credentials(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", _REGION)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")


@pytest.fixture
def moto_infra(aws_credentials, monkeypatch):
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name=_REGION)

        alerts = dynamodb.create_table(
            TableName=_ALERTS_TABLE,
            KeySchema=[{"AttributeName": "alert_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "alert_id", "AttributeType": "S"},
                {"AttributeName": "status", "AttributeType": "S"},
                {"AttributeName": "received_at", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "by_status",
                    "KeySchema": [
                        {"AttributeName": "status", "KeyType": "HASH"},
                        {"AttributeName": "received_at", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        alerts.wait_until_exists()

        verdicts = dynamodb.create_table(
            TableName=_VERDICTS_TABLE,
            KeySchema=[{"AttributeName": "alert_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "alert_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        verdicts.wait_until_exists()

        monkeypatch.setenv("ALERTS_TABLE", _ALERTS_TABLE)
        monkeypatch.setenv("VERDICTS_TABLE", _VERDICTS_TABLE)

        yield {
            "alerts_table": _ALERTS_TABLE,
            "verdicts_table": _VERDICTS_TABLE,
            "region": _REGION,
        }
