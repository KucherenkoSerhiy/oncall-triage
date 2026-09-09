"""Shared fixtures: moto-backed DynamoDB table + GSI and SQS queue, env vars."""

from __future__ import annotations

import boto3
import pytest
from moto import mock_aws

_REGION = "eu-north-1"
_TABLE_NAME = "alerts-test"


@pytest.fixture
def aws_credentials(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", _REGION)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")


@pytest.fixture
def moto_infra(aws_credentials, monkeypatch):
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name=_REGION)
        table = dynamodb.create_table(
            TableName=_TABLE_NAME,
            KeySchema=[{"AttributeName": "alert_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "alert_id", "AttributeType": "S"},
                {"AttributeName": "fingerprint", "AttributeType": "S"},
                {"AttributeName": "received_at", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "by_fingerprint",
                    "KeySchema": [
                        {"AttributeName": "fingerprint", "KeyType": "HASH"},
                        {"AttributeName": "received_at", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()

        sqs = boto3.client("sqs", region_name=_REGION)
        queue_url = sqs.create_queue(QueueName="alerts-queue-test")["QueueUrl"]

        monkeypatch.setenv("ALERTS_TABLE", _TABLE_NAME)
        monkeypatch.setenv("ALERTS_QUEUE_URL", queue_url)
        monkeypatch.setenv("INGEST_HMAC_SECRET", "test-secret")

        yield {"table_name": _TABLE_NAME, "queue_url": queue_url, "region": _REGION}
