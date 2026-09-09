"""Shared fixtures: moto-backed faults table, ledger queue, env vars."""

from __future__ import annotations

import boto3
import pytest
from moto import mock_aws

_REGION = "eu-north-1"
_FAULTS_TABLE = "bank-faults-test"
_LEDGER_QUEUE_NAME = "ledger-test"


@pytest.fixture
def aws_credentials(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", _REGION)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")


@pytest.fixture
def moto_infra(aws_credentials, monkeypatch):
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name=_REGION)
        faults = dynamodb.create_table(
            TableName=_FAULTS_TABLE,
            KeySchema=[{"AttributeName": "service", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "service", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        faults.wait_until_exists()

        sqs = boto3.client("sqs", region_name=_REGION)
        queue_url = sqs.create_queue(QueueName=_LEDGER_QUEUE_NAME)["QueueUrl"]

        monkeypatch.setenv("BANK_FAULTS_TABLE", _FAULTS_TABLE)
        monkeypatch.setenv("LEDGER_QUEUE_URL", queue_url)

        yield {
            "faults_table": _FAULTS_TABLE,
            "queue_url": queue_url,
            "region": _REGION,
        }


def put_fault(moto_infra, service: str, mode: str, minutes: float = 5) -> None:
    import time
    from decimal import Decimal

    table = boto3.resource("dynamodb", region_name=moto_infra["region"]).Table(
        moto_infra["faults_table"]
    )
    now = time.time()
    table.put_item(
        Item={
            "service": service,
            "mode": mode,
            "until": Decimal(str(now + minutes * 60)),
            "set_at": Decimal(str(now)),
            "set_by": "test",
        }
    )
