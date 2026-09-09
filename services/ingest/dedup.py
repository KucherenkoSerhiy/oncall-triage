"""Alert de-duplication store, backed by a single DynamoDB table.

Table schema (Terraform provisioning comes in a later spec):

* Table: partition key ``alert_id`` (S).
* Attributes written per item: all ``CanonicalAlert.to_item()`` fields plus
  ``status`` (S: ``queued`` | ``triaged`` | ...), ``occurrences`` (N),
  ``last_seen_at`` (S, RFC 3339 UTC, set on every ``bump``).
* GSI ``by_fingerprint``: partition key ``fingerprint`` (S), sort key
  ``received_at`` (S, RFC 3339 UTC) — used to find the most recent open
  alert for a given fingerprint.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from services.ingest.canonical import CanonicalAlert

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

_OPEN_STATUSES = {"queued", "triaged"}
_DEDUP_WINDOW = timedelta(minutes=30)


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class AlertStore:
    def __init__(self, table_name: str, resource: Any = None) -> None:
        if resource is None:
            import boto3

            resource = boto3.resource("dynamodb")
        self._table: Table = resource.Table(table_name)

    def put_new(self, alert: CanonicalAlert) -> None:
        item = alert.to_item()
        item["status"] = "queued"
        item["occurrences"] = 1
        self._table.put_item(Item=item)

    def find_open(self, fingerprint: str, now_iso: str) -> dict | None:
        floor = _parse_iso(now_iso) - _DEDUP_WINDOW
        response = self._table.query(
            IndexName="by_fingerprint",
            KeyConditionExpression="fingerprint = :fp AND received_at >= :floor",
            FilterExpression="#status IN (:queued, :triaged)",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":fp": fingerprint,
                ":floor": floor.isoformat().replace("+00:00", "Z"),
                ":queued": "queued",
                ":triaged": "triaged",
            },
            ScanIndexForward=False,
        )
        items = response.get("Items", [])
        return dict(items[0]) if items else None

    def bump(self, alert_id: str, now_iso: str) -> None:
        self._table.update_item(
            Key={"alert_id": alert_id},
            UpdateExpression="SET last_seen_at = :now ADD occurrences :inc",
            ExpressionAttributeValues={":now": now_iso, ":inc": 1},
        )
