"""Lambda handler for ``slo-reporter``: daily EventBridge schedule, 00:15 UTC.

Reads yesterday's triaged alerts and their verdicts, computes
``latency_seconds = verdict.created_at - alert.received_at`` per alert, and
publishes three custom metrics under ``Nordwind/Triage`` (dimension
``estate=all`` only - no ``day`` dimension, so the metric stays one time
series, per ``docs/slo.md``): ``VerdictLatencyP95``, ``AlertsTriaged``,
``SloAttainment``. Logs one JSON line: ``{"day", "alerts", "p95_seconds",
"attainment"}``.

Queries the alerts table's ``by_status`` GSI (hash key ``"triaged"``, range
key ``received_at``) for yesterday's UTC day rather than scanning the whole
table - the table has no ``by_day`` index, but ``by_status`` already sorts
by ``received_at`` within a status, so a bounded ``Query`` with a
``BETWEEN`` key condition returns exactly yesterday's triaged alerts
without an unbounded ``Scan``.

Known-issue short-circuits are ordinary verdicts and count normally. A cap
short-circuit (``verdict.model == "cap"``) always counts as a miss for
``SloAttainment`` regardless of its (near-instant) latency - it did not
receive a real triage - but its latency still feeds ``VerdictLatencyP95``,
which measures raw verdict latency, not SLO compliance. See ``docs/slo.md``.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

_NAMESPACE = "Nordwind/Triage"
_SLO_SECONDS = 300
_CAP_MODEL = "cap"


def _dynamodb_resource() -> Any:
    import boto3

    return boto3.resource("dynamodb")


def _cloudwatch_client() -> Any:
    import boto3

    return boto3.client("cloudwatch")


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _yesterday_bounds(now: datetime) -> tuple[str, str, str]:
    today_start = datetime(now.year, now.month, now.day, tzinfo=UTC)
    yesterday_start = today_start - timedelta(days=1)
    day = yesterday_start.date().isoformat()
    return _iso(yesterday_start), _iso(today_start), day


def _to_epoch(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def _triaged_alerts(alerts_table: Any, start: str, end: str) -> list[dict]:
    items: list[dict] = []
    kwargs: dict[str, Any] = {
        "IndexName": "by_status",
        "KeyConditionExpression": "#status = :s AND received_at BETWEEN :start AND :end",
        "ExpressionAttributeNames": {"#status": "status"},
        "ExpressionAttributeValues": {":s": "triaged", ":start": start, ":end": end},
    }
    while True:
        response = alerts_table.query(**kwargs)
        items.extend(response["Items"])
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            return items
        kwargs["ExclusiveStartKey"] = last_key


def _p95(latencies: list[float]) -> float:
    ordered = sorted(latencies)
    index = min(len(ordered) - 1, round(0.95 * (len(ordered) - 1)))
    return ordered[index]


def build_report(alerts: list[dict], verdicts_table: Any) -> dict[str, Any]:
    """Compute the day's latency/attainment/count report for ``alerts``.

    Alerts with no matching verdict are ignored (redelivery races aside,
    every ``triaged`` alert has one - this just keeps the handler defensive
    rather than crashing on unexpected state).
    """
    latencies: list[float] = []
    hits = 0
    considered = 0
    for alert in alerts:
        response = verdicts_table.get_item(Key={"alert_id": alert["alert_id"]})
        verdict = response.get("Item")
        if verdict is None:
            continue
        considered += 1
        latency = _to_epoch(verdict["created_at"]) - _to_epoch(alert["received_at"])
        latencies.append(latency)
        if verdict.get("model") != _CAP_MODEL and latency <= _SLO_SECONDS:
            hits += 1

    return {
        "alerts": considered,
        "p95_seconds": _p95(latencies) if latencies else None,
        "attainment": (hits / considered) if considered else None,
    }


def _publish_metrics(cloudwatch: Any, report: dict[str, Any]) -> None:
    dimensions = [{"Name": "estate", "Value": "all"}]
    metric_data = [
        {
            "MetricName": "AlertsTriaged",
            "Value": report["alerts"],
            "Unit": "Count",
            "Dimensions": dimensions,
        }
    ]
    if report["p95_seconds"] is not None:
        metric_data.append(
            {
                "MetricName": "VerdictLatencyP95",
                "Value": report["p95_seconds"],
                "Unit": "Seconds",
                "Dimensions": dimensions,
            }
        )
    if report["attainment"] is not None:
        metric_data.append(
            {
                "MetricName": "SloAttainment",
                "Value": report["attainment"],
                "Dimensions": dimensions,
            }
        )
    cloudwatch.put_metric_data(Namespace=_NAMESPACE, MetricData=metric_data)


def lambda_handler(event: dict, context: Any) -> dict:
    resource = _dynamodb_resource()
    alerts_table = resource.Table(os.environ["ALERTS_TABLE"])
    verdicts_table = resource.Table(os.environ["VERDICTS_TABLE"])

    start, end, day = _yesterday_bounds(datetime.now(UTC))
    alerts = _triaged_alerts(alerts_table, start, end)
    report = build_report(alerts, verdicts_table)

    _publish_metrics(_cloudwatch_client(), report)

    logger.info(json.dumps({"day": day, **report}))

    return report
