"""Lambda handler for the triage worker: consumes ``{"alert_id": ...}`` from SQS.

Runs the three-role ADK triage agent (``oncall_triage/agent.py``) per alert,
subject to a daily cap (``cap.py``), and writes the resulting verdict. Uses
``ReportBatchItemFailures`` semantics: failures are returned per-record so
SQS retries only the failed messages.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import UTC, datetime
from typing import Any

from botocore.exceptions import ClientError

from oncall_triage import tools
from oncall_triage.stores import AlertRepo, DynamoStore
from services.triage_worker.cap import DailyCap
from services.triage_worker.runner import TriageResult, TriageRunner

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

_CAP_REACHED_SUMMARY = "Daily LLM cap reached; not triaged"

_runner = TriageRunner()


def _dynamodb_resource() -> Any:
    import boto3

    return boto3.resource("dynamodb")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _configure_tools(resource: Any) -> None:
    known_issues_table = resource.Table(os.environ["KNOWN_ISSUES_TABLE"])
    alerts_table = resource.Table(os.environ["ALERTS_TABLE"])
    tools.configure(DynamoStore(known_issues_table), AlertRepo(alerts_table))


def _verdict_item(alert_id: str, alert: dict, result: TriageResult) -> dict:
    return {
        "alert_id": alert_id,
        "known": result.verdict["known"],
        "severity": result.verdict["severity"],
        "action": result.verdict["action"],
        "summary": result.verdict["summary"],
        "text": result.text,
        "model": result.model,
        "prompt_hash": result.prompt_hash,
        "input_tokens": result.usage["input_tokens"],
        "output_tokens": result.usage["output_tokens"],
        "verdict_parse_error": result.verdict_parse_error,
        "created_at": _now_iso(),
    }


def _cap_verdict_item(alert_id: str, alert: dict) -> dict:
    return {
        "alert_id": alert_id,
        "known": False,
        "severity": alert["severity"],
        "action": "monitor",
        "summary": _CAP_REACHED_SUMMARY,
        "text": _CAP_REACHED_SUMMARY,
        "model": "cap",
        "prompt_hash": "",
        "input_tokens": 0,
        "output_tokens": 0,
        "verdict_parse_error": False,
        "created_at": _now_iso(),
    }


def _process_record(record: dict, alerts_table: Any, verdicts_table: Any, cap: DailyCap) -> None:
    message = json.loads(record["body"])
    alert_id = message["alert_id"]

    response = alerts_table.get_item(Key={"alert_id": alert_id})
    alert = response.get("Item")
    if alert is None:
        raise ValueError(f"alert not found: {alert_id!r}")

    # Redelivery of an already-triaged alert: bail out before spending a
    # model call and a cap slot. The conditional put below is still the
    # authoritative guard against a concurrent double-write - this is just
    # a cheap short-circuit for the common (sequential) redelivery case.
    if "Item" in verdicts_table.get_item(Key={"alert_id": alert_id}):
        return

    start = time.monotonic()
    today = datetime.now(UTC).date().isoformat()
    if cap.try_acquire(today):
        result = _runner.run(alert)
        verdict = _verdict_item(alert_id, alert, result)
    else:
        verdict = _cap_verdict_item(alert_id, alert)
    duration_ms = int((time.monotonic() - start) * 1000)

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

    logger.info(
        json.dumps(
            {
                "alert_id": alert_id,
                "known": verdict["known"],
                "action": verdict["action"],
                "input_tokens": verdict["input_tokens"],
                "output_tokens": verdict["output_tokens"],
                "duration_ms": duration_ms,
            }
        )
    )


def lambda_handler(event: dict, context: Any) -> dict:
    resource = _dynamodb_resource()
    _configure_tools(resource)

    alerts_table = resource.Table(os.environ["ALERTS_TABLE"])
    verdicts_table = resource.Table(os.environ["VERDICTS_TABLE"])
    cap = DailyCap(verdicts_table)

    failures = []
    for record in event["Records"]:
        try:
            _process_record(record, alerts_table, verdicts_table, cap)
        except Exception:
            # Reported back to SQS for retry; logged so the failure is
            # diagnosable from CloudWatch, not just from the DLQ later.
            logger.exception("triage worker failed for message %s", record.get("messageId"))
            failures.append({"itemIdentifier": record["messageId"]})

    return {"batchItemFailures": failures}
