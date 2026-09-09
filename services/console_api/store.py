"""DynamoDB access for the console API.

Table schemas (Terraform provisioning comes in a later spec):

* Alerts table (shared with ``services.ingest.dedup.AlertStore``): partition
  key ``alert_id`` (S). GSI ``by_status``: partition key ``status`` (S),
  sort key ``received_at`` (S, RFC 3339 UTC) - used to list open alerts most
  recent first.
* Verdicts table: partition key ``alert_id`` (S). Attributes: ``known`` (BOOL),
  ``severity`` (S), ``action`` (S), ``text`` (S), ``model`` (S),
  ``prompt_hash`` (S), ``created_at`` (S, RFC 3339 UTC). One verdict per
  alert; writes are conditional on the item not already existing.
* Known-issues table: partition key ``service`` (S), sort key ``issue_id``
  (S, ULID). Attributes: ``pattern`` (S), ``explanation`` (S), ``taught_by``
  (S), ``created_at`` (S, RFC 3339 UTC).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from services.ingest.canonical import new_alert_id

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

_OPEN_STATUSES = ("queued", "triaged")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class ConsoleStore:
    def __init__(
        self, alerts_table: Table, verdicts_table: Table, known_issues_table: Table
    ) -> None:
        self._alerts = alerts_table
        self._verdicts = verdicts_table
        self._known_issues = known_issues_table

    def list_alerts(self, limit: int = 50) -> list[dict]:
        items: list[dict] = []
        for status in _OPEN_STATUSES:
            response = self._alerts.query(
                IndexName="by_status",
                KeyConditionExpression="#status = :s",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={":s": status},
            )
            items.extend(response.get("Items", []))
        items.sort(key=lambda item: item["received_at"], reverse=True)
        return [dict(item) for item in items[:limit]]

    def get_alert(self, alert_id: str) -> dict | None:
        response = self._alerts.get_item(Key={"alert_id": alert_id})
        item = response.get("Item")
        if item is None:
            return None

        verdict_response = self._verdicts.get_item(Key={"alert_id": alert_id})
        verdict = verdict_response.get("Item")
        return {**dict(item), "verdict": dict(verdict) if verdict is not None else None}

    def list_known_issues(self, service: str | None = None) -> list[dict]:
        if service is not None:
            response = self._known_issues.query(
                KeyConditionExpression="service = :s",
                ExpressionAttributeValues={":s": service},
            )
        else:
            response = self._known_issues.scan()
        return [dict(item) for item in response.get("Items", [])]

    def add_known_issue(self, service: str, pattern: str, explanation: str, taught_by: str) -> dict:
        item = {
            "service": service,
            "issue_id": new_alert_id(),
            "pattern": pattern,
            "explanation": explanation,
            "taught_by": taught_by,
            "created_at": _now_iso(),
        }
        self._known_issues.put_item(Item=item)
        return item

    def delete_known_issue(self, service: str, issue_id: str) -> bool:
        response = self._known_issues.delete_item(
            Key={"service": service, "issue_id": issue_id},
            ReturnValues="ALL_OLD",
        )
        return "Attributes" in response
