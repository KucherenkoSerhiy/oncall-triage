"""Lambda handler for the console API: API Gateway HTTP API v2 events."""

from __future__ import annotations

import json
import os
from typing import Any

from services.console_api.auth import AuthError, check_bearer
from services.console_api.http import json_response, no_content_response, options_response
from services.console_api.store import ConsoleStore

_REQUIRED_FIELDS = ("service", "pattern", "explanation")


def _store() -> ConsoleStore:
    import boto3

    resource = boto3.resource("dynamodb")
    return ConsoleStore(
        resource.Table(os.environ["ALERTS_TABLE"]),
        resource.Table(os.environ["VERDICTS_TABLE"]),
        resource.Table(os.environ["KNOWN_ISSUES_TABLE"]),
    )


def _origin() -> str:
    return os.environ["CONSOLE_ORIGIN"]


def _require_auth(event: dict) -> None:
    check_bearer(event.get("headers") or {}, os.environ["CONSOLE_TOKEN"])


def _handle_list_alerts(event: dict, store: ConsoleStore, origin: str) -> dict:
    params = event.get("queryStringParameters") or {}
    try:
        limit = int(params["limit"]) if params.get("limit") else 50
    except ValueError:
        return json_response(400, {"error": "limit must be an integer"}, origin)
    if not 1 <= limit <= 200:
        return json_response(400, {"error": "limit must be between 1 and 200"}, origin)
    return json_response(200, store.list_alerts(limit=limit), origin)


def _handle_get_alert(alert_id: str, store: ConsoleStore, origin: str) -> dict:
    alert = store.get_alert(alert_id)
    if alert is None:
        return json_response(404, {"error": "alert not found"}, origin)
    return json_response(200, alert, origin)


def _handle_list_known_issues(event: dict, store: ConsoleStore, origin: str) -> dict:
    params = event.get("queryStringParameters") or {}
    return json_response(200, store.list_known_issues(params.get("service")), origin)


def _handle_add_known_issue(event: dict, store: ConsoleStore, origin: str) -> dict:
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError as exc:
        return json_response(400, {"error": str(exc)}, origin)

    missing = [field for field in _REQUIRED_FIELDS if not body.get(field)]
    if missing:
        return json_response(400, {"error": f"missing fields: {', '.join(missing)}"}, origin)

    record = store.add_known_issue(
        service=body["service"],
        pattern=body["pattern"],
        explanation=body["explanation"],
        taught_by="console",
    )
    return json_response(201, record, origin)


def _handle_delete_known_issue(
    service: str, issue_id: str, store: ConsoleStore, origin: str
) -> dict:
    deleted = store.delete_known_issue(service, issue_id)
    if not deleted:
        return json_response(404, {"error": "known issue not found"}, origin)
    return no_content_response(origin)


def lambda_handler(event: dict, context: Any) -> dict:
    method = event["requestContext"]["http"]["method"]
    path = event["rawPath"]
    origin = _origin()

    if method == "OPTIONS":
        return options_response(origin)

    if method == "GET" and path == "/health":
        return json_response(200, {"ok": True}, origin)

    try:
        _require_auth(event)
    except AuthError as exc:
        return json_response(401, {"error": str(exc)}, origin)

    store = _store()
    segments = [segment for segment in path.split("/") if segment]

    if method == "GET" and segments == ["alerts"]:
        return _handle_list_alerts(event, store, origin)
    if method == "GET" and len(segments) == 2 and segments[0] == "alerts":
        return _handle_get_alert(segments[1], store, origin)
    if method == "GET" and segments == ["known-issues"]:
        return _handle_list_known_issues(event, store, origin)
    if method == "POST" and segments == ["known-issues"]:
        return _handle_add_known_issue(event, store, origin)
    if method == "DELETE" and len(segments) == 3 and segments[0] == "known-issues":
        return _handle_delete_known_issue(segments[1], segments[2], store, origin)

    return json_response(404, {"error": "not found"}, origin)
