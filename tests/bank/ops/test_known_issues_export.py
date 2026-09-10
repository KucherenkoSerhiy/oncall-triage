from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

import boto3
import pytest
from moto import mock_aws

from bank.ops.known_issues_export import handler

_REGION = "eu-north-1"
_TABLE = "known-issues-export-test"
_BUCKET = "known-issues-export-test-bucket"


@pytest.fixture
def moto_infra(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", _REGION)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")

    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name=_REGION)
        table = dynamodb.create_table(
            TableName=_TABLE,
            KeySchema=[
                {"AttributeName": "service", "KeyType": "HASH"},
                {"AttributeName": "issue_id", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "service", "AttributeType": "S"},
                {"AttributeName": "issue_id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()

        s3 = boto3.client("s3", region_name=_REGION)
        s3.create_bucket(Bucket=_BUCKET, CreateBucketConfiguration={"LocationConstraint": _REGION})

        monkeypatch.setenv("KNOWN_ISSUES_TABLE", _TABLE)
        monkeypatch.setenv("KNOWN_ISSUES_BUCKET", _BUCKET)

        yield {"table": table, "s3": s3}


def _put_issue(table, service: str, issue_id: str, occurrences: int | None = None) -> None:
    item = {
        "service": service,
        "issue_id": issue_id,
        "pattern": "connection pool exhausted",
        "explanation": "benign, self-recovers",
        "taught_by": "test",
        "created_at": "2026-01-01T00:00:00Z",
    }
    if occurrences is not None:
        item["occurrences"] = Decimal(occurrences)
    table.put_item(Item=item)


def _expected_key() -> str:
    return f"known-issues-{datetime.now(UTC).date().isoformat()}.json"


def _exported_payload(moto_infra) -> dict:
    obj = moto_infra["s3"].get_object(Bucket=_BUCKET, Key=_expected_key())
    return json.loads(obj["Body"].read())


def test_export_writes_object_sorted_by_service_then_issue_id(moto_infra):
    _put_issue(moto_infra["table"], "payments", "b", occurrences=3)
    _put_issue(moto_infra["table"], "payments", "a")
    _put_issue(moto_infra["table"], "auth", "z")

    result = handler.lambda_handler({}, None)

    expected_key = _expected_key()
    assert result == {"count": 3, "key": expected_key}

    payload = _exported_payload(moto_infra)
    assert payload["count"] == 3
    assert [(item["service"], item["issue_id"]) for item in payload["items"]] == [
        ("auth", "z"),
        ("payments", "a"),
        ("payments", "b"),
    ]

    # Decimals render as plain JSON numbers, not {"N": "3"} or a string.
    occurrences = next(item["occurrences"] for item in payload["items"] if item["issue_id"] == "b")
    assert occurrences == 3
    assert isinstance(occurrences, int)


def test_empty_table_still_writes_a_zero_count_object(moto_infra):
    result = handler.lambda_handler({}, None)

    expected_key = _expected_key()
    assert result == {"count": 0, "key": expected_key}

    payload = _exported_payload(moto_infra)
    assert payload["count"] == 0
    assert payload["items"] == []
    assert "exported_at" in payload
