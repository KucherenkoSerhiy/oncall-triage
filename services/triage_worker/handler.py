"""Lambda handler for the stub triage worker: consumes ``{"alert_id": ...}`` from SQS.

Writes a stub verdict for the alert and marks it ``triaged``. Uses
``ReportBatchItemFailures`` semantics: failures are returned per-record so
SQS retries only the failed messages.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

_STUB_TEXT = "Stub verdict (M2): triage worker arrives with M3."


def _dynamodb_resource() -> Any:
    import boto3

    return boto3.resource("dynamodb")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _process_record(record: dict, alerts_table: Any, verdicts_table: Any) -> None:
    message = json.loads(record["body"])
    alert_id = message["alert_id"]

    response = alerts_table.get_item(Key={"alert_id": alert_id})
    alert = response.get("Item")
    if alert is None:
        raise ValueError(f"alert not found: {alert_id!r}")

    verdict = {
        "alert_id": alert_id,
        "known": False,
        "severity": alert["severity"],
        "action": "monitor",
        "text": _STUB_TEXT,
        "model": "stub",
        "prompt_hash": "",
        "created_at": _now_iso(),
    }
    try:
        verdicts_table.put_item(
            Item=verdict,
            ConditionExpression="attribute_not_exists(alert_id)",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise
        return

    alerts_table.update_item(
        Key={"alert_id": alert_id},
        UpdateExpression="SET #status = :s",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={":s": "triaged"},
    )


def lambda_handler(event: dict, context: Any) -> dict:
    resource = _dynamodb_resource()
    alerts_table = resource.Table(os.environ["ALERTS_TABLE"])
    verdicts_table = resource.Table(os.environ["VERDICTS_TABLE"])

    failures = []
    for record in event["Records"]:
        try:
            _process_record(record, alerts_table, verdicts_table)
        except Exception:
            # Reported back to SQS for retry; logged so the failure is
            # diagnosable from CloudWatch, not just from the DLQ later.
            logger.exception("triage worker failed for message %s", record.get("messageId"))
            failures.append({"itemIdentifier": record["messageId"]})

    return {"batchItemFailures": failures}
