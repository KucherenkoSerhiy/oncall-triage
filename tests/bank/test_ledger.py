from __future__ import annotations

import boto3

from bank.aws.ledger import handler
from tests.bank.conftest import put_fault


def _event(message_ids: list[str]) -> dict:
    return {"Records": [{"messageId": mid} for mid in message_ids]}


def test_normal_path_reports_no_failures(moto_infra):
    result = handler.lambda_handler(_event(["1", "2", "3"]), None)

    assert result == {"batchItemFailures": []}


def test_lag_mode_fails_every_record(moto_infra):
    put_fault(moto_infra, "ledger", "lag")

    result = handler.lambda_handler(_event(["1", "2", "3"]), None)

    assert result == {
        "batchItemFailures": [
            {"itemIdentifier": "1"},
            {"itemIdentifier": "2"},
            {"itemIdentifier": "3"},
        ]
    }


def test_reconciliation_mismatch_emits_metric_and_processes_normally(moto_infra):
    put_fault(moto_infra, "ledger", "reconciliation-mismatch")

    result = handler.lambda_handler(_event(["1"]), None)

    assert result == {"batchItemFailures": []}
    cloudwatch = boto3.client("cloudwatch", region_name=moto_infra["region"])
    metrics = cloudwatch.list_metrics(Namespace="Nordwind/Bank")["Metrics"]
    assert any(m["MetricName"] == "ReconciliationMismatch" for m in metrics)
