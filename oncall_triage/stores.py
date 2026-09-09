"""Known-issue and alert stores backing the triage tools.

Two ``KnownIssueStore`` implementations share one protocol so
``oncall_triage/tools.py`` can be pointed at either via ``configure()``:
``JsonFileStore`` (a local JSON file, used by ``adk web``) and
``DynamoStore`` (the deployed worker's known-issues table). ``AlertRepo``
wraps the alerts table the same way, with an in-memory stand-in as its
default so local runs don't need AWS.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_STORE_PATH = _REPO_ROOT / "known_issues.json"
_ANY_SERVICE = "*"
_OPEN_STATUSES = ("queued", "triaged")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class KnownIssueStore(Protocol):
    def find_known(self, service: str, error_text: str) -> dict | None: ...

    def add_known(self, service: str, pattern: str, explanation: str, taught_by: str) -> dict: ...

    def list_known(self, service: str) -> list[dict]: ...


class JsonFileStore:
    """Known issues in a local JSON file, matched by case-insensitive substring.

    An issue whose ``service`` is ``"*"`` matches any service. With
    ``path=None`` (the default) the file path is re-read from
    ``TRIAGE_STORE_PATH`` on every call - same as the module-level store this
    class replaces - so tests can monkeypatch the env var after import.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self._fixed_path = Path(path) if path is not None else None

    def _resolve_path(self) -> Path:
        if self._fixed_path is not None:
            return self._fixed_path
        configured = os.environ.get("TRIAGE_STORE_PATH")
        return Path(configured) if configured else _DEFAULT_STORE_PATH

    def _load(self) -> dict:
        path = self._resolve_path()
        if not path.exists():
            return {"issues": []}
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data: dict) -> None:
        # Atomic replace: a crash mid-write must never leave a half-written
        # store - the whole known-issues memory would be unreadable JSON.
        path = self._resolve_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)

    def find_known(self, service: str, error_text: str) -> dict | None:
        data = self._load()
        error_lower = error_text.lower()
        for issue in data.get("issues", []):
            if issue.get("service") not in (service, _ANY_SERVICE):
                continue
            if issue["pattern"].lower() in error_lower:
                return issue
        return None

    def add_known(self, service: str, pattern: str, explanation: str, taught_by: str) -> dict:
        data = self._load()
        record = {
            "service": service,
            "issue_id": uuid.uuid4().hex,
            "pattern": pattern,
            "explanation": explanation,
            "taught_by": taught_by,
            "created_at": _now_iso(),
        }
        data.setdefault("issues", []).append(record)
        self._save(data)
        return record

    def list_known(self, service: str) -> list[dict]:
        data = self._load()
        return [issue for issue in data.get("issues", []) if issue.get("service") == service]


class DynamoStore:
    """Known issues in the M2b DynamoDB table: hash ``service``, range ``issue_id``."""

    def __init__(self, known_issues_table: Any) -> None:
        self._table = known_issues_table

    def _query(self, service: str) -> list[dict]:
        response = self._table.query(
            KeyConditionExpression="service = :s",
            ExpressionAttributeValues={":s": service},
        )
        return [dict(item) for item in response.get("Items", [])]

    def find_known(self, service: str, error_text: str) -> dict | None:
        error_lower = error_text.lower()
        candidates = self._query(service)
        if service != _ANY_SERVICE:
            candidates += self._query(_ANY_SERVICE)
        for issue in candidates:
            if issue["pattern"].lower() in error_lower:
                return issue
        return None

    def add_known(self, service: str, pattern: str, explanation: str, taught_by: str) -> dict:
        item = {
            "service": service,
            "issue_id": uuid.uuid4().hex,
            "pattern": pattern,
            "explanation": explanation,
            "taught_by": taught_by,
            "created_at": _now_iso(),
        }
        self._table.put_item(Item=item)
        return item

    def list_known(self, service: str) -> list[dict]:
        return self._query(service)


class InMemoryAlertsTable:
    """A tiny boto3-Table-like stand-in over a dict, keyed by ``alert_id``.

    Backs the default ``AlertRepo`` so ``adk web`` runs without AWS - empty
    results are fine locally, it just must not crash.
    """

    def __init__(self) -> None:
        self._items: dict[str, dict] = {}

    def put_item(self, *, Item: dict) -> None:  # noqa: N803 - mirrors the boto3 Table API
        self._items[Item["alert_id"]] = dict(Item)

    def get_item(self, *, Key: dict) -> dict:  # noqa: N803 - mirrors the boto3 Table API
        item = self._items.get(Key["alert_id"])
        return {"Item": dict(item)} if item is not None else {}

    def query(
        self,
        *,
        ExpressionAttributeValues: dict,  # noqa: N803 - mirrors the boto3 Table API
        **_kwargs: Any,
    ) -> dict:
        status = ExpressionAttributeValues.get(":s")
        since = ExpressionAttributeValues.get(":since")
        service = ExpressionAttributeValues.get(":svc")
        items = [
            dict(item)
            for item in self._items.values()
            if (status is None or item.get("status") == status)
            and (since is None or item.get("received_at", "") >= since)
            and (service is None or item.get("service") == service)
        ]
        return {"Items": items}


class AlertRepo:
    """Wraps the alerts table (or the in-memory stand-in) for the triage tools."""

    def __init__(self, alerts_table: Any | None = None) -> None:
        self._table = alerts_table if alerts_table is not None else InMemoryAlertsTable()

    def get_alert(self, alert_id: str) -> dict | None:
        response = self._table.get_item(Key={"alert_id": alert_id})
        item = response.get("Item")
        if item is None:
            return None
        result = dict(item)
        result.pop("raw", None)
        return result

    def recent_alerts(self, service: str, since_iso: str, limit: int = 10) -> list[dict]:
        items: list[dict] = []
        for status in _OPEN_STATUSES:
            response = self._table.query(
                IndexName="by_status",
                KeyConditionExpression="#status = :s AND received_at >= :since",
                FilterExpression="service = :svc",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={":s": status, ":since": since_iso, ":svc": service},
            )
            items.extend(response.get("Items", []))
        items.sort(key=lambda item: item["received_at"], reverse=True)
        return [dict(item) for item in items[:limit]]
