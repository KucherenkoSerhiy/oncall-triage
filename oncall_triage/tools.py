"""Plain-Python tools used by the triage agent, bound to swappable stores.

``configure()`` swaps the module-level store instances at runtime: the
deployed worker points them at DynamoDB (``services/triage_worker/handler.py``),
while the default here - a local JSON file plus an in-memory alerts table -
keeps ``adk web`` working without AWS.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from .stores import AlertRepo, JsonFileStore, KnownIssueStore

_known_store: KnownIssueStore = JsonFileStore()
_alert_repo: AlertRepo = AlertRepo()


def configure(known_store: KnownIssueStore, alert_repo: AlertRepo) -> None:
    """Point the tool functions at a different pair of stores."""
    global _known_store, _alert_repo
    _known_store = known_store
    _alert_repo = alert_repo


def get_alert(alert_id: str) -> dict:
    """Fetch the canonical alert record by id (its stored fields, minus raw)."""
    alert = _alert_repo.get_alert(alert_id)
    if alert is None:
        return {"alert_id": alert_id, "found": False}
    return alert


def get_recent_alerts(service: str, minutes: int = 30) -> list[dict]:
    """List recent queued/triaged alerts for a service, most recent first."""
    since = (datetime.now(UTC) - timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")
    items = _alert_repo.recent_alerts(service, since)
    return [
        {
            "id": item["alert_id"],
            "alert_name": item.get("alert_name"),
            "severity": item.get("severity"),
            "received_at": item.get("received_at"),
            "status": item.get("status"),
        }
        for item in items
    ]


def check_known(service: str, error_text: str) -> dict:
    """Check whether error_text matches a previously-explained known issue."""
    match = _known_store.find_known(service, error_text)
    if match is None:
        return {"known": False, "pattern": None, "explanation": None}
    return {"known": True, "pattern": match["pattern"], "explanation": match["explanation"]}


def remember_issue(service: str, error_pattern: str, explanation: str) -> dict:
    """Persist a new known-issue pattern and its explanation, scoped to service."""
    record = _known_store.add_known(service, error_pattern, explanation, taught_by="triage-agent")
    return {"stored": True, "pattern": record["pattern"], "explanation": record["explanation"]}
