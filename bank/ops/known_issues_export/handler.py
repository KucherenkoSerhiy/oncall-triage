"""Lambda handler for ``known-issues-export``: weekly EventBridge schedule,
Monday 00:30 UTC.

Scans the known-issues table and writes ``known-issues-<YYYY-MM-DD>.json`` to
a private S3 bucket, so the taught memory an operator has spent weeks
building survives a table wipe (``bankops known-issues import`` is the
inverse - see docs/specs/m9b-known-issues-export-and-dlq.md). Logs one JSON
line: ``{"event", "count", "key"}``.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


def _dynamodb_resource() -> Any:
    import boto3

    return boto3.resource("dynamodb")


def _s3_client() -> Any:
    import boto3

    return boto3.client("s3")


def _render(value: Any) -> Any:
    """Recursively turn DynamoDB ``Decimal``s into plain JSON numbers."""
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    if isinstance(value, list):
        return [_render(v) for v in value]
    if isinstance(value, dict):
        return {k: _render(v) for k, v in value.items()}
    return value


def _scan_all(table: Any) -> list[dict]:
    items: list[dict] = []
    kwargs: dict[str, Any] = {}
    while True:
        response = table.scan(**kwargs)
        items.extend(response["Items"])
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            return items
        kwargs["ExclusiveStartKey"] = last_key


def build_export(items: list[dict], now: datetime) -> dict[str, Any]:
    rendered = [_render(dict(item)) for item in items]
    rendered.sort(key=lambda item: (item["service"], item["issue_id"]))
    return {
        "exported_at": now.isoformat().replace("+00:00", "Z"),
        "count": len(rendered),
        "items": rendered,
    }


def lambda_handler(event: dict, context: Any) -> dict:
    resource = _dynamodb_resource()
    table = resource.Table(os.environ["KNOWN_ISSUES_TABLE"])

    now = datetime.now(UTC)
    items = _scan_all(table)
    export = build_export(items, now)

    key = f"known-issues-{now.date().isoformat()}.json"
    _s3_client().put_object(
        Bucket=os.environ["KNOWN_ISSUES_BUCKET"],
        Key=key,
        Body=json.dumps(export).encode(),
        ContentType="application/json",
    )

    logger.info(json.dumps({"event": "known-issues-export", "count": export["count"], "key": key}))

    return {"count": export["count"], "key": key}
